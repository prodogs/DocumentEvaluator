from flask import Blueprint, jsonify

document_routes = Blueprint('document_routes', __name__)

# Store background tasks with their status
background_tasks = {}

@document_routes.route('/analyze_document_with_llm', methods=['POST'])
def analyze_document_with_llm():
    """DEPRECATED: Document analysis service moved to KnowledgeDocuments database"""
    return jsonify({
        'message': 'Document analysis service has been moved to KnowledgeDocuments database',
        'success': False,
        'deprecated': True,
        'reason': 'docs and llm_responses tables moved to separate database',
        'status': 'SERVICE_MOVED'
    }), 410  # 410 Gone - resource no longer available

@document_routes.route('/analyze_status/<task_id>', methods=['GET'])
def analyze_status(task_id):
    """DEPRECATED: Document analysis status service moved to KnowledgeDocuments database"""
    return jsonify({
        'status': 'SERVICE_MOVED',
        'totalDocuments': 0,
        'processedDocuments': 0,
        'outstandingDocuments': 0,
        'error_message': 'Document analysis service moved to KnowledgeDocuments database',
        'deprecated': True
    }), 410  # 410 Gone - resource no longer available

def register_document_routes(app):
    """Register document routes with the Flask app"""
    app.register_blueprint(document_routes)

    # Make background_tasks available globally
    app.config['BACKGROUND_TASKS'] = background_tasks

    return app