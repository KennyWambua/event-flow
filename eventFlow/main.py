from flask import (
    Blueprint,
    render_template,
    g,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    make_response,
    session,
    current_app,
    abort,
)

from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import or_
from .models import Event, EventImage, db, TicketType, User, EventRegistration, Order, UserRole
from .forms import EventForm, TicketTypeForm
import imghdr
import requests
import traceback
from flask_wtf.csrf import generate_csrf
from werkzeug.datastructures import ImmutableMultiDict
from .auth import role_required

main = Blueprint("main", __name__)


@main.before_request
def before_request():
    g.now = datetime.now(timezone.utc)


@main.route("/")
def home():
    # Get 4 random upcoming events
    featured_events = (
        Event.query.filter(Event.date >= datetime.now(timezone.utc))
        .order_by(db.func.random())
        .limit(3)
        .all()
    )

    # Get some statistics for the hero section
    upcoming_events = Event.query.filter(
        Event.date >= datetime.now(timezone.utc)
    ).count()

    return render_template(
        "home.html",
        featured_events=featured_events,
        now=g.now,
        stats={"upcoming_events": upcoming_events},
    )


def get_events_per_page():
    screen_width = session.get("screen_width", 1280)
    if screen_width <= 480:
        return 4
    elif screen_width <= 768:
        return 6
    else:
        return 12


@main.route("/event/create", methods=["GET", "POST"])
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
                        is_paid_event=(form.event_type.data == "paid"),
                        currency=(
                            form.currency.data
                            if form.event_type.data == "paid"
                            else None
                        ),
                    )

                    # Process images
                    files = request.files.getlist("images")
                    for file in files:
                        if file and file.filename:
                            try:
                                image_data = file.read()
                                image_type = imghdr.what(None, image_data)

                                if image_type not in ["jpeg", "png"]:
                                    return make_response(
                                        jsonify(
                                            {
                                                "success": False,
                                                "message": f"Invalid image format: {file.filename}",
                                            }
                                        ),
                                        400,
                                    )

                                event_image = EventImage(
                                    image_data=image_data,
                                    image_mime_type=f"image/{image_type}",
                                )
                                new_event.images.append(event_image)
                                print(f"Added image: {file.filename}")

                            except Exception as e:
                                print(f"Error processing image: {str(e)}")
                                traceback.print_exc()
                                db.session.rollback()
                                return make_response(
                                    jsonify(
                                        {
                                            "success": False,
                                            "message": f"Error processing image: {str(e)}",
                                        }
                                    ),
                                    400,
                                )

                    # Process ticket types for paid events
                    if form.event_type.data == "paid":
                        print("Processing ticket types")
                        for ticket_data in form.ticket_types_data:
                            ticket = TicketType(
                                ticket_type=ticket_data["ticket_type"],
                                custom_type=ticket_data.get("custom_type"),
                                quantity=int(ticket_data["quantity"]),
                                price=float(ticket_data["price"]),
                                description=ticket_data.get("description", ""),
                            )
                            new_event.ticket_types.append(ticket)
                            print(f"Added ticket type: {ticket_data['ticket_type']}")

                    db.session.add(new_event)
                    db.session.commit()
                    print("Event created successfully")

                    return make_response(
                        jsonify(
                            {
                                "success": True,
                                "redirect": url_for(
                                    "main.event", event_id=new_event.id
                                ),
                            }
                        ),
                        200,
                    )

                except Exception as e:
                    db.session.rollback()
                    print(f"Error saving event: {str(e)}")
                    traceback.print_exc()
                    return make_response(
                        jsonify(
                            {
                                "success": False,
                                "message": f"Error saving event: {str(e)}",
                            }
                        ),
                        500,
                    )
            else:
                print("Form validation failed:", form.errors)
                return make_response(
                    jsonify(
                        {
                            "success": False,
                            "message": "Form validation failed",
                            "errors": form.errors,
                        }
                    ),
                    400,
                )

        except Exception as e:
            print(f"Error processing request: {str(e)}")
            traceback.print_exc()
            return make_response(
                jsonify(
                    {"success": False, "message": f"Error processing request: {str(e)}"}
                ),
                500,
            )

    return render_template("create_event.html", form=form, now=g.now)


@main.route("/event/find")
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
                    "main.findEvent",
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


@main.route("/event/<int:event_id>")
def event(event_id):

    event = Event.query.join(User).filter(Event.id == event_id).first_or_404()

    if event.date.tzinfo is None:
        event.date = event.date.replace(tzinfo=timezone.utc)

    return render_template("event.html", event=event, now=g.now)


@main.route("/event/<int:event_id>/edit", methods=["GET", "POST"])
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
            event.is_paid_event = form.event_type.data == "paid"
            event.currency = (
                form.currency.data if form.event_type.data == "paid" else None
            )

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
                current_image_count = len(event.images) - len(
                    [id for id in removed_images if id]
                )
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

            # Update ticket types if it's a paid event
            if form.event_type.data == "paid":
                # Clear existing ticket types
                for ticket in event.ticket_types:
                    db.session.delete(ticket)
                event.ticket_types = []

                # Add new ticket types
                for i in range(100):  # Reasonable limit
                    prefix = f"ticket_types-{i}-"
                    ticket_type = request.form.get(f"{prefix}ticket_type")
                    if not ticket_type:
                        break

                    quantity = int(request.form.get(f"{prefix}quantity", 0))
                    price = float(request.form.get(f"{prefix}price", 0))
                    description = request.form.get(f"{prefix}description", "")

                    ticket = TicketType(
                        ticket_type=ticket_type,
                        quantity=quantity,
                        price=price,
                        description=description,
                    )
                    event.ticket_types.append(ticket)

            db.session.commit()
            return jsonify(
                {"success": True, "redirect": url_for("main.event", event_id=event.id)}
            )

        except Exception as e:
            db.session.rollback()
            print(f"Error updating event: {str(e)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Error updating event. Please try again.",
                    }
                ),
                500,
            )

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

