import os

from unified_admin import create_app


app = create_app()


if __name__ == "__main__":
    app.run(host=os.getenv("FLASK_RUN_HOST", "127.0.0.1"), port=int(os.getenv("FLASK_RUN_PORT", "5000")))
