from unittest.mock import patch

def logged_in_as(user):
    """Mocks that the given user is logged in."""
    return patch('flask_login.utils._get_user', return_value=user)
