from flask import Blueprint, render_template, jsonify, request, current_app, send_file
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from .models import Event, Order, TicketType, db, UserRole, EventRegistration
from .auth import role_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import os

reports = Blueprint("reports", __name__)

def get_company_details():
    """Helper function to return company details for reports."""
    return {
        'name': 'EventFlow',
        'address': '123 Event Street, Nairobi, Kenya',
        'phone': '+254 700 000000',
        'email': 'info@eventflow.com',
        'website': 'www.eventflow.com',
        'logo_path': os.path.join(current_app.root_path, 'static', 'images', 'logo.png')
    }

def add_company_header(elements, styles, start_date=None, end_date=None):
    """Helper function to add company header to reports."""
    company = get_company_details()
    
    # Try to add company logo
    try:
        if os.path.exists(company['logo_path']):
            img = Image(company['logo_path'], width=1.5*inch, height=1.5*inch)
            elements.append(img)
    except Exception as e:
        current_app.logger.error(f"Error adding logo: {e}")
    
    # Add company name
    company_name_style = ParagraphStyle(
        'CompanyName',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=12,
        textColor=colors.HexColor('#1a237e')  # Dark blue color
    )
    elements.append(Paragraph(company['name'], company_name_style))
    
    # Add company details
    company_details_style = ParagraphStyle(
        'CompanyDetails',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#424242'),  # Dark grey color
        spaceAfter=20
    )
    company_details = f"""
    {company['address']}<br/>
    Phone: {company['phone']}<br/>
    Email: {company['email']}<br/>
    Website: {company['website']}
    """
    elements.append(Paragraph(company_details, company_details_style))
    
    # Add date range if provided
    if start_date and end_date:
        date_style = ParagraphStyle(
            'DateRange',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#424242'),
            spaceAfter=20
        )
        date_range = f"Report Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elements.append(Paragraph(date_range, date_style))
    
    # Add separator line
    elements.append(Spacer(1, 20))
    
