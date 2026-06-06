from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard.index"))
        flash("Invalid username or password", "error")
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/bootstrap-admin", methods=["POST"])
def bootstrap_admin():
    if not current_app.config.get("ALLOW_BOOTSTRAP_ADMIN", False):
        return {"error": "bootstrap admin is disabled"}, 403
    if User.query.count() > 0:
        return {"error": "Users already exist"}, 409

    username = request.json.get("username", "admin") if request.is_json else "admin"
    password = request.json.get("password", "admin123") if request.is_json else "admin123"
    user = User(username=username, password_hash=generate_password_hash(password), role="admin")
    db.session.add(user)
    db.session.commit()
    return {"message": "Admin created"}, 201
