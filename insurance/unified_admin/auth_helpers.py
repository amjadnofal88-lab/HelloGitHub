from functools import wraps

from flask import abort, g, redirect, session, url_for

from .models import User


def load_current_user():
    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return
    g.current_user = User.query.get(user_id)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not g.get("current_user"):
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = g.get("current_user")
            if not user:
                return redirect(url_for("auth.login"))
            if user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
