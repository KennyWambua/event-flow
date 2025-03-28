from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    DateTimeField,
    TextAreaField,
    SelectField,
    MultipleFileField,
    FieldList,
    FormField,
    IntegerField,
    DecimalField,
    RadioField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    ValidationError,
    Optional,
    NumberRange,
)
from .models import UserRole
from flask_wtf.file import FileAllowed
from flask import request


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me logged in")
    submit = SubmitField("Log In")


class SignupForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    confirm_email = StringField('Confirm Email', validators=[
        DataRequired(),
        EqualTo('email', message='Email addresses must match')
    ])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = RadioField(
        'Role',
        choices=[
            (UserRole.ATTENDEE.name, 'Attendee'),
            (UserRole.ORGANIZER.name, 'Organizer')
        ],
        validators=[DataRequired()],
        default=UserRole.ATTENDEE.name
    )
    accept_terms = BooleanField('I accept the Terms of Service', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

class BaseForm(FlaskForm):
    class Meta:
        # Disable CSRF for all forms
        csrf = False


class TicketTypeForm(BaseForm):
    ticket_type = SelectField(
        "Ticket Type",
        choices=[
            ("", "Select Ticket Type"),
            ("early-bird", "Early Bird"),
            ("regular", "Regular"),
            ("vip", "VIP"),
            ("vvip", "VVIP"),
            ("student", "Student"),
            ("group", "Group"),
            ("custom", "Custom"),
        ],
        validators=[DataRequired(message="Please select a ticket type")],
    )

    custom_type = StringField("Custom Type Name", validators=[Optional()])

    quantity = IntegerField(
        "Quantity available",
        validators=[DataRequired(), NumberRange(min=1)],
        default=100,
    )

    price = DecimalField(
        "Price", validators=[DataRequired(), NumberRange(min=0)], places=2, default=0.00
    )

    description = TextAreaField("Description (Optional)", validators=[Optional()])


class EventForm(FlaskForm):
    title = StringField(
        "Event Title", validators=[DataRequired(message="Please enter an event title")]
    )
    category = SelectField(
        "Category",
        choices=[
            ("", "Select Category"),
            ("music", "Music"),
            ("gaming", "Gaming"),
            ("arts", "Arts"),
            ("sports", "Sports"),
            ("education", "Education"),
            ("business", "Business"),
            ("other", "Other"),
        ],
        validators=[DataRequired(message="Please select an event category")],
    )
    date = DateTimeField(
        "Date and Time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    location = StringField("Location", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])

    event_type = RadioField(
        "Event Type",
        choices=[("free", "Free Event"), ("paid", "Paid Event")],
        default="free",
        validators=[DataRequired()],
    )

    free_ticket_quantity = IntegerField(
        "Number of Available Tickets",
        validators=[Optional(), NumberRange(min=1)],
        default=100,
    )

    currency = SelectField(
        "Currency",
        choices=[
            ("", "Select Currency"),
            ("KES", "KES - Kenyan Shilling"),
            ("USD", "USD - US Dollar"),
            ("EUR", "EUR - Euro"),
            ("GBP", "GBP - British Pound"),
        ],
        validators=[Optional()],
    )

    ticket_types = FieldList(FormField(TicketTypeForm), min_entries=0)

    images = MultipleFileField(
        "Event Images",
        validators=[
            DataRequired(message="At least one image is required"),
            FileAllowed(
                ["jpg", "jpeg", "png"], "Only JPEG and PNG images are allowed!"
            ),
        ],
    )

    def validate_ticket_types(self, field):
        if self.event_type.data == "paid":
            if not field.data:
                raise ValidationError(
                    "At least one ticket type is required for paid events"
                )

            for ticket in field.data:
                if not ticket.get("ticket_type"):
                    raise ValidationError("Ticket type is required")
                if ticket.get("ticket_type") == "custom" and not ticket.get(
                    "custom_type"
                ):
                    raise ValidationError("Custom ticket type name is required")
                if not ticket.get("quantity") or int(ticket.get("quantity", 0)) < 1:
                    raise ValidationError("Quantity must be at least 1")
                if not ticket.get("price") or float(ticket.get("price", 0)) < 0:
                    raise ValidationError("Price must be 0 or greater")

    def validate_currency(self, field):
        if self.event_type.data == "paid" and not field.data:
            raise ValidationError("Currency is required for paid events")

    def validate_free_ticket_quantity(self, field):
        if self.event_type.data == "free":
            if not field.data or field.data < 1:
                raise ValidationError("Number of available tickets must be at least 1 for free events")

    def validate_images(self, field):
        if not field.data or not any(f.filename for f in field.data):
            raise ValidationError("At least one image is required")

        for file in field.data:
            if file and file.filename:
                file.seek(0)
                # Check file size (e.g., max 5MB)
                if len(file.read()) > 5 * 1024 * 1024:  # 5MB in bytes
                    raise ValidationError("Image file size must be less than 5MB")
                file.seek(0)

    def validate(self):
        print("Starting form validation...")
        if not super().validate():
            return False

        # For free events, currency and ticket types are not required
        if self.event_type.data == "free":
            self.currency.data = None  # Clear currency for free events
            if not self.free_ticket_quantity.data or self.free_ticket_quantity.data < 1:
                self.free_ticket_quantity.errors = ["Number of available tickets must be at least 1 for free events"]
                return False
            return True

        # For paid events, validate currency and ticket types
        if self.event_type.data == "paid":
            if not self.currency.data:
                self.currency.errors = ["Currency is required for paid events"]
                return False

            # Validate ticket types
            ticket_types_data = []
            i = 0
            while True:
                prefix = f"ticket_types-{i}-"
                ticket_type = request.form.get(f"{prefix}ticket_type")
                if not ticket_type:
                    break

                ticket_types_data.append(
                    {
                        "ticket_type": ticket_type,
                        "custom_type": request.form.get(f"{prefix}custom_type"),
                        "quantity": request.form.get(f"{prefix}quantity"),
                        "price": request.form.get(f"{prefix}price"),
                        "description": request.form.get(f"{prefix}description"),
                    }
                )
                i += 1

            if not ticket_types_data:
                self.errors["ticket_types"] = [
                    "At least one ticket type is required for paid events"
                ]
                return False

            # Validate each ticket type
            for i, ticket in enumerate(ticket_types_data):
                print(f"Validating ticket type {i}:", ticket)

                if not ticket["ticket_type"]:
                    self.errors[f"ticket_types-{i}"] = ["Ticket type is required"]
                    return False

                if ticket["ticket_type"] == "custom" and not ticket["custom_type"]:
                    self.errors[f"ticket_types-{i}"] = ["Custom type name is required"]
                    return False

                try:
                    quantity = int(ticket["quantity"])
                    if quantity < 1:
                        self.errors[f"ticket_types-{i}"] = [
                            "Quantity must be at least 1"
                        ]
                        return False
                except (ValueError, TypeError):
                    self.errors[f"ticket_types-{i}"] = ["Invalid quantity"]
                    return False

                try:
                    price = float(ticket["price"])
                    if price < 0:
                        self.errors[f"ticket_types-{i}"] = [
                            "Price must be 0 or greater"
                        ]
                        return False
                except (ValueError, TypeError):
                    self.errors[f"ticket_types-{i}"] = ["Invalid price"]
                    return False

            # Store validated ticket types data
            self.ticket_types_data = ticket_types_data

        print("Form validation successful")
        return True
