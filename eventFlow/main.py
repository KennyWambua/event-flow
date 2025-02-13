from flask import Blueprint, render_template, g, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import or_
from .models import Event, EventImage, db
from .forms import EventForm
import imghdr
import requests

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

@main.route('/event/create', methods=['GET', 'POST'])
@login_required
def createEvent():
    form = EventForm()
    
    if form.validate_on_submit():
        try:
            new_event = Event(
                title=form.title.data,
                date=form.date.data.replace(tzinfo=timezone.utc),
                location=form.location.data,
                description=form.description.data,
                category=form.category.data,
                user_id=current_user.id
            )
            
            if form.images.data and form.images.data[0]:
                # Handle uploaded images
                for i, image_file in enumerate(form.images.data):
                    try:
                        image_data = image_file.read()
                        if not image_data:
                            continue
                            
                        # Verify it's a valid image
                        image_type = imghdr.what(None, image_data)
                        if not image_type:
                            flash(f'File "{image_file.filename}" is not a valid image', 'error')
                            continue
                            
                        if image_type not in ['jpeg', 'jpg', 'png']:
                            flash(f'File "{image_file.filename}" must be JPEG or PNG', 'error')
                            continue
                            
                        # Normalize image type
                        if image_type == 'jpg':
                            image_type = 'jpeg'
                            
                        event_image = EventImage(
                            image_data=image_data,
                            image_mime_type=f'image/{image_type}',
                            is_primary=(i == 0)
                        )
                        new_event.images.append(event_image)
                        
                    except Exception as e:
                        print(f"Error processing image {image_file.filename}: {str(e)}")
                        flash(f'Error processing image "{image_file.filename}"', 'error')
                        
            elif form.image_url.data:
                try:
                    response = requests.get(
                        form.image_url.data,
                        timeout=5,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        flash('URL does not point to a valid image', 'error')
                        return render_template('create_event.html', form=form, now=g.now)
                        
                    image_type = content_type.split('/')[-1]
                    if image_type not in ['jpeg', 'jpg', 'png']:
                        flash('Image must be JPEG or PNG', 'error')
                        return render_template('create_event.html', form=form, now=g.now)
                        
                    event_image = EventImage(
                        image_data=response.content,
                        image_mime_type=content_type,
                        is_primary=True
                    )
                    new_event.images.append(event_image)
                    
                except requests.RequestException as e:
                    flash('Error fetching image from URL. Please check the URL or try uploading instead.', 'error')
                    return render_template('create_event.html', form=form, now=g.now)
            
            if not new_event.images:
                flash('Please provide at least one valid image', 'error')
                return render_template('create_event.html', form=form, now=g.now)
            
            db.session.add(new_event)
            db.session.commit()
            
            flash('Event created successfully!', 'success')
            return redirect(url_for('main.findEvent'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating event. Please try again.', 'error')
            print(f"Error: {str(e)}")
            
    return render_template('create_event.html', form=form, now=g.now)

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

 