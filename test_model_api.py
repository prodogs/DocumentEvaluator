#!/usr/bin/env python3
"""
Test model API endpoints
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from flask import Flask
from flask_cors import CORS

# Create a minimal Flask app to test the model routes
app = Flask(__name__)
CORS(app)

# Register model routes
from server.api.model_routes import model_bp
app.register_blueprint(model_bp)

def test_model_routes():
    """Test that model routes are properly registered"""
    with app.test_client() as client:
        print("Testing /api/models endpoint...")
        
        # Test GET /api/models
        response = client.get('/api/models')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_json()}")
        
        if response.status_code == 200:
            print("✅ Model API is working correctly!")
            return True
        else:
            print("❌ Model API returned an error")
            return False

if __name__ == "__main__":
    test_model_routes()
