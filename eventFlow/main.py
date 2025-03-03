from flask import Blueprint, render_template, g, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import or_
from .models import Event, EventImage, db, TicketType, User
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
                    # Use the datetime object directly from the form
                    event_date = form.date.data
                    print(f"Event date: {event_date}")

                    # Create new event
                    new_event = Event(
                        title=form.title.data,
                        date=event_date,  # Use the datetime object directly
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
                                description=ticket_data.get('description', '')
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
    # Get pagination and search parameters
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of items per page
    query = request.args.get('query', '').strip()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()
    
    # Build the base query
    events_query = Event.query
    
    # Apply filters
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
    
    # Only show future events
    events_query = events_query.filter(Event.date >= datetime.now(timezone.utc))
    
    # Order by date
    events_query = events_query.order_by(Event.date.asc())
    
    # Paginate results
    try:
        events = events_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        if not events.items and page > 1:
            # If no items found and we're not on first page, redirect to page 1
            return redirect(url_for('main.findEvent', page=1, query=query, category=category, location=location))
            
    except Exception as e:
        print(f"Pagination error: {str(e)}")
        events = events_query.paginate(page=1, per_page=per_page, error_out=False)

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
    # Use join to load the user relationship
    event = Event.query.join(User).filter(Event.id == event_id).first_or_404()
    
    # Convert event date to timezone-aware if it isn't already
    if event.date.tzinfo is None:
        event.date = event.date.replace(tzinfo=timezone.utc)
    
    return render_template('event.html', event=event, now=g.now)

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', now=g.now)

@main.route('/my-events')
@login_required
def myEvents():
    page = request.args.get('page', 1, type=int)
    
    # Make sure we're using timezone-aware datetime for comparison
    current_time = datetime.now(timezone.utc)
    
    events = Event.query.filter_by(user_id=current_user.id)\
        .order_by(Event.date.desc())\
        .paginate(page=page, per_page=9, error_out=False)
        
    # Convert event dates to timezone-aware
    for event in events.items:
        if event.date.tzinfo is None:
            event.date = event.date.replace(tzinfo=timezone.utc)
    
    return render_template('my_events.html', events=events, now=current_time)

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html', now=g.now)

@main.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def editEvent(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if user owns the event
    if event.user_id != current_user.id:
        flash('You do not have permission to edit this event.', 'error')
        return redirect(url_for('main.myEvents'))
    
    form = EventForm()
    
    if request.method == 'GET':
        # Pre-populate form with existing event data
        form.title.data = event.title
        form.date.data = event.date
        form.location.data = event.location
        form.description.data = event.description
        form.category.data = event.category
        form.event_type.data = 'paid' if event.is_paid_event else 'free'
        form.currency.data = event.currency if event.is_paid_event else None
    
    if form.validate_on_submit():
        try:
            # Update basic event details
            event.title = form.title.data
            event.date = form.date.data
            event.location = form.location.data
            event.description = form.description.data
            event.category = form.category.data
            event.is_paid_event = (form.event_type.data == 'paid')
            event.currency = form.currency.data if form.event_type.data == 'paid' else None
            
            # Handle image updates only if new images are uploaded
            files = request.files.getlist('images')
            if any(f.filename for f in files):
                # Delete old images
                for image in event.images:
                    db.session.delete(image)
                event.images = []
                
                # Add new images
                for file in files:
                    if file and file.filename:
                        try:
                            image_data = file.read()
                            image_type = imghdr.what(None, image_data)
                            if image_type in ['jpeg', 'png']:
                                event_image = EventImage(
                                    image_data=image_data,
                                    image_mime_type=f'image/{image_type}'
                                )
                                event.images.append(event_image)
                            else:
                                flash(f'Invalid image format for {file.filename}. Only JPEG and PNG are supported.', 'error')
                        except Exception as e:
                            flash(f'Error processing image {file.filename}', 'error')
                            print(f"Image processing error: {str(e)}")
            
            # Handle ticket types for paid events
            if form.event_type.data == 'paid':
                # Delete old ticket types
                for ticket in event.ticket_types:
                    db.session.delete(ticket)
                event.ticket_types = []
                
                # Add new ticket types from form data
                for i in range(100):  # Reasonable limit for ticket types
                    prefix = f'ticket_types-{i}-'
                    ticket_type = request.form.get(f'{prefix}ticket_type')
                    if not ticket_type:
                        break
                    
                    try:
                        quantity = int(request.form.get(f'{prefix}quantity', 0))
                        price = float(request.form.get(f'{prefix}price', 0))
                        
                        if quantity < 1:
                            flash(f'Quantity must be at least 1 for ticket type {ticket_type}', 'error')
                            continue
                            
                        if price < 0:
                            flash(f'Price cannot be negative for ticket type {ticket_type}', 'error')
                            continue
                        
                        ticket = TicketType(
                            ticket_type=ticket_type,
                            custom_type=request.form.get(f'{prefix}custom_type'),
                            quantity=quantity,
                            price=price,
                            description=request.form.get(f'{prefix}description', '')
                        )
                        event.ticket_types.append(ticket)
                    except ValueError as e:
                        flash(f'Invalid number format for ticket type {ticket_type}', 'error')
                        continue
            
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('main.event', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating event. Please try again.', 'error')
            print(f"Error: {str(e)}")
            
    return render_template('edit_event.html', form=form, event=event)

@main.route('/event/<int:event_id>/delete', methods=['DELETE'])
@login_required
def deleteEvent(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
        
    try:
        # Delete associated images first
        for image in event.images:
            db.session.delete(image)
            
        # Delete associated tickets
        for ticket in event.ticket_types:
            db.session.delete(ticket)
            
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete event'
        }), 500

@main.route('/image/<int:image_id>')
def get_image(image_id):
    # Get the image from database
    image = EventImage.query.get_or_404(image_id)
    
    # Create response with image data and correct mime type
    response = make_response(image.image_data)
    response.headers.set('Content-Type', image.image_mime_type)
    
    # Set cache control headers
    response.headers.set(
        'Cache-Control', 
        'public, max-age=31536000'  # Cache for 1 year
    )
    
    return response

 