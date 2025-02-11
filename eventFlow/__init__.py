import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
  app = Flask(__name__)

  app.config.from_object(Config)
  app.config['SECRET_KEY'] = secrets.token_hex(16)
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
  app.config['SESSION_TYPE'] = 'filesystem'
  app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
  app.config['SESSION_PERMANENT'] = True 
  app.config['PERMANENT_SESSION_LIFETIME'] = 3600

  db.init_app(app)
  migrate.init_app(app, db)
  login_manager.login_view = 'auth.login'
  login_manager.login_message_category = 'info'
  login_manager.init_app(app)
  
  Session(app)
  
  from .models import User
  
  
  @login_manager.user_loader
  def load_user(id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(id))

  # blueprint for auth routes
  from .auth import auth as auth_blueprint
  app.register_blueprint(auth_blueprint, url_prefix='/auth')
  
  # blueprint for non-auth 
  from .main import main as main_blueprint
  app.register_blueprint(main_blueprint)

  return app