def generate_pdf_report(title, table_data, start_date=None, end_date=None, summary_data=None):
    """Helper function to generate PDF reports with consistent styling."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Add company header
    add_company_header(elements, styles, start_date, end_date)
    
    # Add report title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        textColor=colors.HexColor('#1a237e')  # Dark blue color
    )
    elements.append(Paragraph(title, title_style))
    
    # Add summary data if provided
    if summary_data:
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            textColor=colors.HexColor('#424242')
        )
        for key, value in summary_data.items():
            elements.append(Paragraph(f"{key}: {value}", summary_style))
        elements.append(Spacer(1, 20))
    
    # Create and style the table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@reports.route("/reports/dashboard")
@login_required
@role_required(UserRole.ORGANIZER)
def dashboard():
    # Get date range from query parameters or use None to show all data
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    # Get user's events
    events_query = Event.query.filter(Event.user_id == current_user.id)
    
    # Apply date filter only if dates are provided
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            events_query = events_query.filter(Event.date.between(start_date, end_date))
        except ValueError as e:
            current_app.logger.error(f"Date parsing error: {e}")
            return jsonify({"error": "Invalid date format"}), 400
    
    events = events_query.all()
    current_app.logger.info(f"Found {len(events)} events for user {current_user.id}")
    
    # Calculate summary metrics with debug logging
    total_revenue = 0
    total_orders = 0
    total_tickets_sold = 0
    total_free_registrations = 0
    
    for event in events:
        # Debug log for each order
        for order in event.orders:
            current_app.logger.info(
                f"Order {order.id} for {event.title}: Status={order.payment_status}, Amount={order.total_amount}, Is Paid={order.is_paid}"
            )
            current_app.logger.info(
                f"Ticket details type: {type(order.ticket_details)}, Content: {order.ticket_details}"
            )
            current_app.logger.info(f"Ticket count: {order.get_ticket_count()}")
        
        event_revenue = sum(
            order.total_amount for order in event.orders if order.is_paid
        )
        event_orders = len(event.orders)
        event_tickets = sum(
            order.get_ticket_count() for order in event.orders if order.is_paid
        )
        event_free_regs = len(event.registrations)
        
        current_app.logger.info(
            f"Event {event.title}: Revenue={event_revenue}, Orders={event_orders}, Tickets={event_tickets}, Free Regs={event_free_regs}"
        )
        
        total_revenue += event_revenue
        total_orders += event_orders
        total_tickets_sold += event_tickets
        total_free_registrations += event_free_regs
    
    current_app.logger.info(
        f"Total metrics - Revenue: {total_revenue}, Orders: {total_orders}, Tickets: {total_tickets_sold}, Free Regs: {total_free_registrations}"
    )
    
    # Calculate average order value
    total_paid_orders = sum(
        1 for event in events for order in event.orders if order.is_paid
    )
    avg_order_value = total_revenue / total_paid_orders if total_paid_orders > 0 else 0
    current_app.logger.info(f"Average order value: {avg_order_value}")
    
    # Get total events
    total_events = len(events)
    
    # Get daily sales data with debug logging
    daily_sales = []
    if events:
        current_date = datetime.now(timezone.utc)
        start_date = current_date - timedelta(days=6)  # Last 7 days including today

        while current_date >= start_date:
            daily_revenue = sum(
                order.total_amount 
                for event in events 
                for order in event.orders 
                if order.is_paid and order.created_at.date() == current_date.date()
            )
            daily_free_registrations = sum(
                1 
                for event in events 
                for registration in event.registrations 
                if registration.registration_date.date() == current_date.date()
            )
            
            current_app.logger.info(
                f"Daily data for {current_date.date()}: Revenue={daily_revenue}, Free Regs={daily_free_registrations}"
            )

            daily_sales.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "daily_revenue": daily_revenue,
                    "free_registrations": daily_free_registrations,
                }
            )
            current_date -= timedelta(days=1)

        # Sort by date in ascending order
        daily_sales.sort(key=lambda x: x["date"])
    
    # Get ticket sales by type with debug logging
    ticket_sales = []
    ticket_type_totals = {}  # Dictionary to store aggregated totals
    
    for event in events:
        if event.is_paid_event:
            for ticket_type in event.ticket_types:
                current_app.logger.info(
                    f"Processing ticket type {ticket_type.id} ({ticket_type.ticket_type}) for event {event.title}"
                )
                total_sold = 0
                
                # Get all paid orders for this event
                paid_orders = [order for order in event.orders if order.is_paid]
                
                for order in paid_orders:
                    # Debug log the ticket details
                    
                    # Handle both dictionary and list formats
                    if isinstance(order.ticket_details, dict):
                        # Dictionary format (key is ticket_type_id)
                        ticket_info = order.ticket_details.get(str(ticket_type.id), {})
                        count = int(ticket_info.get('quantity', 0))
                        if count > 0:
                            total_sold += count
                    elif isinstance(order.ticket_details, list):
                        # List format
                        for ticket_detail in order.ticket_details:
                            if str(ticket_detail.get('ticket_type_id')) == str(ticket_type.id):
                                count = int(ticket_detail.get('quantity', 0))

                                total_sold += count
                    else:
                        current_app.logger.warning(
                            f"Unexpected ticket_details format in order {order.id}: {type(order.ticket_details)}"
                        )
                
                if total_sold > 0:
                    # Use the ticket type as the key
                    type_name = ticket_type.custom_type or ticket_type.ticket_type
                    if type_name in ticket_type_totals:
                        ticket_type_totals[type_name] += total_sold
                    else:
                        ticket_type_totals[type_name] = total_sold
                    
                    current_app.logger.info(
                        f"Updated total for {type_name}: {ticket_type_totals[type_name]}"
                    )
    
    # Convert the aggregated totals to the list format expected by the template
    ticket_sales = [
        {"ticket_type": type_name, "total_sold": total}
        for type_name, total in ticket_type_totals.items()
    ]
    
    current_app.logger.info(f"Final ticket sales data: {ticket_sales}")
    
    # Get revenue by category with debug logging
    category_revenue = {}
    for event in events:
        if event.category not in category_revenue:
            category_revenue[event.category] = 0
        event_revenue = sum(
            order.total_amount for order in event.orders if order.is_paid
        )
        category_revenue[event.category] += event_revenue
        current_app.logger.info(
            f"Category revenue for {event.category}: {event_revenue}"
        )
    
    category_revenue = [
        {"category": category, "revenue": revenue}
        for category, revenue in category_revenue.items()
    ]
    
    # Get registration trends with debug logging
    registration_trends = []
    if events:
        current_date = datetime.now(timezone.utc)
        start_date = current_date - timedelta(days=5)  # Last 6 days including today

        while current_date >= start_date:
            paid_registrations = sum(
                1 
                for event in events 
                for order in event.orders 
                if order.is_paid and order.created_at.date() == current_date.date()
            )
            free_registrations = sum(
                1 
                for event in events 
                for registration in event.registrations 
                if registration.registration_date.date() == current_date.date()
            )
            
            current_app.logger.info(
                f"Registration trends for {current_date.date()}: Paid={paid_registrations}, Free={free_registrations}"
            )

            registration_trends.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "paid_registrations": paid_registrations,
                    "free_registrations": free_registrations,
                }
            )
            current_date -= timedelta(days=1)

        # Sort by date in ascending order
        registration_trends.sort(key=lambda x: x["date"])
    
    # Get event performance data with debug logging
    event_performance = []
    for event in events:
        total_capacity = (
            sum(ticket.quantity for ticket in event.ticket_types) 
            if event.is_paid_event 
            else event.free_ticket_quantity or 0
        )
        
        paid_tickets = sum(
            order.get_ticket_count() for order in event.orders if order.is_paid
        )
        free_registrations = len(event.registrations)
        
        total_registrations = (
            paid_tickets if event.is_paid_event else free_registrations
        )
        revenue = sum(order.total_amount for order in event.orders if order.is_paid)
        
        occupancy_rate = (
            (total_registrations / total_capacity * 100) if total_capacity > 0 else 0
        )

        current_app.logger.info(
            f"Event performance for {event.title}: Capacity={total_capacity}, Regs={total_registrations}, Revenue={revenue}, Occupancy={occupancy_rate}%"
        )

        event_performance.append(
            {
                "title": event.title,
                "total_capacity": total_capacity,
                "total_registrations": total_registrations,
                "revenue": revenue,
                "occupancy_rate": occupancy_rate,
                "is_upcoming": event.is_upcoming(datetime.now(timezone.utc)),
            }
        )
    
    return render_template(
        "reports/dashboard.html",
        start_date=start_date.strftime("%Y-%m-%d") if start_date else None,
        end_date=end_date.strftime("%Y-%m-%d") if end_date else None,
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_tickets_sold=total_tickets_sold,
        total_free_registrations=total_free_registrations,
        avg_order_value=avg_order_value,
        total_events=total_events,
        daily_sales=daily_sales,
        ticket_sales=ticket_sales,
        category_revenue=category_revenue,
        registration_trends=registration_trends,
        event_performance=event_performance,
    )

@reports.route("/reports/export")
@login_required
@role_required(UserRole.ORGANIZER)
def export_report():
    # Get report type and format from query parameters
    report_type = request.args.get("type", "sales")
    export_format = request.args.get("format", "pdf")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    # Debug logging
    current_app.logger.info(
        f"Export request - Type: {report_type}, Format: {export_format}, Start: {start_date}, End: {end_date}"
    )
    
    # Get organizer's events
    events_query = Event.query.filter(Event.user_id == current_user.id)
    
    # Apply date filter only if dates are provided
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            events_query = events_query.filter(Event.date.between(start_date, end_date))
        except ValueError as e:
            current_app.logger.error(f"Date parsing error: {e}")
            return jsonify({"error": "Invalid date format"}), 400
    
    events = events_query.all()
    event_ids = [event.id for event in events]
    current_app.logger.info(f"Found {len(events)} events for export")
    
    if report_type == "sales":
        # Generate sales report data
        sales_data = (
            db.session.query(
                Event.title,
                func.count(Order.id).label("total_orders"),
                func.sum(Order.total_amount).label("total_revenue"),
            )
            .join(Order)
            .filter(
                Event.id.in_(event_ids),
                Order.payment_status.in_(["paid", "completed"])
            )
            .group_by(Event.title)
            .all()
        )
        
        # Calculate summary data
        total_revenue = sum(sale.total_revenue for sale in sales_data)
        total_orders = sum(sale.total_orders for sale in sales_data)
        
        # Prepare table data
        table_data = [["Event", "Total Orders", "Total Revenue"]]
        for sale in sales_data:
            table_data.append([
                sale.title,
                str(sale.total_orders),
                f"KES {sale.total_revenue:,.2f}"
            ])
        
        # Generate PDF using helper function
        buffer = generate_pdf_report(
            "Sales Report",
            table_data,
            start_date,
            end_date,
            {
                "Total Revenue": f"KES {total_revenue:,.2f}",
                "Total Orders": total_orders
            }
        )
        
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"sales_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == "tickets":
        # Generate ticket sales report with proper grouping
        ticket_data = (
            db.session.query(
                Event.title,
                TicketType.id,
                TicketType.ticket_type,
                TicketType.custom_type,
                func.sum(
                    func.cast(
                        func.json_extract(
                            Order.ticket_details,
                            f'$."*".quantity'
                        ),
                        db.Integer
                    )
                ).label("total_sold")
            )
            .join(Event, TicketType.event_id == Event.id)
            .join(
                Order,
                db.and_(
                    Order.event_id == Event.id,
                    Order.payment_status.in_(["paid", "completed"])
                )
            )
            .filter(Event.id.in_(event_ids))
            .group_by(Event.title, TicketType.id, TicketType.ticket_type, TicketType.custom_type)
            .order_by(Event.title, TicketType.ticket_type)
            .all()
        )
        
        # Process ticket data manually since JSON extraction is complex
        ticket_totals = {}  # Dictionary to store totals by event and ticket type
        
        # Get all orders for the events
        orders = Order.query.filter(
            Order.event_id.in_(event_ids),
            Order.payment_status.in_(["paid", "completed"])
        ).all()
        
        # Process each order
        for order in orders:
            if not order.ticket_details:
                continue
                
            current_app.logger.info(f"Processing order {order.id} with details: {order.ticket_details}")
            
            # Handle both dictionary and list formats
            if isinstance(order.ticket_details, dict):
                # Dictionary format (key is ticket_type_id)
                for ticket_id, details in order.ticket_details.items():
                    quantity = int(details.get('quantity', 0))
                    if quantity > 0:
                        key = (order.event_id, int(ticket_id))
                        if key not in ticket_totals:
                            ticket_totals[key] = 0
                        ticket_totals[key] += quantity
            elif isinstance(order.ticket_details, list):
                # List format
                for detail in order.ticket_details:
                    ticket_id = detail.get('ticket_type_id')
                    quantity = int(detail.get('quantity', 0))
                    if ticket_id and quantity > 0:
                        key = (order.event_id, int(ticket_id))
                        if key not in ticket_totals:
                            ticket_totals[key] = 0
                        ticket_totals[key] += quantity
        
        # Prepare table data with better organization
        table_data = [["Event", "Ticket Type", "Total Sold"]]
        total_tickets = 0
        current_event = None
        event_total = 0
        
        # Get all ticket types for proper ordering
        ticket_types = (
            TicketType.query
            .join(Event)
            .filter(Event.id.in_(event_ids))
            .order_by(Event.title, TicketType.ticket_type)
            .all()
        )
        
        for ticket_type in ticket_types:
            # Use custom type if available, otherwise use default ticket type
            ticket_type_name = ticket_type.custom_type or ticket_type.ticket_type
            key = (ticket_type.event_id, ticket_type.id)
            sold_count = ticket_totals.get(key, 0)
            
            # Add event subtotal if we're moving to a new event
            if current_event and current_event != ticket_type.event.title:
                table_data.append([
                    f"{current_event} Total",
                    "",
                    str(event_total)
                ])
                table_data.append(["", "", ""])  # Empty row for spacing
                event_total = 0
            
            # Update current event and totals
            current_event = ticket_type.event.title
            event_total += sold_count
            total_tickets += sold_count
            
            # Add the ticket type row
            table_data.append([
                ticket_type.event.title,
                ticket_type_name,
                str(sold_count)
            ])
            
            current_app.logger.info(
                f"Ticket data - Event: {ticket_type.event.title}, Type: {ticket_type_name}, Sold: {sold_count}"
            )
        
        # Add the last event's total
        if current_event:
            table_data.append([
                f"{current_event} Total",
                "",
                str(event_total)
            ])
        
        # Add grand total
        table_data.append(["", "", ""])  # Empty row for spacing
        table_data.append([
            "Grand Total",
            "",
            str(total_tickets)
        ])
        
        # Generate PDF using helper function
        buffer = generate_pdf_report(
            "Ticket Sales Report",
            table_data,
            start_date,
            end_date,
            {
                "Total Events": len(set(t.event.title for t in ticket_types)),
                "Total Ticket Types": len(ticket_types),
                "Total Tickets Sold": total_tickets
            }
        )
        
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"ticket_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == "registrations":
        # Generate registration report
        registration_data = (
            db.session.query(
                Event.title,
                func.count(EventRegistration.id).label("free_registrations"),
                func.count(Order.id).label("paid_registrations"),
            )
            .outerjoin(EventRegistration)
            .outerjoin(Order)
            .filter(Event.id.in_(event_ids))
            .group_by(Event.title)
            .all()
        )
        
        # Prepare table data
        table_data = [["Event", "Free Registrations", "Paid Registrations", "Total"]]
        total_free = 0
        total_paid = 0
        
        for reg in registration_data:
            total = reg.free_registrations + reg.paid_registrations
            table_data.append([
                reg.title,
                str(reg.free_registrations),
                str(reg.paid_registrations),
                str(total)
            ])
            total_free += reg.free_registrations
            total_paid += reg.paid_registrations
        
        # Generate PDF using helper function
        buffer = generate_pdf_report(
            "Registration Report",
            table_data,
            start_date,
            end_date,
            {
                "Total Free Registrations": total_free,
                "Total Paid Registrations": total_paid,
                "Total Registrations": total_free + total_paid
            }
        )
        
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"registration_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == "category":
        # Generate category revenue report
        category_data = (
            db.session.query(
                Event.category,
                func.sum(Order.total_amount).label("total_revenue")
            )
            .join(Order)
            .filter(
                Event.id.in_(event_ids),
                Order.payment_status.in_(["paid", "completed"])
            )
            .group_by(Event.category)
            .all()
        )
        
        # Prepare table data
        table_data = [["Category", "Total Revenue"]]
        total_revenue = 0
        
        for cat in category_data:
            table_data.append([
                cat.category,
                f"KES {cat.total_revenue:,.2f}"
            ])
            total_revenue += cat.total_revenue
        
        # Generate PDF using helper function
        buffer = generate_pdf_report(
            "Revenue by Category Report",
            table_data,
            start_date,
            end_date,
            {
                "Total Revenue": f"KES {total_revenue:,.2f}"
            }
        )
        
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"category_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == "performance":
        # Generate event performance report
        performance_data = (
            db.session.query(
                Event.title,
                func.count(Order.id).label("total_orders"),
                func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
                func.count(EventRegistration.id).label("free_registrations"),
            )
            .outerjoin(Order)
            .outerjoin(EventRegistration)
            .filter(Event.id.in_(event_ids))
            .group_by(Event.title)
            .all()
        )
        
        # Prepare table data
        table_data = [["Event", "Total Orders", "Total Revenue", "Free Registrations", "Total Registrations"]]
        total_orders = 0
        total_revenue = 0
        total_free = 0
        
        for perf in performance_data:
            total_regs = perf.total_orders + perf.free_registrations
            table_data.append([
                perf.title,
                str(perf.total_orders),
                f"KES {float(perf.total_revenue):,.2f}",
                str(perf.free_registrations),
                str(total_regs)
            ])
            total_orders += perf.total_orders
            total_revenue += float(perf.total_revenue)
            total_free += perf.free_registrations
        
        # Generate PDF using helper function
        buffer = generate_pdf_report(
            "Event Performance Report",
            table_data,
            start_date,
            end_date,
            {
                "Total Orders": total_orders,
                "Total Revenue": f"KES {total_revenue:,.2f}",
                "Total Free Registrations": total_free,
                "Total Registrations": total_orders + total_free
            }
        )
        
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"performance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    return jsonify({"error": "Invalid report type"}), 400
