from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from datetime import datetime, timezone
import random
import string
import base64

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

class EventImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    image_data = db.Column(db.LargeBinary)
    image_mime_type = db.Column(db.String(30))
    is_primary = db.Column(db.Boolean, default=False)

    def get_url(self):
        if self.image_data:
            return f"data:{self.image_mime_type};base64,{base64.b64encode(self.image_data).decode('utf-8')}"
        return None

class TicketType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    ticket_type = db.Column(db.String(50), nullable=False)
    custom_type = db.Column(db.String(50))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Event pricing and tickets
    is_paid_event = db.Column(db.Boolean, default=False)
    currency = db.Column(db.String(3), default='KES')
    
    # Relationships
    images = db.relationship('EventImage', backref='event', lazy=True, cascade='all, delete-orphan')
    ticket_types = db.relationship('TicketType', backref='event', lazy=True, cascade='all, delete-orphan')
    organizer = db.relationship('User', backref='events')

    def __repr__(self):
        return f"<Event('{self.title}', '{self.date}', '{self.location}'), '{self.description}', '{self.category}', '{self.images}')>"

    def get_primary_image_url(self):
        primary_image = next((img for img in self.images if img.is_primary), None)
        if primary_image:
            return primary_image.get_url()
        return self.images[0].get_url() if self.images else None