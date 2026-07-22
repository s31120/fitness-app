#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "❌ Copie .env.example en .env et renseigne les valeurs avant de lancer ce script."
  exit 1
fi

echo "→ Build et lancement des conteneurs (backend + n8n)..."
docker compose up -d --build

echo "✅ Terminé."
echo "   App fitness  : http://<IP_SERVEUR>:8000"
echo "   Interface n8n : http://<IP_SERVEUR>:5681"
echo ""
echo "N'oublie pas d'importer n8n/workflow.json dans n8n, et de vérifier l'URL du"
echo "webhook 'Séance terminée' pour la mettre à jour dans .env (N8N_WEBHOOK_URL) si besoin."
