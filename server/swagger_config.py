from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint

def configure_swagger(app):
    """
    Configure Swagger UI for the Flask application

    Args:
        app: Flask application instance

    Returns:
        Configured Flask application with Swagger UI
    """
    # Define Swagger UI route
    SWAGGER_URL = '/api/docs'
    API_URL = '/static/swagger.json'

    # Create Swagger UI blueprint
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Document Evaluator API"
        }
    )

    # Register Swagger UI blueprint
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    return app
def configure_swagger(app):
    """Configure Swagger UI for the Flask application"""
    # Define Swagger UI blueprint
    SWAGGER_URL = '/api/docs'
    API_URL = '/static/swagger.json'

    # Create Swagger UI blueprint with a unique name
    swagger_ui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Document Evaluator API"
        },
        blueprint_name='swagger_ui_blueprint'
    )

    # Register blueprint with Flask app
    app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

    return app
