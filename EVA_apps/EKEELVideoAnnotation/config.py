"""
Flask Application Configuration
=============================

Configures Flask application with reverse proxy support and authentication settings.


Attributes
----------
app : Flask
    Main Flask application instance
login : LoginManager
    Flask-Login manager instance

Warning
-----
Should not be moved or links to the htmls may break

"""

from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from env import APP_SECRET_KEY, APP_SECURITY_PASSWORD_SALT


class ReverseProxied:
    """
    WSGI middleware for handling reverse proxy headers and URL rewriting.

    This class modifies the WSGI environment to support running the application
    behind a reverse proxy, handling script names, URL schemes, and server names.

    Attributes
    ----------
    app : flask.Flask
        The Flask application instance to wrap
    script_name : str or None
        Optional URL prefix for the application
    scheme : str or None
        Optional URL scheme (http/https)
    server : str or None
        Optional server name

    Methods
    -------
    __call__(environ, start_response)
        Process the WSGI environment and handle reverse proxy headers
    """

    def __init__(self, app, script_name=None, scheme=None, server=None):
        """
        Initialize the reverse proxy middleware.

        Parameters
        ----------
        app : flask.Flask
            Flask application instance
        script_name : str, optional
            URL prefix for the application
        scheme : str, optional
            URL scheme (http/https)
        server : str, optional
            Server name
        """
        self.app = app
        self.script_name = script_name
        self.scheme = scheme
        self.server = server

    def __call__(self, environ, start_response):
        """
        Process WSGI environment for reverse proxy support.

        Parameters
        ----------
        environ : dict
            WSGI environment dictionary
        start_response : callable
            WSGI start_response callable

        Returns
        -------
        callable
            Result of calling the wrapped WSGI application
        """
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '') or self.script_name
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        scheme = environ.get('HTTP_X_SCHEME', '') or self.scheme
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        server = environ.get('HTTP_X_FORWARDED_SERVER', '') or self.server
        if server:
            environ['HTTP_HOST'] = server
        return self.app(environ, start_response)

# Flask app configuration
app = Flask(__name__)
app.wsgi_app = ReverseProxied(app.wsgi_app, script_name='/annotator')
Bootstrap(app)
app.config['SECRET_KEY'] = APP_SECRET_KEY
app.config['SECURITY_PASSWORD_SALT'] = APP_SECURITY_PASSWORD_SALT
app.config['APPLICATION_ROOT'] = '/annotator'
login = LoginManager(app)
login.login_view = 'login'