@main.route("/event/<int:event_id>/delete", methods=["DELETE"])
@login_required
def deleteEvent(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        # Delete associated images first
        for image in event.images:
            db.session.delete(image)

        # Delete associated tickets
        for ticket in event.ticket_types:
            db.session.delete(ticket)

        db.session.delete(event)
        db.session.commit()

        return jsonify({"success": True, "message": "Event deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event: {str(e)}")
        return jsonify({"success": False, "error": "Failed to delete event"}), 500


@main.route("/help-center")
def helpCenter():
    return render_template("help_center.html", now=g.now)


@main.route("/find-tickets")
@login_required
def findMyTickets():
    return render_template("find_tickets.html", now=g.now)


@main.route("/contact-organizer")
def contactOrganizer():
    return render_template("contact_organizer.html", now=g.now)


@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html", now=g.now)

@main.route("/contact")
@login_required
def contact():
    return render_template("contact.html", now=g.now)

@main.route("/my-events")
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


@main.route("/settings")
@login_required
def settings():
    return render_template("settings.html", now=g.now)


@main.route("/image/<int:image_id>")
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


@main.route("/update-screen-width", methods=["POST"])
def update_screen_width():
    if request.is_json:
        width = request.json.get("width")
        if width:
            session["screen_width"] = width
            return jsonify({"success": True})

        return jsonify({"success": False}), 400


@main.route('/register-free-event', methods=['POST'])
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
        
        db.session.add(registration)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'redirect': url_for('main.myTickets')
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in free event registration: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration'
        }), 500

@main.route('/my-tickets')
@login_required
def myTickets():
    # Get both paid orders and free registrations
    current_time = datetime.now(timezone.utc)
    
    # Get free event registrations with timezone-aware dates
    free_registrations = (
        EventRegistration.query
        .join(Event)
        .filter(EventRegistration.user_id == current_user.id)
        .order_by(Event.date.desc())
        .all()
    )
    
    # Get paid event orders
    paid_orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    
    # Ensure all event dates are timezone-aware
    for registration in free_registrations:
        if registration.event.date.tzinfo is None:
            registration.event.date = registration.event.date.replace(tzinfo=timezone.utc)
    
    for order in paid_orders:
        if order.event.date.tzinfo is None:
            order.event.date = order.event.date.replace(tzinfo=timezone.utc)
    
    return render_template(
        'my_tickets.html',
        free_registrations=free_registrations,
        paid_orders=paid_orders,
        now=current_time
    )

@main.route('/cancel-registration/<int:registration_id>', methods=['POST'])
@login_required
def cancel_registration(registration_id):
    try:
        # Get the registration
        registration = EventRegistration.query.get_or_404(registration_id)
        
        # Check if the registration belongs to the current user
        if registration.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized to cancel this registration'
            }), 403

        # Get current time in UTC
        current_time = datetime.now(timezone.utc)
        
        # Make event date timezone aware if it isn't
        event_date = registration.event.date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)

        # Check if the event hasn't started yet
        if event_date <= current_time:
            return jsonify({
                'success': False,
                'message': 'Cannot cancel registration for past events'
            }), 400

        # Delete the registration
        db.session.delete(registration)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registration cancelled successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cancellation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while cancelling the registration'
        }), 500

@main.route('/create-order', methods=['POST'])
@login_required
def create_order():
    try:
        data = request.get_json()
        event_id = data.get('eventId')
        tickets = data.get('tickets')

        if not event_id or not tickets:
            return jsonify({'error': 'Invalid request data'}), 400

        event = Event.query.get_or_404(event_id)
        
        # Validate ticket availability
        for ticket_id, ticket_data in tickets.items():
            ticket_type = TicketType.query.get(ticket_id)
            if not ticket_type:
                return jsonify({'error': f'Invalid ticket type: {ticket_id}'}), 400
            
            if ticket_type.quantity < ticket_data['quantity']:
                return jsonify({
                    'error': f'Not enough tickets available for {ticket_data["name"]}'
                }), 400

        # Calculate total amount
        total_amount = sum(
            ticket_data['subtotal'] 
            for ticket_data in tickets.values()
        )

        # Create order with initial payment status
        order = Order(
            user_id=current_user.id,
            event_id=event_id,
            total_amount=total_amount,
            payment_status='pending',
            ticket_details=tickets
        )

        db.session.add(order)
        db.session.commit()

        # Generate payment URL with the order ID
        payment_url = url_for('main.process_payment', order_id=order.id, _external=True)
        
        return jsonify({
            'success': True,
            'redirect_url': payment_url,
            'order_id': order.id
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating order: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your order'}), 500

@main.route('/process-payment/<int:order_id>')
@login_required
def process_payment(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Verify order belongs to current user
    if order.user_id != current_user.id:
        abort(403)
    
    try:
        # Here you would integrate with your payment provider
        # For now, we'll create a simple payment page
        return render_template(
            'payment.html',
            order=order,
            event=order.event,
            tickets=order.ticket_details
        )
    except Exception as e:
        current_app.logger.error(f"Error processing payment: {str(e)}")
        return render_template('error.html', message="Error processing payment")
