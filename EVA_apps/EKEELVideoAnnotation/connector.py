"""
EKEEL Video Annotation Connector
===============================

This module serves as the entry point for gunicorn server deployment.
It configures system paths for gunicorn.


"""

from main import app
import sys

def _configure_paths():
    sys.path.insert(0, "/var/www/ekeel/")
    print(sys.version)
    print(sys.path)

_configure_paths()

if __name__ == "__main__":
    app.run()