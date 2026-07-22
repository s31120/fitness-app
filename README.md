# Fitness Coach — PWA + n8n

Application de suivi fitness installable sur iPhone (PWA, sans App Store) : programme
d'entraînement (templates prêts à l'emploi), cases à cocher par exercice, suivi de poids,
dashboard de progression — et un coach virtuel qui envoie des messages motivants en français sur
Discord (félicitations après séance, rappel du soir, bilan hebdomadaire).

## Architecture

```
PWA (iPhone, ajoutée à l'écran d'accueil)
     │  fetch API (même origine, auth basique)
     ▼
Backend FastAPI + SQLite ──── webhook ───▶ n8n ──▶ Discord (messages motivants)
     (programme, séances,                    │
      poids, stats)                          ├── déclenché à chaque séance loggée (félicitations)
                                              ├── cron quotidien (rappel si pas de séance)
                                              └── cron hebdo (bilan + citation motivante)
```

Deux conteneurs (`docker-compose`) : le backend (API + fichiers de la PWA) et n8n (automatisation).
Pas de base de données séparée — SQLite suffit pour un usage personnel.

## 1. Installation serveur

```bash
git clone <url-de-ce-repo>
cd fitness-app

cp .env.example .env
nano .env   # renseigne APP_USER/PASSWORD, N8N_BASIC_AUTH_*, DISCORD_WEBHOOK_URL

chmod +x deploy.sh
./deploy.sh
```

## 2. Discord

Crée un webhook (`Paramètres du salon → Intégrations → Webhooks`), copie l'URL dans `.env`
(`DISCORD_WEBHOOK_URL`).

## 3. Importer le workflow n8n

Ouvre `http://<IP_SERVEUR>:5681`, connecte-toi (`N8N_BASIC_AUTH_USER`/`PASSWORD`),
**Workflows → Import from File** → `n8n/workflow.json`.

**Active le webhook** : ouvre le node "Séance terminée (webhook)", note l'URL de production
affichée (ex. `http://n8n:5678/webhook/session-done` en interne au réseau Docker — c'est déjà la
valeur par défaut dans `.env.example`, à ajuster seulement si tu changes le path). Publie le
workflow.

## 4. Installer la PWA sur iPhone

1. Ouvre `http://<IP_SERVEUR>:8000` dans **Safari** (pas Chrome — l'ajout à l'écran d'accueil en
   mode PWA fonctionne mieux depuis Safari sur iOS)
2. Connecte-toi avec `APP_USER`/`APP_PASSWORD`
3. Bouton **Partager** → **Sur l'écran d'accueil**
4. L'app s'ouvre ensuite en plein écran, comme une app native

## 5. Choisir ton programme

Dans l'app, onglet **Programme** → choisis un template (Push/Pull/Legs, Upper/Lower, ou Full
Body). L'onglet **Aujourd'hui** affiche alors la séance du jour (rotation automatique basée sur
le nombre de séances déjà loggées).

## Structure du projet

```
backend/
  main.py               # API FastAPI (programme, séances, poids, stats, auth basique)
  templates_data.py      # les 3 programmes prédéfinis
  static/                 # la PWA (HTML/CSS/JS, manifest, service worker, icônes)
  requirements.txt
  Dockerfile
n8n/
  workflow.json            # webhook félicitations + rappel du soir + bilan hebdo
docker-compose.yml           # backend + n8n
deploy.sh
.env.example
```

## Notes

- Auth : une seule paire identifiant/mot de passe protège toute l'app (usage mono-utilisateur —
  pas de système de comptes multiples).
- Le calcul du "prochain jour" de la rotation est simple : `nombre de séances loggées % nombre de
  jours du programme`. Si tu sautes des jours, ça ne "rattrape" pas — ça avance juste séance après
  séance, ce qui reste le comportement le plus intuitif pour ce genre de split.
- Le volume d'entraînement est calculé comme `séries × répétitions × poids`, une métrique standard
  en musculation pour suivre la progression globale.
- Ce n'est pas une app iOS native (pas de distribution App Store) — c'est une PWA, qui couvre le
  même besoin (icône, plein écran, utilisable au quotidien) sans compte développeur Apple ni
  compilation native.

## Pistes d'évolution

- Authentification par utilisateur si tu veux la partager avec quelqu'un d'autre
- Export des données (CSV) pour analyse externe
- Calcul de 1RM estimé (formule d'Epley) par exercice
- Notifications push natives (nécessite un service worker plus poussé + clé VAPID)
