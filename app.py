import os
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DATABASE_PATH = os.path.join(INSTANCE_DIR, "attendance.db")

os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__, instance_path=INSTANCE_DIR)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "student-attendance-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)

    teacher_profile = db.relationship("Teacher", back_populates="user", uselist=False)
    student_profile = db.relationship("Student", back_populates="user", uselist=False)
    marked_attendance = db.relationship("Attendance", back_populates="marker")


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    employee_code = db.Column(db.String(30), unique=True, nullable=False)

    user = db.relationship("User", back_populates="teacher_profile")


class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(20), nullable=False)

    students = db.relationship("Student", back_populates="classroom", cascade="all, delete")
    attendance_records = db.relationship(
        "Attendance", back_populates="classroom", cascade="all, delete"
    )


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    roll_number = db.Column(db.String(30), unique=True, nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classroom.id"), nullable=False)

    user = db.relationship("User", back_populates="student_profile")
    classroom = db.relationship("Classroom", back_populates="students")
    attendance_records = db.relationship(
        "Attendance", back_populates="student", cascade="all, delete"
    )


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classroom.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    marked_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "classroom_id", "date", name="unique_daily_attendance"),
    )

    student = db.relationship("Student", back_populates="attendance_records")
    classroom = db.relationship("Classroom", back_populates="attendance_records")
    marker = db.relationship("User", back_populates="marked_attendance")


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard"))
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def parse_attendance_date(date_value):
    if not date_value:
        return None
    try:
        return datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        return None


def create_user(username, password, role, full_name):
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role,
        full_name=full_name,
    )
    db.session.add(user)
    db.session.flush()
    return user


def seed_demo_data():
    if User.query.first():
        return

    class_a = Classroom(name="BCA", section="A")
    class_b = Classroom(name="BSc IT", section="B")
    db.session.add_all([class_a, class_b])
    db.session.flush()

    admin_user = create_user("admin", "admin123", "admin", "System Admin")
    teacher_user = create_user("teacher1", "teacher123", "teacher", "Amit Sharma")
    db.session.add(Teacher(user_id=teacher_user.id, employee_code="EMP1001"))

    student_users = [
        ("student1", "student123", "Pranjal Shukla", "ROLL001", class_a.id),
        ("student2", "student123", "Rahul Verma", "ROLL002", class_a.id),
        ("student3", "student123", "Sneha Singh", "ROLL003", class_b.id),
    ]

    for username, password, full_name, roll_number, classroom_id in student_users:
        user = create_user(username, password, "student", full_name)
        db.session.add(
            Student(user_id=user.id, roll_number=roll_number, classroom_id=classroom_id)
        )

    db.session.flush()

    students = Student.query.order_by(Student.id).all()
    sample_date = date.today()
    for student in students:
        db.session.add(
            Attendance(
                student_id=student.id,
                classroom_id=student.classroom_id,
                date=sample_date,
                status="Present" if student.roll_number != "ROLL002" else "Absent",
                marked_by=admin_user.id,
            )
        )

    db.session.commit()


def initialize_database():
    db.create_all()
    seed_demo_data()


@app.context_processor
def inject_template_data():
    return {"today_date": date.today().isoformat()}


