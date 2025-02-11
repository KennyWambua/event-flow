from flask import Blueprint, render_template
from flask_login import login_required

main = Blueprint('main', __name__)

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
    return render_template('home.html', featured_events=featured_events)

@main.route('/find-event')
def findEvent():
    return render_template('find_event.html')

@main.route('/create-event')
@login_required
def createEvent():
    return render_template('create_event.html')

@main.route('/help-center')
def helpCenter():
    return render_template('help_center.html')

@main.route('/find-tickets')
def findMyTickets():
    return render_template('find_tickets.html')

@main.route('/contact-organizer')
def contactOrganizer():
    return render_template('contact_organizer.html')

@main.route('/event/<int:event_id>')
def event(event_id):
    return render_template('event.html', event_id=event_id)

 