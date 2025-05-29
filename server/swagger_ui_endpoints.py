from flask import Blueprint, jsonify, request, send_from_directory

# Create a Blueprint for Swagger UI related endpoints
swagger_bp = Blueprint('swagger_ui', __name__)

@swagger_bp.route('/static/swagger.json')
def serve_swagger_spec():
    """Serve the Swagger/OpenAPI specification"""
    return send_from_directory('static', 'swagger.json')

@swagger_bp.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'swagger': 'available at /api/docs'
    })

@swagger_bp.route('/api/docs-config')
def swagger_config():
    """Return configuration for Swagger UI"""
    return jsonify({
        'title': 'Document Processor & Evaluator API',
        'version': '1.0.0',
        'apiPath': '/static/swagger.json'
    })

def register_swagger_endpoints(app):
    """Register all Swagger UI related endpoints with the Flask app"""
    app.register_blueprint(swagger_bp)
