"""
Backend de l'app de suivi fitness. Sert l'API + les fichiers statiques de la PWA.
Base SQLite locale (pas de service DB séparé nécessaire pour un usage perso).

Variables d'environnement :
  APP_USER, APP_PASSWORD      -> auth basique HTTP protégeant toute l'app
  N8N_WEBHOOK_URL              -> webhook n8n appelé à chaque séance loggée (message de félicitations immédiat)
  DB_PATH                      -> chemin du fichier SQLite (défaut: /data/fitness.db)
"""
import json
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from templates_data import TEMPLATES

APP_USER = os.environ.get("APP_USER", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "change-moi")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")
DB_PATH = os.environ.get("DB_PATH", "/data/fitness.db")

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Fitness Tracker API")
security = HTTPBasic()


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, APP_USER)
    ok_pass = secrets.compare_digest(credentials.password, APP_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, detail="Identifiants invalides", headers={"WWW-Authenticate": "Basic"})
    return True


def get_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            day_name TEXT NOT NULL,
            exercises_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


init_db()


# --- Modèles ---
class SelectProgram(BaseModel):
    template_id: str


class ExerciseDone(BaseModel):
    name: str
    sets: int
    reps: int
    weight_kg: float = 0


class LogSession(BaseModel):
    day_name: str
    exercises: list[ExerciseDone]
    date: Optional[str] = None


class LogWeight(BaseModel):
    weight_kg: float
    date: Optional[str] = None


# --- Programmes ---
@app.get("/api/templates")
def list_templates(_: bool = Depends(check_auth)):
    return [{"id": t["id"], "name": t["name"], "description": t["description"]} for t in TEMPLATES.values()]


@app.post("/api/program/select")
def select_program(body: SelectProgram, _: bool = Depends(check_auth)):
    if body.template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Programme introuvable")
    conn = get_db()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('program_id', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (body.template_id,),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/program/current")
def current_program(_: bool = Depends(check_auth)):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = 'program_id'").fetchone()
    if not row:
        conn.close()
        return {"program": None, "next_day": None}

    template = TEMPLATES[row["value"]]
    total_sessions = conn.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    conn.close()

    next_day_index = total_sessions % len(template["days"])
    next_day = template["days"][next_day_index]
    return {"program": template, "next_day": next_day}


# --- Séances ---
@app.post("/api/sessions")
def log_session(body: LogSession, _: bool = Depends(check_auth)):
    session_date = body.date or date.today().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (date, day_name, exercises_json, created_at) VALUES (?, ?, ?, ?)",
        (session_date, body.day_name, json.dumps([e.model_dump() for e in body.exercises]), datetime.now().isoformat()),
    )
    conn.commit()
    total = conn.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    conn.close()

    _notify_n8n({
        "event": "session_completed",
        "day_name": body.day_name,
        "date": session_date,
        "total_sessions": total,
    })
    return {"status": "ok"}


@app.get("/api/sessions")
def list_sessions(limit: int = 100, _: bool = Depends(check_auth)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM sessions ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [
        {"id": r["id"], "date": r["date"], "day_name": r["day_name"], "exercises": json.loads(r["exercises_json"])}
        for r in rows
    ]


# --- Poids ---
@app.post("/api/weight")
def log_weight(body: LogWeight, _: bool = Depends(check_auth)):
    entry_date = body.date or date.today().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO weights (date, weight_kg, created_at) VALUES (?, ?, ?)",
        (entry_date, body.weight_kg, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/weight")
def list_weights(_: bool = Depends(check_auth)):
    conn = get_db()
    rows = conn.execute("SELECT date, weight_kg FROM weights ORDER BY date ASC").fetchall()
    conn.close()
    return [{"date": r["date"], "weight_kg": r["weight_kg"]} for r in rows]


# --- Stats (pour le dashboard et pour n8n) ---
@app.get("/api/stats")
def stats(_: bool = Depends(check_auth)):
    conn = get_db()
    sessions = conn.execute("SELECT date, exercises_json FROM sessions ORDER BY date ASC").fetchall()
    weights = conn.execute("SELECT date, weight_kg FROM weights ORDER BY date ASC").fetchall()
    conn.close()

    dates = sorted({s["date"] for s in sessions})
    streak = _compute_streak(dates)

    cutoff = (date.today() - timedelta(days=7)).isoformat()
    last7 = [s for s in sessions if s["date"] >= cutoff]
    volume_7d = 0.0
    for s in last7:
        for ex in json.loads(s["exercises_json"]):
            volume_7d += ex["sets"] * ex["reps"] * ex["weight_kg"]

    last_session_date = dates[-1] if dates else None
    today_done = last_session_date == date.today().isoformat()

    weight_trend = None
    if len(weights) >= 2:
        weight_trend = round(weights[-1]["weight_kg"] - weights[0]["weight_kg"], 1)

    return {
        "total_sessions": len(sessions),
        "streak_days": streak,
        "volume_7d": round(volume_7d, 1),
        "last_session_date": last_session_date,
        "today_done": today_done,
        "current_weight": weights[-1]["weight_kg"] if weights else None,
        "weight_trend_total": weight_trend,
    }


def _compute_streak(sorted_dates: list[str]) -> int:
    if not sorted_dates:
        return 0
    streak = 1
    for i in range(len(sorted_dates) - 1, 0, -1):
        cur = datetime.fromisoformat(sorted_dates[i])
        prev = datetime.fromisoformat(sorted_dates[i - 1])
        if (cur - prev).days == 1:
            streak += 1
        else:
            break
    last = datetime.fromisoformat(sorted_dates[-1])
    gap = (datetime.now() - last).days
    return streak if gap <= 1 else 0


def _notify_n8n(payload: dict):
    if not N8N_WEBHOOK_URL:
        return
    try:
        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
    except requests.RequestException:
        pass  # ne bloque jamais l'app si n8n est down


# --- Fichiers statiques (PWA) — servis en dernier, protégés par la même auth ---
@app.get("/")
def index(_: bool = Depends(check_auth)):
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/manifest.json")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.json")


@app.get("/service-worker.js")
def sw():
    return FileResponse(STATIC_DIR / "service-worker.js", media_type="application/javascript")
