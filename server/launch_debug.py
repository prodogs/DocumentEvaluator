import os
from app import app

if __name__ == '__main__':
    # Set the FLASK_ENV environment variable to 'development' for debug mode
    os.environ['FLASK_ENV'] = 'development'
    # Run the Flask app with debugging enabled
    app.run(debug=True)