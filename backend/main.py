"""
Backend de l'app de suivi fitness. Sert l'API + les fichiers statiques de la PWA.
Base SQLite locale (pas de service DB séparé nécessaire pour un usage perso).
Multi-utilisateurs : chaque compte a ses propres programmes/séances/poids, isolés par user_id.

Variables d'environnement :
  N8N_WEBHOOK_URL     -> webhook n8n appelé à chaque séance loggée
  DB_PATH              -> chemin du fichier SQLite (défaut: /data/fitness.db)
  REGISTRATION_ENABLED -> "false" pour désactiver la création de nouveaux comptes (défaut: true)
"""
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from templates_data import TEMPLATES, MUSCLE_GROUPS, build_day

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")
DB_PATH = os.environ.get("DB_PATH", "/data/fitness.db")
REGISTRATION_ENABLED = os.environ.get("REGISTRATION_ENABLED", "true").lower() != "false"

STATIC_DIR = Path(__file__).resolve().parent / "static"
PBKDF2_ITERATIONS = 100_000

app = FastAPI(title="SeeBorg API")
security = HTTPBasic()


def get_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (user_id, key)
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            day_name TEXT NOT NULL,
            exercises_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


init_db()


# --- Mots de passe : PBKDF2-HMAC-SHA256 salé, pas de dépendance externe ---
def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    digest, _ = hash_password(password, bytes.fromhex(salt_hex))
    return secrets.compare_digest(digest, expected_hash)


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE login = ?", (credentials.username,)).fetchone()
    conn.close()
    if not row or not verify_password(credentials.password, row["salt"], row["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants invalides", headers={"WWW-Authenticate": "Basic"})
    return {"id": row["id"], "nom": row["nom"], "login": row["login"]}


def _set_setting(conn, user_id: int, key: str, value: str):
    conn.execute(
        "INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value",
        (user_id, key, value),
    )


# --- Modèles ---
class RegisterUser(BaseModel):
    nom: str = Field(min_length=1, max_length=60)
    login: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=4, max_length=200)


class SelectProgram(BaseModel):
    template_id: str


class CustomDay(BaseModel):
    name: str
    muscle_groups: list[str]


class CustomProgram(BaseModel):
    days: list[CustomDay]


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


