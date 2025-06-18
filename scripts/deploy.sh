#!/bin/bash
# Deploy script for ai-conditioner-discord bot

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin main

# Install/update dependencies
echo "📦 Updating dependencies..."
pip install -r requirements.txt

# Restart the bot
echo "🔄 Restarting bot..."
sudo systemctl restart conditioner

echo "✅ Deployment complete!"
echo "Check status with: sudo systemctl status conditioner"