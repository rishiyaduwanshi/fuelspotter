#!/bin/bash
set -e
set -o pipefail

APP_DIR=/root/fuelspotter
DEPLOY_LOG="$APP_DIR/deploy.log"
GUNI_ERR="$APP_DIR/gunicorn-error.log"
GUNI_ACC="$APP_DIR/gunicorn-access.log"

# Ensure mise python tools are usable in CI/cron
export PATH="/root/.local/share/mise/installs/python/3.14.2/bin:$PATH"

echo "=====================================" | tee -a "$DEPLOY_LOG"
echo "🚀 Starting deployment..." | tee -a "$DEPLOY_LOG"
echo "Time: $(date)" | tee -a "$DEPLOY_LOG"
echo "=====================================" | tee -a "$DEPLOY_LOG"

# ---- Go inside project ----
cd "$APP_DIR"

# ---- GIT (safe automation pattern) ----
echo "📥 Syncing with GitHub (safe method)..." | tee -a "$DEPLOY_LOG"

git fetch origin main 2>&1 | tee -a "$DEPLOY_LOG"
git reset --hard origin/main 2>&1 | tee -a "$DEPLOY_LOG"

# Create a virtual env and activate it 
python -m venv venv 
source venv/bin/activate

# ---- Python deps ----
echo "📦 Installing / updating dependencies..." | tee -a "$DEPLOY_LOG"
pip install -r requirements.txt \
  2>&1 | tee -a "$DEPLOY_LOG"

# ---- Gunicorn restart ----
echo "🔄 Restarting Gunicorn..." | tee -a "$DEPLOY_LOG"

pkill -f "gunicorn fuelspotter.wsgi:application" || true
sleep 1

/root/.local/share/mise/installs/python/3.14.2/bin/gunicorn fuelspotter.wsgi:application \
  --bind 127.0.0.1:8485 \
  --workers 2 \
  --timeout 120 \
  --daemon \
  --error-logfile "$GUNI_ERR" \
  --access-logfile "$GUNI_ACC"

echo "✅ Deployment completed successfully!" | tee -a "$DEPLOY_LOG"