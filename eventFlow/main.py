from flask import Blueprint, render_template, g, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import or_
from .models import Event, EventImage, db, TicketType
from .forms import EventForm, TicketTypeForm
import imghdr
import requests
import traceback
from flask_wtf.csrf import generate_csrf

main = Blueprint('main', __name__)

@main.before_request
def before_request():
    g.now = datetime.now(timezone.utc)

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
        }
    ]
    return render_template('home.html', featured_events=featured_events, now=g.now)

@main.route('/event/create', methods=['GET', 'POST'])
@login_required
def createEvent():
    form = EventForm()
    
    if request.method == 'POST':
        print("Processing POST request")
        print("Form data:", request.form)
        print("Files:", request.files)
        
        try:
            if form.validate():
                print("Form validated successfully")
                
                # Start database transaction
                db.session.begin_nested()
                
                try:
                    # Convert date string to datetime object
                    event_date = datetime.strptime(form.date.data, '%Y-%m-%dT%H:%M')
                    print(f"Parsed date: {event_date}")

                    # Create new event with converted date
                    new_event = Event(
                        title=form.title.data,
                        date=event_date,  # Use the converted datetime object
                        location=form.location.data,
                        description=form.description.data,
                        category=form.category.data,
                        user_id=current_user.id,
                        is_paid_event=(form.event_type.data == 'paid'),
                        currency=form.currency.data if form.event_type.data == 'paid' else None
                    )

                    # Process images
                    files = request.files.getlist('images')
                    for file in files:
                        if file and file.filename:
                            try:
                                image_data = file.read()
                                image_type = imghdr.what(None, image_data)
                                
                                if image_type not in ['jpeg', 'png']:
                                    return make_response(jsonify({
                                        'success': False,
                                        'message': f'Invalid image format: {file.filename}'
                                    }), 400)
                                
                                event_image = EventImage(
                                    image_data=image_data,
                                    image_mime_type=f'image/{image_type}'
                                )
                                new_event.images.append(event_image)
                                print(f"Added image: {file.filename}")
                                
                            except Exception as e:
                                print(f"Error processing image: {str(e)}")
                                traceback.print_exc()
                                db.session.rollback()
                                return make_response(jsonify({
                                    'success': False,
                                    'message': f'Error processing image: {str(e)}'
                                }), 400)

                    # Process ticket types for paid events
                    if form.event_type.data == 'paid':
                        print("Processing ticket types")
                        for ticket_data in form.ticket_types_data:
                            ticket = TicketType(
                                ticket_type=ticket_data['ticket_type'],
                                custom_type=ticket_data.get('custom_type'),
                                quantity=int(ticket_data['quantity']),
                                price=float(ticket_data['price']),
                                description=ticket_data.get('description')
                            )
                            new_event.ticket_types.append(ticket)
                            print(f"Added ticket type: {ticket_data['ticket_type']}")

                    db.session.add(new_event)
                    db.session.commit()
                    print("Event created successfully")

                    return make_response(jsonify({
                        'success': True,
                        'redirect': url_for('main.event', event_id=new_event.id)
                    }), 200)

                except Exception as e:
                    db.session.rollback()
                    print(f"Error saving event: {str(e)}")
                    traceback.print_exc()
                    return make_response(jsonify({
                        'success': False,
                        'message': f'Error saving event: {str(e)}'
                    }), 500)
            else:
                print("Form validation failed:", form.errors)
                return make_response(jsonify({
                    'success': False,
                    'message': 'Form validation failed',
                    'errors': form.errors
                }), 400)

        except Exception as e:
            print(f"Error processing request: {str(e)}")
            traceback.print_exc()
            return make_response(jsonify({
                'success': False,
                'message': f'Error processing request: {str(e)}'
            }), 500)

    return render_template('create_event.html', form=form, now=g.now)
 
@main.route('/event/find')
def findEvent():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()
    
    events_query = Event.query
    
    if query:
        search_terms = [term.strip() for term in query.split()]
        search_filters = []
        for term in search_terms:
            search_filters.append(
                or_(
                    Event.title.ilike(f'%{term}%'),
                    Event.description.ilike(f'%{term}%')
                )
            )
        events_query = events_query.filter(or_(*search_filters))
    
    if category:
        events_query = events_query.filter(Event.category == category)
    
    if location:
        location_terms = [term.strip() for term in location.split()]
        location_filters = []
        for term in location_terms:
            location_filters.append(Event.location.ilike(f'%{term}%'))
        events_query = events_query.filter(or_(*location_filters))
    
    # Only show future events by default
    events_query = events_query.filter(Event.date >= datetime.now(timezone.utc))
    
    # Order by date
    events_query = events_query.order_by(Event.date.asc())
    
    # Paginate results
    events = events_query.paginate(
        page=page, 
        per_page=9, 
        error_out=False
    )
    
    return render_template('find_event.html', events=events, now=g.now)


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
    page = request.args.get('page', 1, type=int)
    events = Event.query.filter_by(user_id=current_user.id)\
        .order_by(Event.date.asc())\
        .paginate(page=page, per_page=9, error_out=False)
    return render_template('my_events.html', events=events, now=g.now)

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html', now=g.now)

@main.route('/event/<int:event_id>/delete', methods=['DELETE'])
@login_required
def deleteEvent(event_id):
    event = Event.query.get_or_404(event_id)
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        # Delete associated images first
        for image in event.images:
            db.session.delete(image)
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': 'Event deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Error deleting event'}), 500

 