# --- Comptes ---
@app.post("/api/register")
def register(body: RegisterUser):
    if not REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail="La création de compte est désactivée sur ce serveur")

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE login = ?", (body.login,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Cet identifiant est déjà pris")

    password_hash, salt = hash_password(body.password)
    conn.execute(
        "INSERT INTO users (nom, login, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
        (body.nom.strip(), body.login.strip(), password_hash, salt, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/whoami")
def whoami(user: dict = Depends(get_current_user)):
    return {"status": "ok", "nom": user["nom"]}


# --- Groupes musculaires (pour le constructeur de programme personnalisé) ---
@app.get("/api/muscle-groups")
def list_muscle_groups(user: dict = Depends(get_current_user)):
    return [{"id": k, "name": v} for k, v in MUSCLE_GROUPS.items()]


# --- Programmes ---
@app.get("/api/templates")
def list_templates(user: dict = Depends(get_current_user)):
    return [{"id": t["id"], "name": t["name"], "description": t["description"]} for t in TEMPLATES.values()]


@app.post("/api/program/select")
def select_program(body: SelectProgram, user: dict = Depends(get_current_user)):
    if body.template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Programme introuvable")
    conn = get_db()
    _set_setting(conn, user["id"], "program_id", body.template_id)
    conn.execute("DELETE FROM settings WHERE user_id = ? AND key = 'custom_program_json'", (user["id"],))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.post("/api/program/custom")
def create_custom_program(body: CustomProgram, user: dict = Depends(get_current_user)):
    if not body.days:
        raise HTTPException(status_code=400, detail="Au moins un jour d'entraînement est requis")
    for d in body.days:
        for g in d.muscle_groups:
            if g not in MUSCLE_GROUPS:
                raise HTTPException(status_code=400, detail=f"Groupe musculaire inconnu : {g}")
        if not d.muscle_groups:
            raise HTTPException(status_code=400, detail=f"Le jour '{d.name}' n'a aucun groupe musculaire sélectionné")

    program = {
        "id": "custom",
        "name": "Programme personnalisé",
        "description": "Construit sur mesure",
        "days": [build_day(d.name, d.muscle_groups) for d in body.days],
    }

    conn = get_db()
    _set_setting(conn, user["id"], "program_id", "custom")
    _set_setting(conn, user["id"], "custom_program_json", json.dumps(program, ensure_ascii=False))
    conn.commit()
    conn.close()
    return {"status": "ok", "program": program}


@app.get("/api/program/current")
def current_program(user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE user_id = ? AND key = 'program_id'", (user["id"],)).fetchone()
    if not row:
        conn.close()
        return {"program": None, "next_day": None}

    if row["value"] == "custom":
        custom_row = conn.execute(
            "SELECT value FROM settings WHERE user_id = ? AND key = 'custom_program_json'", (user["id"],)
        ).fetchone()
        if not custom_row:
            conn.close()
            return {"program": None, "next_day": None}
        template = json.loads(custom_row["value"])
    else:
        template = TEMPLATES[row["value"]]

    total_sessions = conn.execute("SELECT COUNT(*) AS c FROM sessions WHERE user_id = ?", (user["id"],)).fetchone()["c"]
    conn.close()

    next_day_index = total_sessions % len(template["days"])
    return {"program": template, "next_day": template["days"][next_day_index]}


# --- Séances ---
@app.post("/api/sessions")
def log_session(body: LogSession, user: dict = Depends(get_current_user)):
    session_date = body.date or date.today().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (user_id, date, day_name, exercises_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (user["id"], session_date, body.day_name, json.dumps([e.model_dump() for e in body.exercises]), datetime.now().isoformat()),
    )
    conn.commit()
    total = conn.execute("SELECT COUNT(*) AS c FROM sessions WHERE user_id = ?", (user["id"],)).fetchone()["c"]
    conn.close()

    _notify_n8n({
        "event": "session_completed",
        "nom": user["nom"],
        "day_name": body.day_name,
        "date": session_date,
        "total_sessions": total,
    })
    return {"status": "ok"}


@app.get("/api/sessions")
def list_sessions(limit: int = 200, user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY date DESC LIMIT ?", (user["id"], limit)
    ).fetchall()
    conn.close()
    return [
        {"id": r["id"], "date": r["date"], "day_name": r["day_name"], "exercises": json.loads(r["exercises_json"])}
        for r in rows
    ]


# --- Poids ---
@app.post("/api/weight")
def log_weight(body: LogWeight, user: dict = Depends(get_current_user)):
    entry_date = body.date or date.today().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO weights (user_id, date, weight_kg, created_at) VALUES (?, ?, ?, ?)",
        (user["id"], entry_date, body.weight_kg, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/weight")
def list_weights(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT date, weight_kg FROM weights WHERE user_id = ? ORDER BY date ASC", (user["id"],)
    ).fetchall()
    conn.close()
    return [{"date": r["date"], "weight_kg": r["weight_kg"]} for r in rows]


# --- Stats (pour le dashboard et pour n8n) ---
@app.get("/api/stats")
def stats(user: dict = Depends(get_current_user)):
    conn = get_db()
    sessions = conn.execute(
        "SELECT date, exercises_json FROM sessions WHERE user_id = ? ORDER BY date ASC", (user["id"],)
    ).fetchall()
    weights = conn.execute(
        "SELECT date, weight_kg FROM weights WHERE user_id = ? ORDER BY date ASC", (user["id"],)
    ).fetchall()
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


# --- Fichiers statiques (PWA) — publics : l'app shell ne contient rien de sensible,
# c'est la connexion côté frontend (via l'API) qui gère l'accès aux données ---
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/manifest.json")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.json")


@app.get("/service-worker.js")
def sw():
    return FileResponse(STATIC_DIR / "service-worker.js", media_type="application/javascript")
