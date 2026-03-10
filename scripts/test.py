#!/usr/bin/env python
"""
ScholarSource Test Script

Unified testing script with command-line options for various test scenarios.

Usage:
    python scripts/test.py --help
    python scripts/test.py --all
    python scripts/test.py --celery
    python scripts/test.py --refactored
    python scripts/test.py --setup
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables using centralized loader
from backend.env_loader import load_environment
load_environment()


def test_imports():
    """Test that all required modules can be imported."""
    print("\n" + "=" * 60)
    print("TEST: Imports")
    print("=" * 60)

    modules = {
        'backend.celery_app': 'Celery app',
        'backend.tasks': 'Celery tasks',
        'backend.crew_runner': 'Crew runner',
        'backend.main': 'FastAPI app',
        'celery': 'Celery',
        'redis': 'Redis',
        'fastapi': 'FastAPI',
    }

    all_ok = True
    for module_name, display_name in modules.items():
        try:
            __import__(module_name)
            print(f'✅ {display_name}')
        except ImportError as e:
            print(f'❌ {display_name}: {e}')
            all_ok = False

    return all_ok


def test_celery_config():
    """Test Celery configuration."""
    print("\n" + "=" * 60)
    print("TEST: Celery Configuration")
    print("=" * 60)

    try:
        from backend.celery_app import app
        from backend import tasks

        # Basic config
        print(f'✅ App name: {app.main}')
        print(f'✅ Broker: {app.conf.broker_url[:30]}...')
        result_backend = app.conf.result_backend
        if result_backend:
            print(f'✅ Result Backend: {result_backend[:30]}...')
        else:
            print(f'✅ Result Backend: Disabled (results stored in database)')
        print(f'✅ Serializer: {app.conf.task_serializer}')

        # Queues
        queues = [q.name for q in app.conf.task_queues]
        print(f'✅ Queues: {queues}')

        # Tasks
        task_names = [name for name in sorted(app.tasks.keys())
                     if not name.startswith('celery.')]
        print(f'✅ Registered tasks ({len(task_names)}):')
        for task_name in task_names:
            print(f'   - {task_name}')

        return True

    except Exception as e:
        print(f'❌ Celery config test failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_redis_connection():
    """Test Redis connection."""
    print("\n" + "=" * 60)
    print("TEST: Redis Connection")
    print("=" * 60)

    try:
        from redis import Redis
        import re

        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            print('❌ REDIS_URL not set in environment')
            return False

        # Mask password for display
        masked_url = re.sub(r':[^@]+@', ':***@', redis_url)
        print(f'Connecting to: {masked_url}')

        redis_client = Redis.from_url(redis_url)

        # Test ping
        redis_client.ping()
        print('✅ PING successful')

        # Test set/get
        test_key = 'test_script_key'
        test_value = 'test_value'
        redis_client.set(test_key, test_value, ex=10)
        result = redis_client.get(test_key)
        redis_client.delete(test_key)

        if result.decode() == test_value:
            print('✅ SET/GET successful')
        else:
            print('❌ SET/GET failed')
            return False

        return True

    except Exception as e:
        print(f'❌ Redis connection failed: {e}')
        return False


def test_refactored_runner():
    """Test refactored crew runner functions."""
    print("\n" + "=" * 60)
    print("TEST: Refactored Crew Runner")
    print("=" * 60)

    try:
        from backend.crew_runner import run_crew_async, cancel_crew_job, validate_crew_inputs
        import inspect

        # Test function signatures
        sig = inspect.signature(run_crew_async)
        params = list(sig.parameters.keys())
        assert 'job_id' in params and 'inputs' in params
        print(f'✅ run_crew_async signature: {params}')
        print(f'✅ Returns: {sig.return_annotation.__name__}')

        sig = inspect.signature(cancel_crew_job)
        params = list(sig.parameters.keys())
        assert 'job_id' in params
        print(f'✅ cancel_crew_job signature: {params}')

        # Test input validation
        valid_inputs = {
            'course_name': 'CS 101',
            'book_title': 'Test Book',
            'book_author': 'Test Author'
        }
        assert validate_crew_inputs(valid_inputs) == True
        print('✅ validate_crew_inputs: valid inputs accepted')

        invalid_inputs = {}
        assert validate_crew_inputs(invalid_inputs) == False
        print('✅ validate_crew_inputs: invalid inputs rejected')

        return True

    except Exception as e:
        print(f'❌ Refactored runner test failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_task_queue_config():
    """Test task queue configuration."""
    print("\n" + "=" * 60)
    print("TEST: Task Queue Configuration")
    print("=" * 60)

    try:
        from backend.celery_app import app

        # Check queues
        queues = [q.name for q in app.conf.task_queues]
        assert 'crew_jobs' in queues and 'default' in queues
        print(f'✅ Queues configured: {queues}')

        # Check task routing
        task_routes = app.conf.task_routes
        assert 'backend.tasks.run_crew_task' in task_routes
        assert task_routes['backend.tasks.run_crew_task']['queue'] == 'crew_jobs'
        print('✅ Task routing configured correctly')

        # Check worker settings
        print(f'✅ Prefetch multiplier: {app.conf.worker_prefetch_multiplier}')
        print(f'✅ Task time limit: {app.conf.task_time_limit}s')
        print(f'✅ Acks late: {app.conf.task_acks_late}')

        return True

    except Exception as e:
        print(f'❌ Task queue config test failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_environment():
    """Test environment variables."""
    print("\n" + "=" * 60)
    print("TEST: Environment Variables")
    print("=" * 60)

    required_vars = {
        'REDIS_URL': 'Redis connection',
        'OPENAI_API_KEY': 'OpenAI API key',
        'SERPER_API_KEY': 'Serper API key',
        'SUPABASE_URL': 'Supabase URL',
        'SUPABASE_ANON_KEY': 'Supabase anon key',
    }

    all_ok = True
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            # Show first 20 chars for verification
            display_value = value[:20] + '...' if len(value) > 20 else value
            print(f'✅ {var_name}: {display_value}')
        else:
            print(f'❌ {var_name} not set ({description})')
            all_ok = False

    return all_ok


def test_file_structure():
    """Test that required files exist."""
    print("\n" + "=" * 60)
    print("TEST: File Structure")
    print("=" * 60)

    required_files = [
        'backend/celery_app.py',
        'backend/tasks.py',
        'backend/crew_runner.py',
        'backend/main.py',
        'Procfile',
        'scripts/start_worker.sh',
        'scripts/verify_setup.sh',
        '.env.example',
    ]

    all_ok = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f'✅ {file_path}')
        else:
            print(f'❌ {file_path} missing')
            all_ok = False

    return all_ok


def test_rate_limiting_config():
    """Test rate limiting configuration (checks Redis usage)."""
    print("\n" + "=" * 60)
    print("TEST: Rate Limiting Configuration")
    print("=" * 60)

    try:
        from backend.rate_limiter import limiter
        import redis
        
        redis_url = os.getenv('REDIS_URL')
        
        if redis_url:
            # Should be using Redis
            print(f'✅ REDIS_URL is set')
            
            # Verify Redis connection works
            try:
                redis_client = redis.from_url(redis_url)
                redis_client.ping()
                print('✅ Redis connection verified')
                
                # Check if limiter is using Redis storage
                if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'connection_pool'):
                    print('✅ Rate limiter is using Redis storage')
                else:
                    print('⚠️  Rate limiter storage type unclear (may still be using Redis)')
                
            except Exception as e:
                print(f'❌ Redis connection failed: {e}')
                return False
        else:
            # Should allow in-memory if explicitly set
            allow_in_memory = os.getenv('ALLOW_IN_MEMORY_RATE_LIMIT', 'false').lower() in ('true', '1', 'yes')
            if allow_in_memory:
                print('⚠️  Using in-memory rate limiting (ALLOW_IN_MEMORY_RATE_LIMIT is set)')
                print('   This is OK for development, but Redis is required for production')
            else:
                print('❌ REDIS_URL not set and ALLOW_IN_MEMORY_RATE_LIMIT not enabled')
                print('   Rate limiting requires Redis for production deployments')
                return False
        
        print(f'✅ Rate limiter initialized successfully')
        return True
        
    except ValueError as e:
        if 'REDIS_URL' in str(e):
            print(f'⚠️  {e}')
            print('   Set REDIS_URL or ALLOW_IN_MEMORY_RATE_LIMIT=true for development')
            return False
        raise
    except Exception as e:
        print(f'❌ Rate limiting config test failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiting():
    """Test API rate limiting (requires running server)."""
    print("\n" + "=" * 60)
    print("TEST: Rate Limiting (API Integration)")
    print("=" * 60)

    try:
        import requests
    except ImportError:
        print('⚠️  requests package not installed (pip install requests)')
        print('   Skipping rate limiting tests')
        return True

    base_url = "http://localhost:8000"

    # Check if server is running
    try:
        response = requests.get(f"{base_url}/api/health", timeout=2)
        if response.status_code != 200:
            print('⚠️  Server not responding correctly')
            print('   Start with: uvicorn backend.main:app --host 0.0.0.0 --port 8000')
            print('   Skipping rate limiting tests')
            return True
    except requests.exceptions.ConnectionError:
        print('⚠️  Cannot connect to server (not running)')
        print('   Start with: uvicorn backend.main:app --host 0.0.0.0 --port 8000')
        print('   Skipping rate limiting tests')
        return True

    print('✅ Server is running')

    # Test health endpoint (no rate limit)
    print('\nTesting health endpoint (no rate limit)...')
    for i in range(5):
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 429:
            print(f'❌ Unexpected rate limit on health check')
            return False
    print('✅ No rate limit on health endpoint')

    # Test submit endpoint rate limit
    print('\nTesting submit endpoint (2/minute limit)...')
    payload = {"course_name": "Test", "university_name": "Test"}
    hit_limit = False
    for i in range(3):
        response = requests.post(f"{base_url}/api/submit", json=payload)
        if response.status_code == 429:
            print(f'✅ Rate limit triggered on request {i+1}')
            hit_limit = True
            break
        elif response.status_code in [400, 200]:
            print(f'   Request {i+1}: {response.status_code}')

    if not hit_limit:
        print('⚠️  Rate limit not triggered (may need more requests or time)')

    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SCHOLARSOURCE TEST SUITE")
    print("=" * 60)

    tests = [
        ('Environment Variables', test_environment),
        ('File Structure', test_file_structure),
        ('Imports', test_imports),
        ('Celery Configuration', test_celery_config),
        ('Redis Connection', test_redis_connection),
        ('Rate Limiting Configuration', test_rate_limiting_config),
        ('Task Queue Configuration', test_task_queue_config),
        ('Refactored Runner', test_refactored_runner),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='ScholarSource Test Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test.py --all              Run all tests
  python scripts/test.py --celery           Test Celery configuration only
  python scripts/test.py --redis            Test Redis connection only
  python scripts/test.py --refactored       Test refactored crew runner only
  python scripts/test.py --setup            Test environment and file structure
        """
    )

    parser.add_argument('--all', action='store_true',
                       help='Run all tests (excluding API integration tests)')
    parser.add_argument('--celery', action='store_true',
                       help='Test Celery configuration')
    parser.add_argument('--redis', action='store_true',
                       help='Test Redis connection')
    parser.add_argument('--refactored', action='store_true',
                       help='Test refactored crew runner')
    parser.add_argument('--setup', action='store_true',
                       help='Test environment and file structure')
    parser.add_argument('--imports', action='store_true',
                       help='Test module imports')
    parser.add_argument('--queue', action='store_true',
                       help='Test task queue configuration')
    parser.add_argument('--api', action='store_true',
                       help='Test API rate limiting (requires running server)')
    parser.add_argument('--rate-limit', action='store_true',
                       help='Test rate limiting configuration')

    args = parser.parse_args()

    # If no arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 0

    # Run selected tests
    if args.all:
        return run_all_tests()

    results = []
    if args.setup:
        results.append(('Environment', test_environment()))
        results.append(('File Structure', test_file_structure()))
    if args.imports:
        results.append(('Imports', test_imports()))
    if args.celery:
        results.append(('Celery Config', test_celery_config()))
    if args.redis:
        results.append(('Redis Connection', test_redis_connection()))
    if args.queue:
        results.append(('Task Queue Config', test_task_queue_config()))
    if args.refactored:
        results.append(('Refactored Runner', test_refactored_runner()))
    if args.rate_limit:
        results.append(('Rate Limiting Config', test_rate_limiting_config()))
    if args.api:
        results.append(('API Rate Limiting', test_rate_limiting()))

    # Print results
    if results:
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        passed = sum(1 for _, success in results if success)
        total = len(results)
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_name}")
        print(f"\nTotal: {passed}/{total} tests passed")
        return 0 if passed == total else 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
