#!/bin/bash

echo "🚀 Starting Eclipse Shield (Secure Local Mode)"
echo "=============================================="

# Load environment variables
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
fi

# I read .env.local from the folder I am run in, and the compose file is
# a relative path too, so this script only works from the repo root. I
# run it there. From anywhere else it starts nothing and the health
# address below stays silent.
# Start services
if command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f docker-compose.local.yml up -d
else
    docker compose -f docker-compose.local.yml up -d
fi

echo ""
echo "✅ Eclipse Shield is starting up..."
echo "🌐 Access URL: http://localhost:5000"
echo "❤️  Health Check: http://localhost:5000/health"
echo ""
echo "📋 Useful commands:"
echo "   ./stop.sh       - Stop all services"
echo "   ./logs.sh       - View application logs"
echo "   ./status.sh     - Check service status"
echo "   ./test.sh       - Run security tests"
