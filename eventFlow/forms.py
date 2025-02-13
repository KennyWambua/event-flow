from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeField, TextAreaField, SelectField, URLField, MultipleFileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, URL, Optional
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