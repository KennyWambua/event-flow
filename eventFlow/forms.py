from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeField, TextAreaField, SelectField, URLField, MultipleFileField, FieldList, FormField, IntegerField, DecimalField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, URL, Optional, NumberRange
from .models import User
from flask_wtf.file import FileField, FileAllowed, FileRequired

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember = BooleanField('Remember me')
    submit = SubmitField('Log In')

class SignupForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    confirm_email = StringField('Confirm Email', validators=[
        DataRequired(),
        Email(),
        EqualTo('email', message='Emails must match')
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    accept_terms = BooleanField('I accept the Terms and Conditions', validators=[
        DataRequired(message="You must accept the terms and conditions")
    ])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class TicketTypeForm(FlaskForm):
    ticket_type = SelectField('Ticket Type', choices=[
        ('', 'Select Ticket Type'),
        ('early-bird', 'Early Bird - Limited time offer'),
        ('regular', 'Regular - Standard admission'),
        ('vip', 'VIP - Premium experience'),
        ('vvip', 'VVIP - Ultimate experience'),
        ('student', 'Student - Valid student ID required'),
        ('group', 'Group - Minimum 5 people'),
        ('custom', 'Custom Type - Create your own')
    ], validators=[DataRequired(message="Please select a ticket type")])
    
    custom_type = StringField('Custom Type Name', validators=[
        Optional(),
        Length(min=2, max=50, message="Custom type name must be between 2 and 50 characters")
    ])
    
    quantity = IntegerField('Quantity Available', validators=[
        DataRequired(),
        NumberRange(min=1, message="Quantity must be at least 1")
    ])
    
    price = DecimalField('Price', 
        places=2,  # Ensure 2 decimal places
        rounding=None,  # Don't round the input
        validators=[
            DataRequired(message="Please enter a price"),
            NumberRange(min=0, message="Price cannot be negative")
        ]
    )
    
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message="Description must not exceed 500 characters")
    ])

    def validate(self):
        if not super().validate():
            return False
            
        if self.ticket_type.data == 'custom' and not self.custom_type.data:
            self.custom_type.errors.append('Please enter a name for your custom ticket type')
            return False
            
        return True

class EventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired()])
    date = DateTimeField('Event Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('music', 'Music'),
        ('food', 'Food & Drink'),
        ('business', 'Business'),
        ('arts', 'Arts & Culture'),
        ('sports', 'Sports')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    images = MultipleFileField('Upload Images', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    image_url = URLField('Enter Image URL', validators=[Optional(), URL()])
    is_paid_event = BooleanField('This is a paid event')
    currency = SelectField('Currency', choices=[
        ('KES', 'KES - Kenyan Shilling'),
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound')
    ], validators=[Optional()])
    
    ticket_types = FieldList(
        FormField(TicketTypeForm), 
        min_entries=1,
        max_entries=5,
        label='Ticket Types'
    )

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators=extra_validators)
        if not initial_validation:
            return False
            
        if not self.images.data[0] and not self.image_url.data:
            self.images.errors.append('Please either upload images or provide an image URL')
            return False
            
        if self.images.data[0] and self.image_url.data:
            self.images.errors.append('Please provide either image uploads or URL, not both')
            return False
            
        return True 
        return True 