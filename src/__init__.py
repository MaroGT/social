from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import os
import stripe
from dotenv import load_dotenv
from flask_mail import Mail
from flask_migrate import Migrate







# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()  # Correct initialization
mail = Mail()



def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.from_object('config.Config')



    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app) #configure mail

    
    
    

    # Configure Login Manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from .views import main_bp
    from .auth import auth
    from .admin import admin
    from .user import user
    from .market import market

    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(main_bp)
    app.register_blueprint(user)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(market, url_prefix='/market')  # Add the url_prefix to ensure the routes are scoped


    return app

# User loader function
from .models import User  # Import User model here after defining the app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
