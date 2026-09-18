from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import models so Flask-Migrate can detect them
    from app.models.user import User  # noqa: F401
    from app.models import finance  # noqa: F401
    from app.models import academic  # noqa: F401
    from app.models import habit  # noqa: F401
    from app.models import health  # noqa: F401

    # Ensure upload directory exists for medical reports
    if app.config.get("UPLOAD_FOLDER"):
        import os
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.finance import finance_bp
    from app.routes.academic import academic_bp
    from app.routes.habit import habit_bp
    from app.routes.health import health_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(academic_bp)
    app.register_blueprint(habit_bp)
    app.register_blueprint(health_bp)

    # Register CLI commands
    @app.cli.command("seed-categories")
    def seed_categories():
        """Seed the database with default transaction categories."""
        from app.models.finance import Category
        
        default_categories = [
            {"name": "Food", "type": "expense"},
            {"name": "Rent", "type": "expense"},
            {"name": "Utilities", "type": "expense"},
            {"name": "Entertainment", "type": "expense"},
            {"name": "Transport", "type": "expense"},
            {"name": "Academics", "type": "expense"},
            {"name": "Health & Fitness", "type": "expense"},
            {"name": "Shopping", "type": "expense"},
            {"name": "Miscellaneous", "type": "expense"},
            {"name": "Salary", "type": "income"},
            {"name": "Freelance", "type": "income"},
            {"name": "Pocket Money", "type": "income"},
            {"name": "Investments", "type": "income"},
            {"name": "Gifts", "type": "income"},
        ]
        
        seeded = 0
        for cat_data in default_categories:
            existing = Category.query.filter_by(name=cat_data["name"]).first()
            if not existing:
                cat = Category(name=cat_data["name"], type=cat_data["type"])
                db.session.add(cat)
                seeded += 1
        
        if seeded > 0:
            db.session.commit()
            print(f"Successfully seeded {seeded} categories.")
        else:
            print("All default categories already exist.")

    return app

