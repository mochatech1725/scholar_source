#!/bin/bash
# Test Celery configuration before deploying to Railway

set -e

echo "🧪 Testing Celery Configuration..."
echo "=================================="
echo ""

# Test 1: Environment variables
echo "1️⃣  Checking environment variables..."
if [ -z "$REDIS_URL" ]; then
    echo "   ⚠️  REDIS_URL not set (will use default: redis://localhost:6379/0)"
    export REDIS_URL="redis://localhost:6379/0"
else
    echo "   ✅ REDIS_URL: ${REDIS_URL:0:40}..."
fi
echo ""

# Test 2: Import Celery app
echo "2️⃣  Testing Celery app import..."
python -c "
from backend.celery_app import app
print('   ✅ Celery app imported successfully')
print(f'   📋 Broker: {app.conf.broker_url[:40]}...')
result_backend = app.conf.result_backend
if result_backend:
    print(f'   📋 Result Backend: {result_backend[:40]}...')
else:
    print('   📋 Result Backend: Disabled (results stored in database)')
" || {
    echo "   ❌ Failed to import Celery app"
    exit 1
}
echo ""

# Test 3: Test task import
echo "3️⃣  Testing task import..."
python -c "
from backend.tasks import run_crew_task
print('   ✅ run_crew_task imported successfully')
" || {
    echo "   ❌ Failed to import tasks"
    exit 1
}
echo ""

# Test 4: Redis connection
echo "4️⃣  Testing Redis connection..."
python -c "
import redis
import os
url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
try:
    r = redis.from_url(url)
    r.ping()
    print('   ✅ Redis connection successful')
except Exception as e:
    print(f'   ❌ Redis connection failed: {e}')
    print('   ℹ️  Make sure Redis is running (locally: redis-server)')
    exit(1)
" || exit 1
echo ""

# Test 5: Celery inspect
echo "5️⃣  Testing Celery inspect (requires running worker)..."
python -c "
from backend.celery_app import app
try:
    stats = app.control.inspect().stats()
    if stats:
        print(f'   ✅ Found {len(stats)} active worker(s)')
        for worker, stat in stats.items():
            print(f'      Worker: {worker}')
    else:
        print('   ⚠️  No active workers found')
        print('      Start a worker with: celery -A backend.celery_app worker --loglevel=info')
except Exception as e:
    print(f'   ⚠️  Could not connect to workers: {e}')
    print('      (This is OK if no worker is running yet)')
" || true
echo ""

echo "=================================="
echo "✅ All critical tests passed!"
echo ""
echo "Next steps:"
echo "  1. Start worker: celery -A backend.celery_app worker --loglevel=info"
echo "  2. Test task: python -c 'from backend.tasks import run_crew_task; result = run_crew_task.delay(\"test\", {\"course_url\": \"https://example.com\"}); print(result.id)'"
echo ""
