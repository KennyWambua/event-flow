import secrets
from flask import Flask, request,  url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from config import Config
from flask_wtf.csrf import CSRFProtect
from .utils import init_app as init_utils


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
  app = Flask(__name__)

  app.config.from_object(Config)
  app.config['SECRET_KEY'] = secrets.token_hex(16)
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eventflow.db'
  app.config['SESSION_TYPE'] = 'filesystem'
  app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
  app.config['SESSION_PERMANENT'] = True 
  app.config['PERMANENT_SESSION_LIFETIME'] = 3600

  db.init_app(app)
  migrate.init_app(app, db)
  
  # Initialize Session before login manager
  Session(app)
  
  # Initialize CSRF protection
  csrf.init_app(app)
  
  # Initialize utility functions
  init_utils(app)
  
  login_manager.login_view = 'auth.login'
  login_manager.login_message = 'Please log in to access this page.'
  login_manager.login_message_category = 'info'

  @login_manager.unauthorized_handler
  def unauthorized():
    # Get the full current URL
    next_url = request.url
    # Remove the domain part if present
    if '//' in next_url:
        next_url = '/' + next_url.split('/', 3)[3]
    return redirect(url_for('auth.login', next=next_url))

  login_manager.init_app(app)
  
  from .models import User, UserRole
  
  
  @login_manager.user_loader
  def load_user(id):
    return User.query.get(int(id))

  # Make UserRole available to all templates
  @app.context_processor
  def inject_enums():
    return {
      'UserRole': UserRole
    }

  # blueprint for auth routes
  from .auth import auth as auth_blueprint
  app.register_blueprint(auth_blueprint, url_prefix='/auth')
  
  # blueprint for main routes 
  from .main import main as main_blueprint
  app.register_blueprint(main_blueprint)
  
  # blueprint for events routes 
  from .events import events as events_blueprint
  app.register_blueprint(events_blueprint)
  
  # blueprint for events routes 
  from .tickets import tickets as tickets_blueprint
  app.register_blueprint(tickets_blueprint)

  # blueprint for reports routes 
  from .reports import reports as reports_blueprint
  app.register_blueprint(reports_blueprint)
  
  # Create database tables within app context
  with app.app_context():
    db.create_all()

  return app