from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    current_app,
    flash,
    redirect,
    url_for,
    send_file
)
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, and_, desc, or_
from .models import Event, Order, TicketType, db, UserRole, EventRegistration
from . import db
from .auth import role_required

reports = Blueprint("reports", __name__)

@reports.route("/reports/dashboard")
@login_required
@role_required(UserRole.ORGANIZER)
def dashboard():
    # Get date range from query parameters or use None to show all data
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Debug logging
    current_app.logger.info(f"Dashboard request - Start date: {start_date}, End date: {end_date}")
    
    # Get user's events
    events_query = Event.query.filter(Event.user_id == current_user.id)
    
    # Apply date filter only if dates are provided
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
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
            current_app.logger.info(f"Order {order.id} for {event.title}: Status={order.payment_status}, Amount={order.total_amount}, Is Paid={order.is_paid}")
            current_app.logger.info(f"Ticket details type: {type(order.ticket_details)}, Content: {order.ticket_details}")
            current_app.logger.info(f"Ticket count: {order.get_ticket_count()}")
        
        event_revenue = sum(order.total_amount for order in event.orders if order.is_paid)
        event_orders = len(event.orders)
        event_tickets = sum(order.get_ticket_count() for order in event.orders if order.is_paid)
        event_free_regs = len(event.registrations)
        
        current_app.logger.info(f"Event {event.title}: Revenue={event_revenue}, Orders={event_orders}, Tickets={event_tickets}, Free Regs={event_free_regs}")
        
        total_revenue += event_revenue
        total_orders += event_orders
        total_tickets_sold += event_tickets
        total_free_registrations += event_free_regs
    
    current_app.logger.info(f"Total metrics - Revenue: {total_revenue}, Orders: {total_orders}, Tickets: {total_tickets_sold}, Free Regs: {total_free_registrations}")
    
    # Calculate average order value
    total_paid_orders = sum(1 for event in events for order in event.orders if order.is_paid)
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
            
            current_app.logger.info(f"Daily data for {current_date.date()}: Revenue={daily_revenue}, Free Regs={daily_free_registrations}")
            
            daily_sales.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'daily_revenue': daily_revenue,
                'free_registrations': daily_free_registrations
            })
            current_date -= timedelta(days=1)
        
        # Sort by date in ascending order
        daily_sales.sort(key=lambda x: x['date'])
    
    # Get ticket sales by type with debug logging
    ticket_sales = []
    for event in events:
        if event.is_paid_event:
            for ticket_type in event.ticket_types:
                current_app.logger.info(f"Calculating ticket sales for {event.title} - {ticket_type.ticket_type} (ID: {ticket_type.id})")
                total_sold = 0
                for order in event.orders:
                    if order.is_paid:
                        count = order.get_ticket_count(ticket_type.id)
                        current_app.logger.info(f"Order {order.id}: Ticket count for type {ticket_type.id} = {count}")
                        total_sold += count
                
                if total_sold > 0:
                    current_app.logger.info(f"Total ticket sales for {event.title} - {ticket_type.ticket_type}: {total_sold}")
                    ticket_sales.append({
                        'ticket_type': ticket_type.custom_type or ticket_type.ticket_type,
                        'total_sold': total_sold
                    })
    
    # Get revenue by category with debug logging
    category_revenue = {}
    for event in events:
        if event.category not in category_revenue:
            category_revenue[event.category] = 0
        event_revenue = sum(order.total_amount for order in event.orders if order.is_paid)
        category_revenue[event.category] += event_revenue
        current_app.logger.info(f"Category revenue for {event.category}: {event_revenue}")
    
    category_revenue = [
        {'category': category, 'revenue': revenue}
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
            
            current_app.logger.info(f"Registration trends for {current_date.date()}: Paid={paid_registrations}, Free={free_registrations}")
            
            registration_trends.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'paid_registrations': paid_registrations,
                'free_registrations': free_registrations
            })
            current_date -= timedelta(days=1)
        
        # Sort by date in ascending order
        registration_trends.sort(key=lambda x: x['date'])
    
    # Get event performance data with debug logging
    event_performance = []
    for event in events:
        total_capacity = (
            sum(ticket.quantity for ticket in event.ticket_types) 
            if event.is_paid_event 
            else event.free_ticket_quantity or 0
        )
        
        paid_tickets = sum(
            order.get_ticket_count() 
            for order in event.orders 
            if order.is_paid
        )
        free_registrations = len(event.registrations)
        
        total_registrations = paid_tickets if event.is_paid_event else free_registrations
        revenue = sum(
            order.total_amount 
            for order in event.orders 
            if order.is_paid
        )
        
        occupancy_rate = (
            (total_registrations / total_capacity * 100) 
            if total_capacity > 0 
            else 0
        )
        
        current_app.logger.info(f"Event performance for {event.title}: Capacity={total_capacity}, Regs={total_registrations}, Revenue={revenue}, Occupancy={occupancy_rate}%")
        
        event_performance.append({
            'title': event.title,
            'total_capacity': total_capacity,
            'total_registrations': total_registrations,
            'revenue': revenue,
            'occupancy_rate': occupancy_rate,
            'is_upcoming': event.is_upcoming(datetime.now(timezone.utc))
        })
    
    return render_template(
        'reports/dashboard.html',
        start_date=start_date.strftime('%Y-%m-%d') if start_date else None,
        end_date=end_date.strftime('%Y-%m-%d') if end_date else None,
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
        event_performance=event_performance
    )

