import logging
import os
import secrets

from flask import Flask, g
from werkzeug.security import generate_password_hash

from .auth import auth_bp
from .auth_helpers import load_current_user
from .config import CONFIG_MAP
from .dashboard import dashboard_bp
from .extensions import db
from .insurance_module import insurance_bp
from .models import User
from .reports_module import reports_bp
from .vip import vip_bp

logger = logging.getLogger(__name__)


def create_app(environment=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    env = environment or os.getenv("APP_ENV", "development")
    config_class = CONFIG_MAP.get(env, CONFIG_MAP["development"])
    app.config.from_object(config_class)
    if hasattr(config_class, "validate"):
        config_class.validate()

    db.init_app(app)

    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            password = os.getenv("INITIAL_ADMIN_PASSWORD")
            if not password:
                password = secrets.token_urlsafe(16)
                logger.warning(
                    "No INITIAL_ADMIN_PASSWORD environment variable set. "
                    "Generated bootstrap admin password: %s — change it immediately.",
                    password,
                )
            db.session.add(
                User(
                    username="admin",
                    password_hash=generate_password_hash(password),
                    role="admin",
                )
            )
            db.session.commit()

    @app.before_request
    def _load_user_context():
        load_current_user()

    @app.context_processor
    def _inject_globals():
        return {"current_user": g.get("current_user")}

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(insurance_bp)
    app.register_blueprint(vip_bp)
    app.register_blueprint(reports_bp)

    return app
