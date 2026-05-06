#!/bin/bash

set -e
set -o pipefail

APP_DIR=/root/fuelspotter

DEPLOY_LOG="$APP_DIR/deploy.log"
GUNI_ERR="$APP_DIR/gunicorn-error.log"
GUNI_ACC="$APP_DIR/gunicorn-access.log"

PORT=8454

echo "=====================================" | tee -a "$DEPLOY_LOG"
echo "🚀 Starting deployment..." | tee -a "$DEPLOY_LOG"
echo "🕒 Time: $(date)" | tee -a "$DEPLOY_LOG"
echo "=====================================" | tee -a "$DEPLOY_LOG"

# --------------------------------------------------
# Go to project directory
# --------------------------------------------------

cd "$APP_DIR"

# --------------------------------------------------
# Git sync
# --------------------------------------------------

echo "📥 Syncing latest code from GitHub..." | tee -a "$DEPLOY_LOG"

git fetch origin main 2>&1 | tee -a "$DEPLOY_LOG"

git reset --hard origin/main 2>&1 | tee -a "$DEPLOY_LOG"

# --------------------------------------------------
# Activate virtual environment
# --------------------------------------------------

echo "🐍 Activating virtual environment..." | tee -a "$DEPLOY_LOG"

source venv/bin/activate

# --------------------------------------------------
# Install dependencies
# --------------------------------------------------

echo "📦 Installing dependencies..." | tee -a "$DEPLOY_LOG"

pip install -r requirements.txt 2>&1 | tee -a "$DEPLOY_LOG"

# --------------------------------------------------
# Django migrations
# --------------------------------------------------

echo "🗃 Running migrations..." | tee -a "$DEPLOY_LOG"

python manage.py migrate 2>&1 | tee -a "$DEPLOY_LOG"

# --------------------------------------------------
# Collect static files
# --------------------------------------------------

echo "🎨 Collecting static files..." | tee -a "$DEPLOY_LOG"

python manage.py collectstatic --noinput 2>&1 | tee -a "$DEPLOY_LOG"

# --------------------------------------------------
# Restart Gunicorn
# --------------------------------------------------

echo "🔄 Restarting Gunicorn..." | tee -a "$DEPLOY_LOG"

pkill -f "gunicorn fuelspotter.wsgi:application" || true

sleep 2

# IMPORTANT:
# Use VENV gunicorn, not global gunicorn

venv/bin/gunicorn fuelspotter.wsgi:application \
    --bind 127.0.0.1:$PORT \
    --workers 2 \
    --timeout 120 \
    --daemon \
    --error-logfile "$GUNI_ERR" \
    --access-logfile "$GUNI_ACC"

sleep 3

# --------------------------------------------------
# Health check
# --------------------------------------------------

echo "🩺 Checking Gunicorn health..." | tee -a "$DEPLOY_LOG"

if curl -s http://127.0.0.1:$PORT > /dev/null; then
    echo "✅ Gunicorn is running successfully!" | tee -a "$DEPLOY_LOG"
else
    echo "❌ Gunicorn failed to start!" | tee -a "$DEPLOY_LOG"
    echo "📄 Check logs: $GUNI_ERR" | tee -a "$DEPLOY_LOG"
    exit 1
fi

echo "=====================================" | tee -a "$DEPLOY_LOG"
echo "🎉 Deployment completed successfully!" | tee -a "$DEPLOY_LOG"
echo "=====================================" | tee -a "$DEPLOY_LOG"