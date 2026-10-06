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

def _calculate_points_redemption(cust, requested_points, merchandise_total):
    """Use the current 30-point minimum while preserving the existing safeguards."""
    points = round(_app.parse_float(requested_points, 0.0), 2)
    balance = round(max(0.0, _app.parse_float(cust.points_balance, 0.0)), 2)
    total = round(max(0.0, _app.parse_float(merchandise_total, 0.0)), 2)

    if points <= 0:
        return 0.0, 0.0
    if points < _app.MIN_REDEMPTION_POINTS:
        raise _app.OrderValidationError(
            f'Minimum redemption is {_app.MIN_REDEMPTION_POINTS:g} points.'
        )
    if not _app.customer_has_early_redemption_qualifying_purchase(cust):
        raise _app.OrderValidationError(
            'Before claiming a 30-point discount, members below ₱600 lifetime purchases '
            'must first complete one verified purchase worth at least ₱100.'
        )
    if points > balance + 1e-9:
        raise _app.OrderValidationError(f'Only {balance:,.2f} points are available.')

    point_value = _app.POINT_VALUE_PHP
    max_points = round(total / point_value, 2)
    if points > max_points + 1e-9:
        raise _app.OrderValidationError(
            f'Only {max_points:,.2f} points can be used on this purchase.'
        )
    return points, round(points * point_value, 2)

# Replace only the redemption function reference used by the existing routes.
_app.calculate_points_redemption = _calculate_points_redemption

# Keep the existing Flask app object as the WSGI application.
app = _app.app
application = app
