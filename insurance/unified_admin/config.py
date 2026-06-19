import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'unified_admin.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False

    @staticmethod
    def validate():
        if os.getenv("SECRET_KEY") in (None, "", "dev-secret-change-me"):
            raise RuntimeError("SECRET_KEY must be set in production")


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
