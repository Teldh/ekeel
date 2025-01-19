"""
User management module for Flask-Login integration.

This module provides user authentication and management functionality
by extending Flask-Login's UserMixin class.
"""

from flask_login import UserMixin
from config import login
from database.mongo import users


class User(UserMixin):
    """
    User class for authentication and session management.

    This class extends Flask-Login's UserMixin to provide user 
    authentication functionality with MongoDB backend storage.

    Attributes
    ----------
    email : str
        User's email address (unique identifier)
    name : str
        User's first name
    surname : str
        User's last name
    complete_name : str
        User's full name (first + last)
    mongodb_id : str
        MongoDB document ID for the user

    Methods
    -------
    get_id()
        Get user identifier for Flask-Login
    load_user(email)
        Load user from database by email
    """

    def __init__(self, email):
        """
        Initialize user from database.

        Parameters
        ----------
        email : str
            User's email address
        """
        self.email = email
        u = users.find_one({"email": email})

        self.name = u["name"]
        self.surname = u["surname"]
        self.complete_name = u["name"] + " " + u["surname"]
        self.mongodb_id = str(u["_id"])

    def get_id(self):
        """
        Get user identifier for Flask-Login.

        Returns
        -------
        str
            User's email address
        """
        return self.email

    @login.user_loader
    def load_user(email):
        """
        Load user from database by email.

        Used by Flask-Login to reload the user object from the user ID 
        stored in the session.

        Parameters
        ----------
        email : str
            User's email address

        Returns
        -------
        User or None
            User object if found, None otherwise
        """
        u = users.find_one({"email": email})
        if not u:
            return None
        return User(email=u['email'])