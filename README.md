# Life Tracker

A modular personal tracking app built with Flask + SQLAlchemy to learn Python, SQL, and backend development.

## Modules
- [x] Auth (register/login/logout)
- [x] Finance Tracker (starter module — CRUD + dashboard aggregation)
- [ ] Academic Tracker
- [ ] Health Tracker
- [ ] Habit Tracker
- [ ] Coding & Productivity Tracker
- [ ] Calendar Integration
- [ ] Weekly Journal

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize the database (run once)
flask --app run.py db init
flask --app run.py db migrate -m "Initial migration"
flask --app run.py db upgrade

# 4. Run the app
python run.py
```

Then visit http://127.0.0.1:5000

## Project structure

```
life_tracker/
├── app/
│   ├── __init__.py       # App factory — registers extensions & blueprints
│   ├── models/            # One file per domain (user.py, finance.py, ...)
│   ├── routes/             # Blueprints (auth.py, main.py, finance.py, ...)
│   ├── templates/
│   └── static/
├── migrations/             # Created by `flask db init`
├── config.py
├── run.py
└── requirements.txt
```

## Adding a new tracker module (e.g. Habit Tracker)

1. Create `app/models/habit.py` with your model(s), importing `db` from `app`.
2. Import the new model in `app/__init__.py` so Flask-Migrate can detect it.
3. Create `app/routes/habit.py` as a blueprint (`habit_bp = Blueprint("habit", __name__, url_prefix="/habit")`), register it in `app/__init__.py`.
4. Add templates under `app/templates/habit/`.
5. Run `flask --app run.py db migrate -m "add habit tracker"` then `db upgrade`.
6. Add a summary card for it on `dashboard.html`.

This is the same pattern the Finance module follows — copy it as a template for each new tracker.
