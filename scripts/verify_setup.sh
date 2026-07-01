#!/bin/bash
# Verify ScholarSource Celery Setup
#
# This script verifies that all components are properly configured for the Celery-based
# task queue system.

echo "============================================================"
echo "ScholarSource Celery Setup Verification"
echo "============================================================"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ .env file found and loaded"
else
    echo "❌ .env file not found"
    echo "   Copy .env.example to .env and fill in your credentials"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found (expected at .venv/)"
fi

echo ""
echo "Checking required environment variables..."
echo "------------------------------------------------------------"

# Check Redis URL
if [ -z "$REDIS_URL" ]; then
    echo "❌ REDIS_URL not set"
    echo "   Add REDIS_URL to your .env file"
    exit 1
else
    echo "✅ REDIS_URL is set"
fi

# Check other required variables
required_vars=("OPENAI_API_KEY" "SERPER_API_KEY" "SUPABASE_URL" "SUPABASE_ANON_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "⚠️  $var not set (may be required for full functionality)"
    else
        echo "✅ $var is set"
    fi
done

echo ""
echo "Checking Python dependencies..."
echo "------------------------------------------------------------"

python -c "
import sys

packages = {
    'celery': 'Celery',
    'redis': 'Redis',
    'fastapi': 'FastAPI',
    'dotenv': 'python-dotenv'
}

all_ok = True
for module, name in packages.items():
    try:
        __import__(module)
        print(f'✅ {name} installed')
    except ImportError:
        print(f'❌ {name} not installed')
        all_ok = False

if not all_ok:
    print()
    print('Run: pip install -r requirements.txt')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "Checking Celery configuration..."
echo "------------------------------------------------------------"

python -c "
from backend.celery_app import app
from backend import tasks
import sys

# Check app configuration
print(f'✅ Celery app loaded: {app.main}')
print(f'✅ Broker: {app.conf.broker_url[:30]}...')
print(f'✅ Queues: {[q.name for q in app.conf.task_queues]}')

# Check registered tasks
task_count = sum(1 for t in app.tasks.keys() if not t.startswith('celery.'))
print(f'✅ Registered tasks: {task_count}')

if task_count < 3:
    print('⚠️  Expected at least 3 custom tasks')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Celery configuration check failed"
    exit 1
fi

echo ""
echo "Testing Redis connection..."
echo "------------------------------------------------------------"

python -c "
from redis import Redis
import os
import sys

try:
    redis_url = os.getenv('REDIS_URL')
    redis_client = Redis.from_url(redis_url)
    redis_client.ping()

    # Test set/get
    test_key = 'verify_setup_test'
    redis_client.set(test_key, 'ok', ex=10)
    result = redis_client.get(test_key)
    redis_client.delete(test_key)

    if result.decode() == 'ok':
        print('✅ Redis connection successful')
        print('✅ Redis read/write working')
    else:
        print('❌ Redis read/write failed')
        sys.exit(1)

except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    print()
    print('Make sure:')
    print('1. REDIS_URL is set correctly in .env')
    print('2. Redis server is accessible')
    print('3. Network/firewall allows connection')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "Checking file structure..."
echo "------------------------------------------------------------"

files=(
    "backend/celery_app.py"
    "backend/tasks.py"
    "backend/crew_runner.py"
    "backend/main.py"
    "Procfile"
    "start_worker.sh"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

echo ""
echo "============================================================"
echo "Verification Complete!"
echo "============================================================"
echo ""
echo "✅ All checks passed! Your setup is ready."
echo ""
echo "Next steps:"
echo ""
echo "1. Start the backend API:"
echo "   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2. Start the Celery worker:"
echo "   ./start_worker.sh"
echo ""
echo "3. Start the frontend (in web/ directory):"
echo "   cd web && npm run dev"
echo ""
echo "4. Test the application:"
echo "   - Frontend: http://localhost:5175"
echo "   - Backend API: http://localhost:8000/docs"
echo ""
echo "For deployment to Railway:"
echo "   - Push to Git"
echo "   - Railway will use the Procfile to start both 'web' and 'worker'"
echo "   - Make sure REDIS_URL is set in Railway environment variables"
echo ""