@reports.route("/reports/export")
@login_required
@role_required(UserRole.ORGANIZER)
def export_report():
    # Get report type and format from query parameters
    report_type = request.args.get('type', 'sales')
    export_format = request.args.get('format', 'pdf')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Debug logging
    current_app.logger.info(f"Export request - Type: {report_type}, Format: {export_format}, Start: {start_date}, End: {end_date}")
    
    # Get organizer's events
    events_query = Event.query.filter(Event.user_id == current_user.id)
    
    # Apply date filter only if dates are provided
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            events_query = events_query.filter(Event.date.between(start_date, end_date))
        except ValueError as e:
            current_app.logger.error(f"Date parsing error: {e}")
            return jsonify({"error": "Invalid date format"}), 400
    
    events = events_query.all()
    event_ids = [event.id for event in events]
    current_app.logger.info(f"Found {len(events)} events for export")
    
    if report_type == 'sales':
        # Generate sales report data
        sales_data = db.session.query(
            Event.title,
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_revenue')
        ).join(Order).filter(
            Event.id.in_(event_ids),
            Order.payment_status.in_(['paid', 'completed'])
        ).group_by(Event.title).all()
        
        current_app.logger.info(f"Sales data: {len(sales_data)} records")
        for sale in sales_data:
            current_app.logger.info(f"Sale: {sale.title} - Orders: {sale.total_orders}, Revenue: {sale.total_revenue}")
        
        # Generate PDF report
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph("Sales Report", title_style))
        
        # Add date range if provided
        if start_date and end_date:
            date_style = ParagraphStyle(
                'DateRange',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20
            )
            elements.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", date_style))
        
        # Add summary
        total_revenue = sum(sale.total_revenue for sale in sales_data)
        total_orders = sum(sale.total_orders for sale in sales_data)
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=20
        )
        elements.append(Paragraph(f"Total Revenue: KES {total_revenue:.2f}", summary_style))
        elements.append(Paragraph(f"Total Orders: {total_orders}", summary_style))
        
        # Add table
        table_data = [['Event', 'Total Orders', 'Total Revenue']]
        for sale in sales_data:
            table_data.append([sale.title, str(sale.total_orders), f"KES {sale.total_revenue:.2f}"])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"sales_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == 'tickets':
        # Generate ticket sales report
        ticket_data = db.session.query(
            Event.title,
            TicketType.ticket_type,
            func.count(Order.id).label('total_sold')
        ).join(Order).join(TicketType).filter(
            Order.event_id.in_(event_ids),
            Order.payment_status.in_(['paid', 'completed'])
        ).group_by(Event.title, TicketType.ticket_type).all()
        
        current_app.logger.info(f"Ticket data: {len(ticket_data)} records")
        for ticket in ticket_data:
            current_app.logger.info(f"Ticket: {ticket.title} - {ticket.ticket_type}: {ticket.total_sold}")
        
        # Generate PDF report
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph("Ticket Sales Report", title_style))
        
        # Add date range if provided
        if start_date and end_date:
            date_style = ParagraphStyle(
                'DateRange',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20
            )
            elements.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", date_style))
        
        # Add table
        table_data = [['Event', 'Ticket Type', 'Total Sold']]
        for ticket in ticket_data:
            table_data.append([ticket.title, ticket.ticket_type, str(ticket.total_sold)])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"ticket_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == 'registrations':
        # Generate registration report
        registration_data = db.session.query(
            Event.title,
            func.count(EventRegistration.id).label('free_registrations'),
            func.count(Order.id).label('paid_registrations')
        ).outerjoin(EventRegistration).outerjoin(Order).filter(
            Event.id.in_(event_ids)
        ).group_by(Event.title).all()
        
        current_app.logger.info(f"Registration data: {len(registration_data)} records")
        for reg in registration_data:
            current_app.logger.info(f"Registration: {reg.title} - Free: {reg.free_registrations}, Paid: {reg.paid_registrations}")
        
        # Generate PDF report
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph("Registration Report", title_style))
        
        # Add date range if provided
        if start_date and end_date:
            date_style = ParagraphStyle(
                'DateRange',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20
            )
            elements.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", date_style))
        
        # Add table
        table_data = [['Event', 'Free Registrations', 'Paid Registrations', 'Total']]
        for reg in registration_data:
            total = reg.free_registrations + reg.paid_registrations
            table_data.append([reg.title, str(reg.free_registrations), str(reg.paid_registrations), str(total)])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"registration_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == 'category':
        # Generate category revenue report
        category_data = db.session.query(
            Event.category,
            func.sum(Order.total_amount).label('total_revenue')
        ).join(Order).filter(
            Event.id.in_(event_ids),
            Order.payment_status.in_(['paid', 'completed'])
        ).group_by(Event.category).all()
        
        current_app.logger.info(f"Category data: {len(category_data)} records")
        for cat in category_data:
            current_app.logger.info(f"Category: {cat.category} - Revenue: {cat.total_revenue}")
        
        # Generate PDF report
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph("Revenue by Category Report", title_style))
        
        # Add date range if provided
        if start_date and end_date:
            date_style = ParagraphStyle(
                'DateRange',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20
            )
            elements.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", date_style))
        
        # Add table
        table_data = [['Category', 'Total Revenue']]
        for cat in category_data:
            table_data.append([cat.category, f"KES {cat.total_revenue:.2f}"])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"category_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    elif report_type == 'performance':
        # Generate event performance report
        performance_data = db.session.query(
            Event.title,
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_revenue'),
            func.count(EventRegistration.id).label('free_registrations')
        ).outerjoin(Order).outerjoin(EventRegistration).filter(
            Event.id.in_(event_ids)
        ).group_by(Event.title).all()
        
        current_app.logger.info(f"Performance data: {len(performance_data)} records")
        for perf in performance_data:
            current_app.logger.info(f"Performance: {perf.title} - Orders: {perf.total_orders}, Revenue: {perf.total_revenue}, Free: {perf.free_registrations}")
        
        # Generate PDF report
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph("Event Performance Report", title_style))
        
        # Add date range if provided
        if start_date and end_date:
            date_style = ParagraphStyle(
                'DateRange',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20
            )
            elements.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", date_style))
        
        # Add table
        table_data = [['Event', 'Total Orders', 'Total Revenue', 'Free Registrations', 'Total Registrations']]
        for perf in performance_data:
            total_regs = perf.total_orders + perf.free_registrations
            table_data.append([
                perf.title,
                str(perf.total_orders),
                f"KES {perf.total_revenue:.2f}",
                str(perf.free_registrations),
                str(total_regs)
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"performance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    
    return jsonify({"error": "Invalid report type"}), 400

