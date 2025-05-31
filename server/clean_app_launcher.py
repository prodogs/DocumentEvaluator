#!/usr/bin/env python3
"""
Clean Application Launcher

A clean version of the app launcher that avoids SQLAlchemy model conflicts
by ensuring proper import order and model registration.
"""

import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    CORS(app)
    
    # Initialize database and models first
    try:
        logger.info("Initializing database and models...")
        from database import Base, engine
        
        # Import all models to register them (temporarily reduced due to missing models)
        from models import (
            Batch, Folder, Doc, Document, Prompt,
            LlmConfiguration, LlmResponse, BatchArchive
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database and models initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise
    
    # Add health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'ok',
            'version': '1.0.0',
            'message': 'Clean app launcher is working!'
        })
    
    # Register blueprints in order (minimal set to avoid conflicts)
    try:
        # Register connection management routes (our new feature)
        logger.info("Registering connection management routes...")
        from api.connection_routes import connection_bp
        app.register_blueprint(connection_bp)

        # Register LLM provider management routes
        logger.info("Registering LLM provider routes...")
        from api.llm_provider_routes import llm_provider_bp
        app.register_blueprint(llm_provider_bp)

        # Register model management routes
        logger.info("Registering model routes...")
        from api.model_routes import model_bp
        app.register_blueprint(model_bp)

        # Skip other routes for now to isolate the connection system
        logger.info("✅ Core routes registered successfully")

    except Exception as e:
        logger.error(f"❌ Error registering routes: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return app

def main():
    """Main function to launch the application"""
    try:
        logger.info("🚀 Starting Clean Document Processor API...")
        
        # Create the Flask app
        app = create_app()
        
        # Get port from environment or use default
        port = int(os.getenv('PORT', 5001))
        
        # Print registered routes for debugging
        logger.info("📍 Registered Routes:")
        for rule in app.url_map.iter_rules():
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            if methods:
                logger.info(f"  {methods:20s} {rule.rule}")
        
        logger.info(f"🌐 Starting server on port {port}")
        logger.info(f"🔗 Connection management available at http://localhost:{port}/api/connections")
        
        # Run the Flask app
        app.run(host='0.0.0.0', port=port, debug=True)
        
    except Exception as e:
        logger.error(f"❌ Error starting application: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
