from flask import url_for
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
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    role = db.Column(db.String(20), nullable=False, default='attendee')
    # Add relationship to events
    events = db.relationship('Event', backref='user', lazy=True)
    registered_events = db.relationship('Event', 
                                      secondary='event_registration',
                                      backref=db.backref('registered_users', lazy=True))
    # Add orders relationship
    orders = db.relationship('Order', backref='purchaser', lazy=True)

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

    def get_upcoming_tickets(self):
        """Returns all upcoming tickets (both free and paid)"""
        current_time = datetime.now(timezone.utc)
        
        # Get free registrations
        free_tickets = EventRegistration.query.join(Event).filter(
            EventRegistration.user_id == self.id,
            Event.date > current_time
        ).all()
        
        # Get paid tickets
        paid_tickets = Order.query.join(Event).filter(
            Order.user_id == self.id,
            Order.payment_status == 'paid',
            Event.date > current_time
        ).all()
        
        return {'free': free_tickets, 'paid': paid_tickets}

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
    orders = db.relationship('Order', backref='ordered_event', lazy=True)

    def __repr__(self):
        return f"<Event('{self.title}', '{self.date}', '{self.location}'), '{self.description}', '{self.category}', '{self.images}')>"

    def get_primary_image_url(self):
        """Returns the URL for the primary (first) image of the event"""
        if self.images:
            return url_for('main.get_image', image_id=self.images[0].id)
        return url_for('static', filename='images/audience.jpg')

    def is_user_registered(self, user):
        return EventRegistration.query.filter_by(
            event_id=self.id,
            user_id=user.id
        ).first() is not None

    @property
    def date_utc(self):
        """Return timezone-aware date"""
        if self.date.tzinfo is None:
            return self.date.replace(tzinfo=timezone.utc)
        return self.date

    def get_sales_stats(self):
        total_sales = sum(order.total_amount for order in self.orders if order.is_paid)
        total_tickets_sold = sum(order.get_ticket_count() for order in self.orders if order.is_paid)
        free_registrations = len(self.registrations)
        
        return {
            'total_sales': total_sales,
            'total_tickets_sold': total_tickets_sold,
            'free_registrations': free_registrations
        }

class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('registrations', lazy=True))
    event = db.relationship('Event', backref=db.backref('registrations', lazy=True))

    def __repr__(self):
        return f'<EventRegistration {self.id}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_id = db.Column(db.String(255), nullable=False, unique=True)
    payment_status = db.Column(db.String(50), default='pending')
    ticket_details = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='user_orders')
    event = db.relationship('Event', backref='event_orders')

    def __repr__(self):
        return f'<Order {self.id} - {self.payment_status}>'

    @property
    def is_paid(self):
        return self.payment_status == 'paid'

    def get_ticket_count(self):
        """Returns total number of tickets in the order"""
        return sum(ticket['quantity'] for ticket in self.ticket_details)

    def get_formatted_amount(self):
        """Returns formatted amount with currency"""
        return f"{self.total_amount:.2f} {self.event.currency}"

    @staticmethod
    def create_from_checkout(user_id, event_id, total_amount, payment_id, ticket_details):
        """Helper method to create order from checkout data"""
        order = Order(
            user_id=user_id,
            event_id=event_id,
            total_amount=total_amount,
            payment_id=payment_id,
            ticket_details=ticket_details
        )
        db.session.add(order)
        db.session.commit()
        return order 