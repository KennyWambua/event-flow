from flask import (
    Blueprint,
    render_template,
    g,
    request,
    redirect,
    url_for,
    jsonify,
    make_response,
    session,
    current_app,
    abort,
)

from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import or_
from .models import Event, EventImage, db, User, EventRegistration, UserRole, TicketType
from .forms import EventForm
import imghdr
from .auth import role_required

events = Blueprint("events", __name__)

@events.before_request
def before_request():
    g.now = datetime.now(timezone.utc)
    
def get_events_per_page():
    screen_width = session.get("screen_width", 1280)
    if screen_width <= 480:
        return 4
    elif screen_width <= 768:
        return 6
    else:
        return 12
      
@events.route("/event/create", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ORGANIZER)
def createEvent():
    form = EventForm()

    if request.method == "POST":
        print("Processing POST request")
        print("Form data:", request.form)
        print("Files:", request.files)

        try:
            if form.validate():
                # Create new event
                new_event = Event(
                    title=form.title.data,
                    date=form.date.data,
                    location=form.location.data,
                    description=form.description.data,
                    category=form.category.data,
                    user_id=current_user.id,
                    free_ticket_quantity=form.free_ticket_quantity.data if form.event_type.data == "free" else None,
                    is_paid_event=(form.event_type.data == "paid"),
                    currency=(form.currency.data if form.event_type.data == "paid" else None),
                )

                # Add ticket types if it's a paid event
                if form.event_type.data == "paid":
                    # Get ticket types data from form
                    i = 0
                    while True:
                        prefix = f"ticket_types-{i}-"
                        ticket_type = request.form.get(f"{prefix}ticket_type")
                        if not ticket_type:
                            break

                        # Create ticket type
                        ticket = TicketType(
                            ticket_type=ticket_type,
                            custom_type=request.form.get(f"{prefix}custom_type"),
                            quantity=int(request.form.get(f"{prefix}quantity", 0)),
                            price=float(request.form.get(f"{prefix}price", 0)),
                            description=request.form.get(f"{prefix}description", "")
                        )
                        new_event.ticket_types.append(ticket)
                        i += 1

                # Process images
                files = request.files.getlist("images")
                for file in files:
                    if file and file.filename:
                        try:
                            image_data = file.read()
                            image_type = imghdr.what(None, image_data)

                            if image_type not in ["jpeg", "png"]:
                                return make_response(
                                    jsonify({"success": False, "message": f"Invalid image format: {file.filename}"}), 400
                                )

                            event_image = EventImage(
                                image_data=image_data,
                                image_mime_type=f"image/{image_type}",
                            )
                            new_event.images.append(event_image)

                        except Exception as e:
                            db.session.rollback()
                            return make_response(
                                jsonify({"success": False, "message": f"Error processing image: {str(e)}"}), 400
                            )

                db.session.add(new_event)
                db.session.commit()

                return make_response(
                    jsonify({"success": True, "redirect": url_for("events.event", event_id=new_event.id)}), 200
                )

        except Exception as e:
            db.session.rollback()
            return make_response(
                jsonify({"success": False, "message": f"Error processing request: {str(e)}"}), 500
            )

    return render_template("create_event.html", form=form, now=g.now)

