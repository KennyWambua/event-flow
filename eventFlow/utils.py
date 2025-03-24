import locale

# Set locale for currency formatting
try:
    locale.setlocale(locale.LC_ALL, 'en_KE.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

def format_currency(amount, currency='KES', include_symbol=True):
    """
    Format currency amount with proper formatting and symbol.
    
    Args:
        amount (float): The amount to format
        currency (str): The currency code (default: 'KES')
        include_symbol (bool): Whether to include the currency symbol (default: True)
    
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        return ''
    
    try:
        # Round to nearest integer
        rounded_amount = round(float(amount))
        
        # Format with thousands separator
        formatted_amount = locale.format_string('%d', rounded_amount, grouping=True)
        
        if include_symbol:
            return f"{currency} {formatted_amount}"
        return formatted_amount
    except (ValueError, TypeError):
        return ''

def init_app(app):
    """Initialize utility functions with the Flask app"""
    # Register format_currency as a Jinja2 filter
    app.jinja_env.filters['format_currency'] = format_currency 