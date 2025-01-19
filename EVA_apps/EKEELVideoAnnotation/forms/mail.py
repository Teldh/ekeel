"""
Email handling module for user communications.

This module provides functionality for sending emails, managing SMTP connections,
and handling email verification tokens.

Classes
-------
MailSender
    Email sending class with SMTP connection management

Functions
---------
send_mail
    Send email with HTML content
generate_confirmation_token
    Generate email verification token
confirm_token
    Verify email confirmation token
send_confirmation_mail_with_link
    Send verification email with confirmation link
send_confirmation_mail
    Send verification email with confirmation code
"""

import smtplib
from flask import render_template, url_for

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from itsdangerous import URLSafeTimedSerializer

from config import app
from env import EMAIL_ACCOUNT, EMAIL_PASSWORD

class MailSender:
    """
    Email sender with SMTP server connection management.

    Attributes
    ----------
    username : str
        SMTP server login username
    password : str
        SMTP server login password
    server_name : str
        SMTP server hostname
    server_port : int
        SMTP server port
    use_SSL : bool
        Whether to use SSL connection
    smtpserver : smtplib.SMTP
        SMTP server connection
    connected : bool
        Connection status
    recipients : list
        List of recipient email addresses
    html_ready : bool
        Whether HTML content is enabled
    msg : MIMEMultipart
        Email message content

    Warning
    -------
    SMTP servers use different ports for SSL and TLS.
    
    Methods
    -------
    set_message(plaintext, subject, from, htmltext)
        Set email content and metadata
    clear_message()
        Clear email content
    connect()
        Connect to SMTP server
    send_all(close_connection)
        Send email to all recipients
    """
    def __init__(self, in_username, in_password, in_server=("smtp.gmail.com", 587), use_SSL=False):
        """
        Initialize mail sender with server configuration.

        Parameters
        ----------
        in_username : str
            SMTP server username
        in_password : str
            SMTP server password
        in_server : tuple, optional
            (hostname, port) for SMTP server
        use_SSL : bool, optional
            Whether to use SSL instead of TLS
        """
        self.username = in_username
        self.password = in_password
        self.server_name = in_server[0]
        self.server_port = in_server[1]
        self.use_SSL = use_SSL

        if self.use_SSL:
            self.smtpserver = smtplib.SMTP_SSL(self.server_name, self.server_port)
        else:
            self.smtpserver = smtplib.SMTP(self.server_name, self.server_port)
        self.connected = False
        self.recipients = []

    def __str__(self):
        return "Type: Mail Sender \n" \
               "Connection to server {}, port {} \n" \
               "Connected: {} \n" \
               "Username: {}, Password: {}".format(self.server_name, self.server_port, self.connected, self.username, self.password)

    def set_message(self, in_plaintext, in_subject="", in_from=None, in_htmltext=None):
        """
        Create MIME message with optional HTML content.

        Parameters
        ----------
        in_plaintext : str
            Plain text email body
        in_subject : str, optional
            Email subject line
        in_from : str, optional
            Sender email address
        in_htmltext : str, optional
            HTML version of email body
        """

        if in_htmltext is not None:
            self.html_ready = True
        else:
            self.html_ready = False

        if self.html_ready:
            self.msg = MIMEMultipart('alternative')  # 'alternative' allows attaching an html version of the message later
            self.msg.attach(MIMEText(in_plaintext, 'plain'))
            self.msg.attach(MIMEText(in_htmltext, 'html'))
        else:
            self.msg = MIMEText(in_plaintext, 'plain')

        self.msg['Subject'] = in_subject
        if in_from is None:
            self.msg['From'] = self.username
        else:
            self.msg['From'] = in_from
        self.msg["To"] = None
        self.msg["CC"] = None
        self.msg["BCC"] = None

    def clear_message(self):
        """
        Remove all email body content.

        Clears both plain text and HTML content if present.
        """
        self.msg.set_payload("")

    def set_subject(self, in_subject):
        """
        Set email subject line.

        Parameters
        ----------
        in_subject : str
            New subject line
        """
        self.msg.replace_header("Subject", in_subject)

    def set_from(self, in_from):
        """
        Set sender email address.

        Parameters
        ----------
        in_from : str
            Sender email address
        """
        self.msg.replace_header("From", in_from)

    def set_plaintext(self, in_body_text):
        """
        Set plain text email body.

        Parameters
        ----------
        in_body_text : str
            Plain text content

        Warning
        -------
        Replaces entire payload if no HTML content exists
        """
        if not self.html_ready:
            self.msg.set_payload(in_body_text)
        else:
            payload = self.msg.get_payload()
            payload[0] = MIMEText(in_body_text)
            self.msg.set_payload(payload)

    def set_html(self, in_html):
        """
        Set HTML email body.

        Parameters
        ----------
        in_html : str
            HTML content

        Raises
        ------
        TypeError
            If HTML wasn't enabled in set_message()
        """
        try:
            payload = self.msg.get_payload()
            payload[1] = MIMEText(in_html, 'html')
            self.msg.set_payload(payload)
        except TypeError:
            print("ERROR: "
                  "Payload is not a list. Specify an HTML message with in_htmltext in MailSender.set_message()")
            raise

    def set_recipients(self, in_recipients):
        """
        Set list of recipient email addresses.

        Parameters
        ----------
        in_recipients : list
            List of recipient email addresses

        Raises
        ------
        TypeError
            If input is not a list or tuple
        """
        if not isinstance(in_recipients, (list, tuple)):
            raise TypeError("Recipients must be a list or tuple, is {}".format(type(in_recipients)))

        self.recipients = in_recipients

    def add_recipient(self, in_recipient):
        """
        Add single recipient to list.

        Parameters
        ----------
        in_recipient : str
            Recipient email address
        """
        self.recipients.append(in_recipient)

    def connect(self):
        """
        Connect to SMTP server.

        Establishes connection using configured credentials.
        Must be called before sending messages.
        """
        if not self.use_SSL:
            self.smtpserver.starttls()
        self.smtpserver.login(self.username, self.password)
        self.connected = True
        print("Connected to {}".format(self.server_name))

    def disconnect(self):
        """
        Close SMTP server connection.
        """
        self.smtpserver.close()
        self.connected = False

    def send_all(self, close_connection=True):
        """
        Send message to all recipients.

        Parameters
        ----------
        close_connection : bool, optional
            Whether to close connection after sending

        Raises
        ------
        ConnectionError
            If not connected to SMTP server
        """
        if not self.connected:
            raise ConnectionError("Not connected to any server. Try self.connect() first")

        print("Message: {}".format(self.msg.get_payload()))

        for recipient in self.recipients:
                self.msg.replace_header("To", recipient)
                print("Sending to {}".format(recipient))
                self.smtpserver.send_message(self.msg)

        print("All messages sent")

        if close_connection:
            self.disconnect()
            print("Connection closed")


