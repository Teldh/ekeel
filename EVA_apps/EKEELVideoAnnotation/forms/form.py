"""
Flask form definitions for user management and video processing.

This module provides WTForms form classes for handling various user interactions
including authentication, video submission, and analysis configuration.
"""

from flask_wtf import FlaskForm
from wtforms import Form, BooleanField, TextField, SubmitField, StringField, PasswordField, RadioField, SelectMultipleField, widgets, SelectField
from wtforms.validators import InputRequired, Email, EqualTo, ValidationError, Length
from forms.mail import send_confirmation_mail_with_link
import bcrypt
import database.mongo as mongo


class addVideoForm(FlaskForm):
    """
    Form for adding new video for annotation.

    Attributes
    ----------
    url : TextField
        Video URL input field
    annotator : wtforms.fields.StringField
        Annotator name input field with a required validator.
    submit : SubmitField
        Form submission button
    """
    url = TextField('Url', validators=[InputRequired()])
    annotator = TextField('Annotator', validators=[InputRequired()])
    submit = SubmitField('Start annotate')


class BurstForm(FlaskForm):
    """
    Form for burst video processing configuration.

    Attributes
    ----------
    url : TextField
        Video URL input field
    type : RadioField
        Processing type selection (semi-automatic or automatic)
    """
    url = TextField('Url', validators=[InputRequired()])
    type = RadioField('video', choices=[("semi","semi-automatic"), ("auto","automatic")])


class ForgotForm(FlaskForm):
    """
    Password recovery request form.

    Attributes
    ----------
    email : StringField
        User email input field
    submit : SubmitField
        Form submission button
    """
    email = StringField('Email', validators=[InputRequired(), Email('Email not correct')])
    submit = SubmitField('Send mail')


class PasswordResetForm(FlaskForm):
    """
    Password reset form.

    Attributes
    ----------
    password : PasswordField
        New password input field
    password2 : PasswordField
        Password confirmation field
    submit : SubmitField
        Form submission button
    """
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password', message = "Passwords must match")])
    submit = SubmitField('Reset password')


class ConfirmCodeForm(FlaskForm):
    """
    Email confirmation code form.

    Attributes
    ----------
    code : StringField
        Confirmation code input field
    submit : SubmitField
        Form submission button
    """
    code = StringField("Insert the code received by email", validators=[InputRequired()])
    submit = SubmitField('Reset password')

class RegisterForm(FlaskForm):
    """
    User registration form.

    Attributes
    ----------
    name : StringField
        First name input field
    surname : StringField
        Last name input field
    email : StringField
        Email input field
    password : PasswordField
        Password input field
    password2 : PasswordField
        Password confirmation field
    submit : SubmitField
        Form submission button

    Methods
    -------
    validate_email(email)
        Validate email uniqueness in database
    """
    name = StringField('First name', validators=[InputRequired()])
    surname = StringField('Last name', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired(), Email('Email not correct')])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password', message = "Passwords must match")])
    submit = SubmitField('Register')

    def validate_email(self, email):
        """
        Check if email is already registered.

        Parameters
        ----------
        email : StringField
            Email field to validate

        Raises
        ------
        ValidationError
            If email exists in verified or unverified users
        """
        if mongo.unverified_users.find_one({"email":email.data}):
            raise ValidationError('There is an unverified account already registered under this email')
        elif mongo.users.find_one({"email":email.data}):
            raise ValidationError('There is already an account registered under this email')


class LoginForm(FlaskForm):
    """
    User login form.

    Attributes
    ----------
    email : StringField
        Email input field
    password : PasswordField
        Password input field
    remember_me : BooleanField
        Remember login option
    submit : SubmitField
        Form submission button

    Methods
    -------
    validate()
        Validate login credentials
    """
    email = StringField('Email', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    remember_me = BooleanField('Remember Me')

    submit = SubmitField('Login')

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)

    def validate(self):
        """
        Validate login credentials against database.

        Returns
        -------
        bool
            True if credentials are valid, False otherwise
        """
        initial_validation = super(LoginForm, self).validate()
        if not initial_validation:
            return False

        user = mongo.db.students.find_one({"email": self.email.data})

        if user:
            password = user["password_hash"]
            if bcrypt.checkpw(self.password.data.encode('utf-8'), password.encode('utf-8')):
                return True
            else:
                self.email.errors.append("Email or password incorrect")

        elif mongo.unverified_users.find_one({"email": self.email.data}):

            send_confirmation_mail_with_link(self.email.data)
            self.email.errors.append("An email has been sent to your address in order to verify it")
            return False

        else:
            self.email.errors.append("Email or password incorrect")

        return False


class analysisForm(FlaskForm):
    """
    Analysis configuration form.

    Attributes
    ----------
    video : RadioField
        Video selection field
    annotator : RadioField
        Annotator selection field
    """
    video = RadioField('video', choices = [])
    annotator = RadioField('annotators', choices = [])


class MultiCheckboxField(SelectMultipleField):
    """
    Custom multiple checkbox field.

    Attributes
    ----------
    widget : ListWidget
        List widget for checkboxes
    option_widget : CheckboxInput
        Individual checkbox widget
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class NonValidatingSelectField(SelectField):
    """
    Select field without validation.

    Methods
    -------
    pre_validate(form)
        Skip field validation
    """
    def pre_validate(self, form):
        pass

class GoldStandardForm(FlaskForm):
    """
    Gold standard creation form.

    Attributes
    ----------
    video : RadioField
        Video selection field
    annotators : MultiCheckboxField
        Multiple annotator selection
    agreements : NonValidatingSelectField
        Combination criteria selection
    name : StringField
        Gold standard name field
    submit : SubmitField
        Form submission button
    """
    video = RadioField('Video', choices = [])
    annotators = MultiCheckboxField('Annotators', choices=[], validators=[InputRequired()])
    agreements = NonValidatingSelectField('Combination criteria', choices = [])
    name = StringField("Gold Name", validators=[InputRequired()])
    submit = SubmitField('Launch Creation')

