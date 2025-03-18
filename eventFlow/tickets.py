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

tickets = Blueprint("tickets", __name__)

@tickets.before_request
def before_request():
    g.now = datetime.now(timezone.utc)


@tickets.route('/my-tickets')
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

@tickets.route('/cancel-registration/<int:registration_id>', methods=['POST'])
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

@tickets.route('/create-order', methods=['POST'])
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
        payment_url = url_for('tickets.process_payment', order_id=order.id, _external=True)
        
        return jsonify({
            'success': True,
            'redirect_url': payment_url,
            'order_id': order.id
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating order: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your order'}), 500

@tickets.route('/process-payment/<int:order_id>', methods=['GET', 'POST'])
@login_required
def process_payment(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
      
    ticket_details = json.loads(order.ticket_details) if isinstance(order.ticket_details, str) else order.ticket_details
    
    if request.method == 'GET':
        return render_template('payment.html', order=order, event=order.event, tickets=ticket_details)
    
    if request.method == 'POST':
      data = request.get_json()
      print("Received Data:", data) 
      phone_number = data.get('phone')
            
      if not phone_number or len(phone_number) < 9:
        return jsonify({'error': 'Phone number is required'}), 400
      
      try:
        
        # Update ticket quantities
        for ticket_id, ticket_detail in ticket_details.items():
          ticket_type =  TicketType.query.get(ticket_id)
          if ticket_type:
            new_quantity = ticket_type.quantity - ticket_detail['quantity']
            if new_quantity < 0:
              return jsonify({'error': 'Not enough tickets available'}), 400
            
            ticket_type.quantity = new_quantity
            
        # Update order status
        order.payment_status = 'completed'
        db.session.commit()
        
        return jsonify({
          'success': True,
          'message': 'Payment processed successfully'
        })
        
      except Exception as e:
        db.session.rollback()
        return jsonify({
								'error': str(e)
						}), 500

@tickets.route('/delete-order/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Ensure the order belongs to the current user
    if order.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Only allow deletion of pending payments
    if order.payment_status != 'pending':
        return jsonify({'error': 'Cannot delete orders with completed payments'}), 400
    
    try:
        db.session.delete(order)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Order deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete order'}), 500

@tickets.route('/download-tickets/<int:order_id>')
@login_required
def download_tickets(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Check if payment is completed
    if order.payment_status != 'completed':
        return jsonify({'error': 'Payment not completed'}), 400
    
    # Create PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Get event details
    event = order.event
    user = current_user
    
    # Add event logo/header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1*inch, height-1*inch, event.title)
    
    # Add event details
    c.setFont("Helvetica", 12)
    y = height - 2*inch
    c.drawString(1*inch, y, f"Date: {event.date_utc.strftime('%B %d, %Y at %I:%M %p')}")
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Location: {event.location}")
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Attendee: {current_user.first_name} {current_user.last_name}")
    
    # Add ticket details
    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "Ticket Details:")
    c.setFont("Helvetica", 12)
    
    ticket_details = json.loads(order.ticket_details) if isinstance(order.ticket_details, str) else order.ticket_details
    print("DEBUG: Ticket details structure ->", ticket_details)
    
    for ticket_id, ticket_detail in ticket_details.items():
      try:
        ticket_id_int = int(ticket_id)  # Convert ticket ID to integer
        ticket_type = TicketType.query.get(ticket_id_int)
        ticket_name = ticket_detail.get("name", "Unknown Ticket")  # Use ticket name from JSON
        ticket_quantity = ticket_detail.get("quantity", 0)
        ticket_price = ticket_detail.get("price", 0)
        y -= 0.3 * inch  # Move down for each ticket
        c.drawString(1*inch, y, f"{ticket_name} x {ticket_quantity} @ {ticket_price} KES")
            
      except Exception as e:
        print(f"Error displaying ticket {ticket_id}: {str(e)}")
    
    # Generate QR code
    ticket_details = json.loads(order.ticket_details) if isinstance(order.ticket_details, str) else order.ticket_details
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr_data = f"""
    Attendee Details
    	Name: {user.first_name} {user.last_name}
    	Email: {user.email}

    Event Details
    	Title: {event.title}
    	Date: {event.date_utc.strftime('%B %d, %Y at %I:%M %p')}
    	Location: {event.location}

    Ticket Details
    """  
    for ticket_detail in ticket_details.values():
        qr_data += f" {ticket_detail['name']} - {ticket_detail['quantity']} Ticket(s) @ {ticket_detail['price']} KES\n "

    qr.add_data(qr_data.strip()) 
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    
    qr_image = ImageReader(qr_buffer)
    c.drawImage(qr_image, width-3*inch, height-3*inch, width=2*inch, height=2*inch)
    
    # Add footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(1*inch, 0.5*inch, "This ticket is valid for one-time entry only. Please present this ticket at the event entrance.")
    
    c.save()
    buffer.seek(0)
    
    safe_event_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in event.title)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{safe_event_name}_ticket.pdf",
        mimetype='application/pdf'
    )

@tickets.route('/download-free-ticket/<int:registration_id>')
@login_required
def download_free_ticket(registration_id):
    registration = EventRegistration.query.get_or_404(registration_id)
    
    if registration.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    event = registration.event

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Generate ticket PDF
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1*inch, height-1*inch, event.title)

    c.setFont("Helvetica", 12)
    y = height - 2*inch
    c.drawString(1*inch, y, f"Date: {event.date_utc.strftime('%B %d, %Y at %I:%M %p')}")
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Location: {event.location}")
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Attendee: {current_user.first_name} {current_user.last_name}")

    # Generate QR Code
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr_data = f"""
    Attendee Details
    Name: {current_user.first_name} {current_user.last_name}
    Email: {current_user.email}

    Event Details
    Title: {event.title}
    Date: {event.date_utc.strftime('%B %d, %Y at %I:%M %p')}
    Location: {event.location}
    """
    
    qr.add_data(qr_data.strip())
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    qr_image = ImageReader(qr_buffer)
    c.drawImage(qr_image, width-3*inch, height-3*inch, width=2*inch, height=2*inch)

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(1*inch, 0.5*inch, "This ticket is valid for one-time entry only.")

    c.save()
    buffer.seek(0)

    safe_event_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in event.title)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{safe_event_name}_free_ticket.pdf",
        mimetype='application/pdf'
    )


@tickets.route('/generate-ticket-qr/<int:order_id>')
@login_required
def generate_ticket_qr(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Check if payment is completed
    if order.payment_status != 'completed':
        return jsonify({'error': 'Payment not completed'}), 400
    
    event = order.event
    user = current_user
    
    ticket_details = json.loads(order.ticket_details) if isinstance(order.ticket_details, str) else order.ticket_details
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr_data = f"""
    Attendee Details
    	Name: {user.first_name} {user.last_name}
    	Email: {user.email}

    Event Details
    	Title: {event.title}
    	Date: {event.date_utc.strftime('%B %d, %Y at %I:%M %p')}
    	Location: {event.location}

    Ticket Details
    """  
    for ticket_detail in ticket_details.values():
        qr_data += f" {ticket_detail['name']} - {ticket_detail['quantity']} Ticket(s) @ {ticket_detail['price']} KES\n "
    
    qr.add_data(qr_data.strip()) 
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(
        img_buffer,
        mimetype='image/png',
        as_attachment=False
    )