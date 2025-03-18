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
from werkzeug.utils import secure_filename
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



@main.route("/help-center")
def helpCenter():
    return render_template("help_center.html", now=g.now)


@main.route("/contact-organizer", methods=["GET", "POST"])
@login_required
def contactOrganizer():
    if request.method == "POST":
        try:
            email = request.form.get("email")
            message = request.form.get("message")

            if not email or not message:
                flash("Please fill in all fields.", "error")
                return redirect(url_for("main.contactOrganizer"))

            # Here, you can implement sending an email or storing messages in the database
            # Example: Send an email (requires an email-sending function)
            # send_email(to=email, subject="Message from Attendee", body=message)

            flash("Your message has been sent successfully!", "success")
            return redirect(url_for("main.contactOrganizer"))

        except Exception as e:
            current_app.logger.error(f"Error sending message: {str(e)}")
            flash("An error occurred while sending your message. Please try again.", "error")
            return redirect(url_for("main.contactOrganizer"))

    return render_template("contact_organizer.html", now=g.now)


@main.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    return render_template("profile.html", now=g.now)

@main.route("/update-profile", methods=["POST"])
@login_required
def updateProfile():
    try:
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        profile_picture = request.files.get("profile_picture")

        if not first_name or not last_name:
            flash("First name and last name are required.", "error")
            return redirect(url_for("main.profile"))

        current_user.first_name = first_name
        current_user.last_name = last_name

        # Save profile picture if uploaded
        if profile_picture:
            filename = secure_filename(profile_picture.filename)
            profile_path = os.path.join("static/uploads/profiles", filename)
            profile_picture.save(profile_path)
            current_user.profile_picture = f"/static/uploads/profiles/{filename}"

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("main.profile"))

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("main.profile"))


@main.route("/contact")
@login_required
def contact():
    return render_template("contact.html", now=g.now)

@main.route("/update-screen-width", methods=["POST"])
def update_screen_width():
    if request.is_json:
        width = request.json.get("width")
        if width:
            session["screen_width"] = width
            return jsonify({"success": True})

        return jsonify({"success": False}), 400

