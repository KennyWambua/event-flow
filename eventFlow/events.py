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
    send_file,
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
import qrcode
from io import BytesIO
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader
# from reportlab.pdfinterp import PDFResourceManager
# from reportlab.pdfpage.pdfpage import PDFPage
# from reportlab.pdfdoc import PDFDocument
# from reportlab.pdfgen import PDFPageAggregator
# from reportlab.pdfbase.image import ImageReader
from reportlab.lib import colors
import os

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
                                    "events.event", event_id=new_event.id
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

    return render_template("event.html", event=event, now=g.now)

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
                {"success": True, "redirect": url_for("events.event", event_id=event.id)}
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

@events.route("/event/<int:event_id>/delete", methods=["DELETE"])
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
            'redirect': url_for('tickets.myTickets')
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in free event registration: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration'
        }), 500
