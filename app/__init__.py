from flask import Flask
from flask_cors import CORS
from app.routes import api_bp

def create_app():
    """
    Cria e configura a aplicação Flask
    
    Returns:
        Flask: Aplicação Flask configurada
    """
    app = Flask(__name__)
    CORS(app)
    
    # Registra o blueprint de API
    app.register_blueprint(api_bp)
    
    return app 