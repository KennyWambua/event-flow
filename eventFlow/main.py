from flask import (
    Blueprint,
    render_template,
    g,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    current_app,
)

from flask_login import login_required, current_user
from datetime import datetime, timezone
from .models import Event, db, User
from werkzeug.utils import secure_filename
import os

main = Blueprint("main", __name__)

@main.before_request
def before_request():
    g.now = datetime.now(timezone.utc)

@main.route("/")
def home():
    # Get 3 random upcoming events
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
            subject = request.form.get("subject")
            message = request.form.get("message")

            if not email or not message or not subject:
                flash("Please fill in all fields.", "error")
                return redirect(url_for("main.contactOrganizer"))


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
        # Handle profile picture upload
        profile_picture = request.files.get("profile_picture")
        if profile_picture:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            filename = secure_filename(f"{current_user.id}_{profile_picture.filename}")
            file_path = os.path.join(upload_dir, filename)
            
            # Save the file
            profile_picture.save(file_path)
            
            # Update user's profile picture path
            current_user.profile_picture = f"/static/uploads/profiles/{filename}"
            db.session.commit()
            flash("Profile picture updated successfully!", "success")
            return redirect(url_for("main.profile"))

        # Handle other profile updates
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("username")
        email = request.form.get("email")

        if not first_name or not last_name:
            flash("First name and last name are required.", "error")
            return redirect(url_for("main.profile"))

        # Check if username is already taken by another user
        if username and username != current_user.username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username is already taken.", "error")
                return redirect(url_for("main.profile"))
            current_user.username = username

        # Check if email is already taken by another user
        if email and email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email is already taken.", "error")
                return redirect(url_for("main.profile"))
            current_user.email = email

        current_user.first_name = first_name
        current_user.last_name = last_name

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("main.profile"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("main.profile"))


@main.route("/contact", methods=["GET", "POST"])
@login_required
def contact():
    if request.method == "POST":
        try:
            email = request.form.get("email")
            name = request.form.get("email")
            subject = request.form.get("subject")
            message = request.form.get("message")

            if not email or not name or not message or not subject:
                flash("Please fill in all fields.", "error")
                return redirect(url_for("main.contact"))


            flash("Message has been sent successfully!", "success")
            return redirect(url_for("main.contact"))

        except Exception as e:
            current_app.logger.error(f"Error sending message: {str(e)}")
            flash("An error occurred while sending your message. Please try again.", "error")
            return redirect(url_for("main.contactO"))
        
    return render_template("contact.html", now=g.now)

@main.route("/update-screen-width", methods=["POST"])
def update_screen_width():
    if request.is_json:
        width = request.json.get("width")
        if width:
            session["screen_width"] = width
            return jsonify({"success": True})

        return jsonify({"success": False}), 400

@main.route("/change-password", methods=["POST"])
@login_required
def changePassword():
    try:
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validate input
        if not current_password or not new_password or not confirm_password:
            flash("All fields are required.", "error")
            return redirect(url_for("main.profile"))

        # Validate current password
        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("main.profile"))

        # Validate new password
        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "error")
            return redirect(url_for("main.profile"))

        # Validate password confirmation
        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return redirect(url_for("main.profile"))

        # Update password
        current_user.set_password(new_password)
        db.session.commit()

        flash("Password updated successfully!", "success")
        return redirect(url_for("main.profile"))

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "error")

@main.route("/update-preferences", methods=["POST"])
@login_required
def updatePreferences():
    try:
        email_notifications = request.form.get("email_notifications") == "on"
        theme_preference = request.form.get("theme_preference")

        # Validate theme preference
        if theme_preference not in ["light", "dark", "system"]:
            flash("Invalid theme preference.", "error")
            return redirect(url_for("main.profile"))

        # Update preferences
        current_user.email_notifications = email_notifications
        current_user.theme_preference = theme_preference
        db.session.commit()

        flash("Preferences updated successfully!", "success")
        return redirect(url_for("main.profile"))

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("main.profile"))