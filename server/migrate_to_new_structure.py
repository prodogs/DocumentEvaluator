#!/usr/bin/env python3
"""
Migration script to update app.py to use the new modular structure

This script demonstrates how to use the new architecture.
"""

import os
import shutil
from datetime import datetime


def backup_original():
    """Backup original app.py"""
    if os.path.exists('app.py'):
        backup_name = f'app.py.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2('app.py', backup_name)
        print(f"✅ Backed up app.py to {backup_name}")
        return True
    return False


def create_new_app_py():
    """Create new app.py that uses the modular structure"""
    
    new_app_content = '''#!/usr/bin/env python3
"""
DocumentEvaluator Server Application

This is the main entry point for the DocumentEvaluator server.
It uses the new modular architecture defined in app/main.py
"""

import os
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import create_app, register_cli_commands, register_admin_routes
from app.core.logger import get_logger

# Create application
app = create_app(os.environ.get('FLASK_ENV', 'development'))

# Register CLI commands
register_cli_commands(app)

# Register admin routes (development only)
if app.debug:
    register_admin_routes(app)

# Get logger
logger = get_logger(__name__)

if __name__ == '__main__':
    # Log startup
    logger.info("=" * 50)
    logger.info("Starting DocumentEvaluator Server")
    logger.info(f"Environment: {app.config.get('ENV', 'default')}")
    logger.info(f"Debug Mode: {app.debug}")
    logger.info(f"Host: {app.config['HOST']}")
    logger.info(f"Port: {app.config['PORT']}")
    logger.info("=" * 50)
    
    # Run the application
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG'],
        use_reloader=app.config['DEBUG']
    )
'''
    
    with open('app_new.py', 'w') as f:
        f.write(new_app_content)
    
    print("✅ Created new app_new.py using modular structure")
    print("   Test it with: python app_new.py")
    print("   If it works, rename it to app.py")


def create_env_example():
    """Create example environment file"""
    
    env_content = '''# DocumentEvaluator Environment Configuration

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Server Configuration
HOST=0.0.0.0
PORT=5001

# Database Configuration
DATABASE_URL=postgresql://postgres:prodogs03@studio.local:5432/doc_eval
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0
CACHE_TIMEOUT=300

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log

# Performance Settings
ENABLE_ASYNC=true
CONNECTION_POOL_SIZE=100
REQUEST_TIMEOUT=30
MAX_CONCURRENT_TASKS=30

# Rate Limiting (production only)
RATELIMIT_ENABLED=false
RATELIMIT_DEFAULT=100/hour

# SSL (production only)
SSL_REDIRECT=false
'''
    
    with open('.env.example', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env.example file")
    print("   Copy it to .env and update with your settings")


def create_startup_script():
    """Create improved startup script"""
    
    script_content = '''#!/bin/bash
# Improved startup script for DocumentEvaluator

echo "🚀 Starting DocumentEvaluator Server..."

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "📦 Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

# Check Redis connection (optional)
echo "🔍 Checking Redis connection..."
python3 -c "
import redis
try:
    r = redis.from_url('redis://localhost:6379')
    r.ping()
    print('✅ Redis is available')
except:
    print('⚠️  Redis not available - using in-memory cache')
"

# Check database connection
echo "🔍 Checking database connection..."
python3 -c "
from app.core.database import db_manager
if db_manager.health_check():
    print('✅ Database connection successful')
else:
    print('❌ Database connection failed')
    exit(1)
"

# Run migrations if using Alembic
if [ -f "alembic.ini" ]; then
    echo "🔧 Running database migrations..."
    alembic upgrade head
fi

# Start the server
echo "🚀 Starting server..."
if [ "$FLASK_ENV" = "production" ]; then
    # Production: use gunicorn
    gunicorn -w 4 -k gevent --timeout 120 -b 0.0.0.0:5001 app:app
else
    # Development: use Flask development server
    python3 app.py
fi
'''
    
    with open('start_server.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('start_server.sh', 0o755)
    print("✅ Created start_server.sh script")


def main():
    """Run migration steps"""
    print("🔄 Migrating to new modular structure...")
    print()
    
    # Step 1: Backup original
    backup_original()
    
    # Step 2: Create new app.py
    create_new_app_py()
    
    # Step 3: Create environment example
    create_env_example()
    
    # Step 4: Create startup script
    create_startup_script()
    
    print()
    print("✅ Migration preparation complete!")
    print()
    print("Next steps:")
    print("1. Install new dependencies: pip install -r requirements.txt")
    print("2. Copy .env.example to .env and update settings")
    print("3. Test the new structure: python app_new.py")
    print("4. If successful, replace app.py with app_new.py")
    print("5. Use ./start_server.sh to start the server")
    print()
    print("Benefits of the new structure:")
    print("- ✨ Structured logging with request tracking")
    print("- 🚀 Async support for better performance")
    print("- 💾 Redis caching for improved response times")
    print("- 🛡️ Better error handling and monitoring")
    print("- 📊 Performance tracking and metrics")
    print("- 🔧 Cleaner, more maintainable code")


if __name__ == '__main__':
    main()