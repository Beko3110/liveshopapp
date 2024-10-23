import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy.orm import DeclarativeBase
from flask_session import Session

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # Basic config
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
    app.config["SESSION_TYPE"] = "filesystem"
    
    # Database config
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize extensions
    Session(app)
    db.init_app(app)
    socketio.init_app(app)
    
    with app.app_context():
        # Import models here to ensure they're registered with SQLAlchemy
        import models
        # Create all database tables
        db.create_all()
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.products import products_bp
    from routes.orders import orders_bp
    from routes.stream import stream_bp
    from routes.social import social_bp
    from routes.rewards import rewards_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(rewards_bp)
    
    return app
