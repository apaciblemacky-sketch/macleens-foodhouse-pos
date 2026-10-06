"""Runtime overrides for the production app's loyalty rules.

This module imports the existing Flask application unchanged, then applies the
current business rules before Gunicorn starts serving requests. It does not
alter customer/order data.
"""
import app as _app

# Current Macleen's loyalty rules:
# - ₱60 eligible spend = 1 base point
# - minimum 30 points per redemption transaction
# Existing earned balances are preserved.
_app.MIN_REDEMPTION_POINTS = 30.0

# Keep the existing Flask app object as the WSGI application.
app = _app.app
application = app
