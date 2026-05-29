# Cloud-Based Student Attendance Management System

A beginner-friendly Flask mini-project to manage student attendance with separate login areas for admin, teacher, and student users. The system uses SQLite for storage, Bootstrap 5 for the interface, and session-based authentication with role-based access control.

## Features

- Admin login, teacher login, and student login
- Admin can add students, teachers, and classes
- Teacher can mark attendance by class and date
- Duplicate attendance for the same class and date is replaced automatically
- Admin and teacher can view attendance with filters
- Student can view personal attendance history and percentage
- Demo data is seeded automatically on first run
- Ready to run locally with `python app.py`
- Ready to deploy on Render with `gunicorn`

## Tech Stack

- Python 3.10+
- Flask
- Flask-SQLAlchemy
- SQLite
- HTML, CSS, JavaScript
- Bootstrap 5
- Jinja2
- Werkzeug password hashing
- gunicorn

## Demo Credentials

Admin:
- Username: `admin`
- Password: `admin123`

Teacher:
- Username: `teacher1`
- Password: `teacher123`

Students:
- Username: `student1`
- Password: `student123`
- Username: `student2`
- Password: `student123`
- Username: `student3`
- Password: `student123`

## Local Setup

1. Create a virtual environment.
2. Activate it.
3. Install dependencies.
4. Run the app.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Render Deployment

1. Push the project to GitHub.
2. Create a new Render Web Service.
3. Connect the repository.
4. Render will use `render.yaml`.
5. Start command: `gunicorn app:app`

## Database Notes

- SQLite database file: `instance/attendance.db`
- Database tables are created automatically
- Demo data is added automatically if the database is empty
- SQLite is ideal for local demo and mini-project submission
