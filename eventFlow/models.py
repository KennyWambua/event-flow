from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from datetime import datetime, timezone
import random
import string

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    @staticmethod
    def generate_username(first_name, last_name):
        # Combine first and last name, convert to lowercase and remove spaces
        base_username = f"{first_name}{last_name}".lower().replace(' ', '')
        
        # Try the base username first
        if not User.query.filter_by(username=base_username).first():
            return base_username
            
        # If base username exists, add random numbers until we find a unique one
        while True:
            random_number = ''.join(random.choices(string.digits, k=4))
            username = f"{base_username}{random_number}"
            if not User.query.filter_by(username=username).first():
                return username

    def __repr__(self):
        return f"User('{self.first_name}', '{self.last_name}', '{self.email}')"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)