def send_mail(To, subject, html):
    """
    Send email with HTML content.

    Parameters
    ----------
    To : str
        Recipient email address
    subject : str
        Email subject line
    html : str
        HTML email content
    """
    ourmailsender = MailSender(EMAIL_ACCOUNT, EMAIL_PASSWORD, ('smtp.gmail.com', 587))
    
    ourmailsender.set_message("edurell", subject, "EKEEL Annotations", html)

    ourmailsender.set_recipients([To])

    ourmailsender.connect()
    ourmailsender.send_all()


def generate_confirmation_token(email):
    """
    Generate secure token for email confirmation.

    Parameters
    ----------
    email : str
        Email address to encode in token

    Returns
    -------
    str
        Secure URL-safe token
    """
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, app.config['SECURITY_PASSWORD_SALT'])


def confirm_token(token, expiration=5600):
    """
    Verify email confirmation token.

    Parameters
    ----------
    token : str
        Token to verify
    expiration : int, optional
        Token expiration time in seconds

    Returns
    -------
    str or bool
        Email address if valid, False if invalid
    """
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email


def send_confirmation_mail_with_link(email):
    """
    Send verification email containing confirmation link.

    Parameters
    ----------
    email : str
        Recipient email address
    """
    token = generate_confirmation_token(email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = render_template('user/user_activate_mail_with_link.html', confirm_url=confirm_url)
    subject = "Please confirm your email"

    send_mail(email, subject, html)


def send_confirmation_mail(email, code):
    """
    Send verification email containing confirmation code.

    Parameters
    ----------
    email : str
        Recipient email address
    code : str
        Verification code
    """
    html = render_template('user/user_activate_mail.html', code=code)
    subject = "Please confirm your email"

    send_mail(email, subject, html)

if __name__ == "__main__":
    # plaintext = "Welcome to edurell, \n" \
    #             "Prova.\n"
    #
    # html = "<h1> Ciao! </h1>"
    #
    # ourmailsender = MailSender('educationalRelationsLearning@gmail.com', 'qyzlabajrvwxlbfs', ('smtp.gmail.com', 587))
    # ourmailsender.set_message(plaintext, "This is a test", "EKEEL Annotations", html)
    #
    print(token)
