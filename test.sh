#!/bin/bash

echo "🧪 Running Eclipse Shield Security Tests"
echo "========================================"

# Wait for service to be ready
echo "Waiting for service to start..."
sleep 5

# I give the service five seconds and then test whether it came up or
# not. On a slow first Docker build that is not enough time, and a fail
# here can mean still building rather than broken. I check status.sh
# before I trust a fail from this script.
# Run security tests
if [ -f "security_test.py" ]; then
    python3 security_test.py http://localhost:5000
else
    echo "❌ security_test.py not found"
fi