def get_student_dashboard_data(user_id):
    student = Student.query.filter_by(user_id=user_id).first()
    records = (
        Attendance.query.filter_by(student_id=student.id)
        .order_by(Attendance.date.desc())
        .all()
    )
    present_count = sum(1 for item in records if item.status == "Present")
    absent_count = sum(1 for item in records if item.status == "Absent")
    total_count = len(records)
    percentage = round((present_count / total_count) * 100, 2) if total_count else 0
    return {
        "student": student,
        "attendance_records": records,
        "present_count": present_count,
        "absent_count": absent_count,
        "total_count": total_count,
        "percentage": percentage,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["full_name"] = user.full_name
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")

    if role == "admin":
        stats = {
            "students": Student.query.count(),
            "teachers": Teacher.query.count(),
            "classes": Classroom.query.count(),
            "attendance_records": Attendance.query.count(),
        }
        classrooms = Classroom.query.order_by(Classroom.name, Classroom.section).all()
        return render_template("admin_dashboard.html", stats=stats, classrooms=classrooms)

    if role == "teacher":
        classrooms = Classroom.query.order_by(Classroom.name, Classroom.section).all()
        recent_attendance = (
            Attendance.query.order_by(Attendance.date.desc(), Attendance.id.desc())
            .limit(10)
            .all()
        )
        return render_template(
            "teacher_dashboard.html",
            classrooms=classrooms,
            recent_attendance=recent_attendance,
        )

    if role == "student":
        return render_template(
            "student_dashboard.html", **get_student_dashboard_data(session["user_id"])
        )

    flash("Invalid user role.", "danger")
    return redirect(url_for("logout"))


@app.route("/admin/add-student", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_student():
    classrooms = Classroom.query.order_by(Classroom.name, Classroom.section).all()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        roll_number = request.form.get("roll_number", "").strip()
        classroom_id = request.form.get("classroom_id", type=int)

        if not all([full_name, username, password, roll_number, classroom_id]):
            flash("All fields are required.", "danger")
            return render_template("add_student.html", classrooms=classrooms)

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template("add_student.html", classrooms=classrooms)

        if Student.query.filter_by(roll_number=roll_number).first():
            flash("Roll number already exists.", "danger")
            return render_template("add_student.html", classrooms=classrooms)

        user = create_user(username, password, "student", full_name)
        db.session.add(Student(user_id=user.id, roll_number=roll_number, classroom_id=classroom_id))
        db.session.commit()
        flash("Student added successfully.", "success")
        return redirect(url_for("add_student"))

    return render_template("add_student.html", classrooms=classrooms)


@app.route("/admin/add-teacher", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_teacher():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        employee_code = request.form.get("employee_code", "").strip()

        if not all([full_name, username, password, employee_code]):
            flash("All fields are required.", "danger")
            return render_template("add_teacher.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template("add_teacher.html")

        if Teacher.query.filter_by(employee_code=employee_code).first():
            flash("Employee code already exists.", "danger")
            return render_template("add_teacher.html")

        user = create_user(username, password, "teacher", full_name)
        db.session.add(Teacher(user_id=user.id, employee_code=employee_code))
        db.session.commit()
        flash("Teacher added successfully.", "success")
        return redirect(url_for("add_teacher"))

    return render_template("add_teacher.html")


@app.route("/admin/add-class", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_class():
    existing_classes = Classroom.query.order_by(Classroom.name, Classroom.section).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        section = request.form.get("section", "").strip()

        if not name or not section:
            flash("Class name and section are required.", "danger")
            return render_template("add_class.html", existing_classes=existing_classes)

        db.session.add(Classroom(name=name, section=section))
        db.session.commit()
        flash("Class added successfully.", "success")
        return redirect(url_for("add_class"))

    return render_template("add_class.html", existing_classes=existing_classes)


def get_filtered_attendance(classroom_id=None, attendance_date=None):
    query = Attendance.query

    if classroom_id:
        query = query.filter(Attendance.classroom_id == classroom_id)

    if attendance_date:
        query = query.filter(Attendance.date == attendance_date)

    return query.order_by(Attendance.date.desc()).all()



@app.route("/admin/attendance")
@login_required
@role_required("admin")
def admin_attendance():
    classrooms = Classroom.query.order_by(Classroom.name, Classroom.section).all()
    classroom_id = request.args.get("classroom_id", type=int)
    attendance_date = parse_attendance_date(request.args.get("attendance_date", ""))
    records = get_filtered_attendance(classroom_id, attendance_date)
    return render_template(
        "manage_attendance.html",
        classrooms=classrooms,
        attendance_records=records,
        selected_classroom_id=classroom_id,
        selected_date=request.args.get("attendance_date", ""),
    )


@app.route("/teacher/mark-attendance", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def mark_attendance():
    classrooms = Classroom.query.order_by(Classroom.name, Classroom.section).all()
    selected_classroom_id = request.values.get("classroom_id", type=int)
    selected_date = request.values.get("attendance_date", date.today().isoformat())
    attendance_date = parse_attendance_date(selected_date)

    students = []
    existing_statuses = {}
    if selected_classroom_id:
        students = (
            Student.query.filter_by(classroom_id=selected_classroom_id)
            .join(User)
            .order_by(User.full_name.asc())
            .all()
        )
        if attendance_date:
            existing_records = Attendance.query.filter_by(
                classroom_id=selected_classroom_id, date=attendance_date
            ).all()
            existing_statuses = {
                record.student_id: record.status for record in existing_records
            }

    if request.method == "POST":
        if not selected_classroom_id or not attendance_date:
            flash("Please select a class and valid date.", "danger")
            return render_template(
                "mark_attendance.html",
                classrooms=classrooms,
                students=students,
                selected_classroom_id=selected_classroom_id,
                selected_date=selected_date,
                existing_statuses=existing_statuses,
            )

        Attendance.query.filter_by(classroom_id=selected_classroom_id, date=attendance_date).delete(
            synchronize_session=False
        )

        saved_count = 0
        for student in students:
            status = request.form.get(f"status_{student.id}", "Absent")
            db.session.add(
                Attendance(
                    student_id=student.id,
                    classroom_id=selected_classroom_id,
                    date=attendance_date,
                    status=status if status in {"Present", "Absent"} else "Absent",
                    marked_by=session["user_id"],
                )
            )
            saved_count += 1

        db.session.commit()
        flash(f"Attendance saved for {saved_count} students.", "success")
        return redirect(
            url_for(
                "mark_attendance",
                classroom_id=selected_classroom_id,
                attendance_date=attendance_date.isoformat(),
            )
        )

    return render_template(
        "mark_attendance.html",
        classrooms=classrooms,
        students=students,
        selected_classroom_id=selected_classroom_id,
        selected_date=selected_date,
        existing_statuses=existing_statuses,
    )


@app.route("/teacher/view-attendance")
@login_required
@role_required("teacher", "admin")
def teacher_view_attendance():
    classrooms = Classroom.query.order_by(Classroom.name, Classroom.section).all()
    classroom_id = request.args.get("classroom_id", type=int)
    attendance_date = parse_attendance_date(request.args.get("attendance_date", ""))
    records = get_filtered_attendance(classroom_id, attendance_date)
    return render_template(
        "view_attendance.html",
        classrooms=classrooms,
        attendance_records=records,
        selected_classroom_id=classroom_id,
        selected_date=request.args.get("attendance_date", ""),
    )


@app.route("/student/view-attendance")
@login_required
@role_required("student")
def student_view_attendance():
    return render_template(
        "student_dashboard.html", **get_student_dashboard_data(session["user_id"])
    )


with app.app_context():
    initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
