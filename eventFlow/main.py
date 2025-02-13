from flask import Blueprint, render_template, g
from flask_login import login_required
from datetime import datetime

main = Blueprint('main', __name__)

@main.before_request
def before_request():
    g.now = datetime.utcnow()

@main.route('/')
def home():
    featured_events = [
        {
            'id': 1,
            'title': 'Easter Music Festival',
            'date': 'April 15, 2025',
            'location': 'Uhuru Gardens, Nairobi',
            'image_url': '/static/images/audience.jpg'
        },
            {
            'id': 2,
            'title': 'Food & Wine Festival',
            'date': 'May 5, 2025',
            'location': 'Carnivore, Westlands',
            'image_url': '/static/images/glasses.jpg'
        },
        {
            'id': 3,
            'title': 'Tech Conference 2025',
            'date': 'July 20, 2025',
            'location': 'Convention Center, SF',
            'image_url': '/static/images/conference.jpg'
        },
    
    ]
    return render_template('home.html', featured_events=featured_events, now=g.now)

@main.route('/find-event')
def findEvent():
    return render_template('find_event.html', now=g.now)

@main.route('/create-event')
@login_required
def createEvent():
    return render_template('create_event.html', now=g.now)

@main.route('/help-center')
def helpCenter():
    return render_template('help_center.html', now=g.now)

@main.route('/find-tickets')
@login_required
def findMyTickets():
    return render_template('find_tickets.html', now=g.now)

@main.route('/contact-organizer')
def contactOrganizer():
    return render_template('contact_organizer.html', now=g.now)

@main.route('/event/<int:event_id>')
def event(event_id):
    return render_template('event.html', event_id=event_id, now=g.now)

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', now=g.now)

@main.route('/my-events')
@login_required
def myEvents():
    return render_template('my_events.html', now=g.now)

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html', now=g.now)

 