@events.route("/event/find")
def findEvent():
    # Get pagination and search parameters
    page = request.args.get("page", 1, type=int)
    events_per_page = get_events_per_page()
    query = request.args.get("query", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()

    # Build the base query
    events_query = Event.query

    # Apply filters
    if query:
        search_terms = [term.strip() for term in query.split()]
        search_filters = []
        for term in search_terms:
            search_filters.append(
                or_(
                    Event.title.ilike(f"%{term}%"), Event.description.ilike(f"%{term}%")
                )
            )
        events_query = events_query.filter(or_(*search_filters))

    if category:
        events_query = events_query.filter(Event.category == category)

    if location:
        location_terms = [term.strip() for term in location.split()]
        location_filters = []
        for term in location_terms:
            location_filters.append(Event.location.ilike(f"%{term}%"))
        events_query = events_query.filter(or_(*location_filters))

    # Only show future events
    events_query = events_query.filter(Event.date >= datetime.now(timezone.utc))

    # Order by date
    events_query = events_query.order_by(Event.date.asc())

    # Paginate results
    try:
        events = events_query.paginate(
            page=page, per_page=events_per_page, error_out=False
        )

        if not events.items and page > 1:
            # If no items found and we're not on first page, redirect to page 1
            return redirect(
                url_for(
                    "events.findEvent",
                    page=1,
                    query=query,
                    category=category,
                    location=location,
                )
            )

    except Exception as e:
        print(f"Pagination error: {str(e)}")
        events = events_query.paginate(
            page=1, per_page=events_per_page, error_out=False
        )

    return render_template("find_event.html", events=events, now=g.now)


@events.route("/event/<int:event_id>")
def event(event_id):
    event = Event.query.join(User).filter(Event.id == event_id).first_or_404()

    if event.date.tzinfo is None:
        event.date = event.date.replace(tzinfo=timezone.utc)

    # Get the minimum ticket price if it's a paid event with ticket types
    min_ticket_price = None
    if event.is_paid_event and event.ticket_types:
        try:
            # Filter out any ticket types with None price and get the minimum
            valid_tickets = [t for t in event.ticket_types if t.price is not None]
            if valid_tickets:
                min_ticket_price = min(t.price for t in valid_tickets)
        except (ValueError, TypeError) as e:
            print(f"Error calculating min ticket price: {str(e)}")
            min_ticket_price = None

    return render_template("event.html", event=event, now=g.now, min_ticket_price=min_ticket_price)

@events.route("/image/<int:image_id>")
def get_image(image_id):
    # Get the image from database
    image = EventImage.query.get_or_404(image_id)

    # Create response with image data and correct mime type
    response = make_response(image.image_data)
    response.headers.set("Content-Type", image.image_mime_type)

    # Set cache control headers
    response.headers.set(
        "Cache-Control", "public, max-age=31536000"  # Cache for 1 year
    )

    return response

@events.route("/event/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ORGANIZER)
def editEvent(event_id):
    event = Event.query.get_or_404(event_id)

    # Check if user owns the event
    if event.user_id != current_user.id:
        abort(403)

    form = EventForm()

    if request.method == "POST":
        try:
            # Update basic event details
            event.title = form.title.data
            event.date = form.date.data
            event.location = form.location.data
            event.description = form.description.data
            event.category = form.category.data
            event.free_ticket_quantity = form.free_ticket_quantity.data if form.event_type.data == "free" else None
            event.is_paid_event = form.event_type.data == "paid"
            event.currency = form.currency.data if form.event_type.data == "paid" else None
            
            if form.event_type.data == "paid":
                    # Get ticket types data from form
                    i = 0
                    while True:
                        prefix = f"ticket_types-{i}-"
                        ticket_type = request.form.get(f"{prefix}ticket_type")
                        if not ticket_type:
                            break

                        # Create ticket type
                        ticket = TicketType(
                            ticket_type=ticket_type,
                            custom_type=request.form.get(f"{prefix}custom_type"),
                            quantity=int(request.form.get(f"{prefix}quantity", 0)),
                            price=float(request.form.get(f"{prefix}price", 0)),
                            description=request.form.get(f"{prefix}description", "")
                        )
                        event.ticket_types.append(ticket)
                        i += 1

            # Handle image deletions if any
            removed_images = request.form.get("removed_images", "").split(",")
            if removed_images[0]:  # Check if there are actually IDs to delete
                for image_id in removed_images:
                    image = EventImage.query.get(int(image_id))
                    if image and image.event_id == event.id:
                        db.session.delete(image)

            # Handle new image uploads if any
            files = request.files.getlist("images")
            if any(f.filename for f in files):
                current_image_count = len(event.images) - len([id for id in removed_images if id])
                allowed_new_images = 5 - current_image_count

                for file in files[:allowed_new_images]:
                    if file and file.filename:
                        try:
                            image_data = file.read()
                            image_type = imghdr.what(None, image_data)
                            if image_type in ["jpeg", "png"]:
                                event_image = EventImage(
                                    image_data=image_data,
                                    image_mime_type=f"image/{image_type}",
                                )
                                event.images.append(event_image)
                        except Exception as e:
                            print(f"Error processing image: {str(e)}")

            db.session.commit()
            return jsonify({"success": True, "redirect": url_for("events.event", event_id=event.id)})

        except Exception as e:
            print(f"Error updating event: {str(e)}")
            db.session.rollback()
            return jsonify({"success": False, "message": "Error updating event. Please try again." }), 500

    # Pre-populate form for GET request
    if request.method == "GET":
        form.title.data = event.title
        form.date.data = event.date
        form.location.data = event.location
        form.description.data = event.description
        form.category.data = event.category
        form.event_type.data = "paid" if event.is_paid_event else "free"
        form.currency.data = event.currency if event.is_paid_event else None

    return render_template("edit_event.html", form=form, event=event)

@events.route("/event/<int:event_id>/delete", methods=["DELETE"])
@login_required
def deleteEvent(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        db.session.delete(event)
        db.session.commit()

        return jsonify({"success": True, "message": "Event deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event: {str(e)}")
        return jsonify({"success": False, "error": "Failed to delete event"}), 500

@events.route("/my-events")
@login_required
@role_required(UserRole.ORGANIZER)
def myEvents():
    page = request.args.get("page", 1, type=int)
    events_per_page = get_events_per_page()

    # Make sure we're using timezone-aware datetime for comparison
    current_time = datetime.now(timezone.utc)

    events = (
        Event.query.filter_by(user_id=current_user.id)
        .order_by(Event.date.desc())
        .paginate(page=page, per_page=events_per_page, error_out=False)
    )

    # Convert event dates to timezone-aware
    for event in events.items:
        if event.date.tzinfo is None:
            event.date = event.date.replace(tzinfo=timezone.utc)

    return render_template("my_events.html", events=events, now=current_time)

@events.route('/register-free-event', methods=['POST'])
@login_required
def register_free_event():
    try:
        data = request.get_json()
        event_id = data.get('eventId')
        
        if not event_id:
            return jsonify({
                'success': False,
                'message': 'Event ID is required'
            }), 400

        event = Event.query.get_or_404(event_id)

        # Check if event is actually free
        if event.is_paid_event:
            return jsonify({
                'success': False,
                'message': 'This is not a free event'
            }), 400

        # Check if there are tickets available
        if not event.free_ticket_quantity or event.free_ticket_quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'No tickets available for this event'
            }), 400

        # Check if user is already registered
        existing_registration = EventRegistration.query.filter_by(
            user_id=current_user.id,
            event_id=event_id
        ).first()

        if existing_registration:
            return jsonify({
                'success': False,
                'message': 'You are already registered for this event'
            }), 400

        # Create new registration
        registration = EventRegistration(
            user_id=current_user.id,
            event_id=event_id
        )
        
        # Update the free ticket quantity
        event.free_ticket_quantity -= 1
        
        db.session.add(registration)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'redirect': url_for('tickets.myTickets')
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in free event registration: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration'
        }), 500
