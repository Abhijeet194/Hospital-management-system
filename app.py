from flask import Flask, render_template, request, redirect, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy import text
import os

app = Flask(__name__)


app.secret_key = os.getenv("abhi@995545", "dev-secret-key")


app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://root:password@127.0.0.1:3306/hospital_db?charset=utf8mb4'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


def db_fetchone(query, params=None):
    result = db.session.execute(text(query), params or {})
    return result.fetchone()


def db_fetchall(query, params=None):
    result = db.session.execute(text(query), params or {})
    return result.fetchall()


def db_execute(query, params=None):
    db.session.execute(text(query), params or {})
    db.session.commit()


def login_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'role' not in session:
                return redirect('/login')

            if role and session.get('role') != role:
                return redirect('/login')

            return func(*args, **kwargs)
        return wrapper
    return decorator


def format_time_12h(value):
    if not value:
        return ""

    try:
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds % 3600) // 60

            suffix = "AM" if hours < 12 else "PM"
            hour_12 = hours % 12 or 12

            return f"{hour_12:02d}:{minutes:02d} {suffix}"

        if hasattr(value, "strftime"):
            return value.strftime("%I:%M %p")

        return str(value)[:5]

    except:
        return str(value)


@app.route('/')
def home():
    return redirect('/login')


@app.route('/login')
def login():
    return render_template('select_login.html')


@app.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        username = request.form.get('username')
        password = request.form.get('password')

        if not name or not username or not password:
            flash("Name, Username and Password are required!", "error")
            return redirect('/patient/register')

        hashed_password = generate_password_hash(password)

        try:
            db.session.execute(
                text("""
                    INSERT INTO patients(name, age, gender)
                    VALUES(:name, :age, :gender)
                """),
                {"name": name, "age": age, "gender": gender}
            )

            patient_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()

            db.session.execute(
                text("""
                    INSERT INTO users(username, password, role, ref_id)
                    VALUES(:username, :password, 'patient', :ref_id)
                """),
                {"username": username, "password": hashed_password, "ref_id": patient_id}
            )

            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect('/patient/login')

        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {e}", "error")
            return redirect('/patient/register')

    return render_template('patient_register.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = db_fetchone(
            "SELECT id, username, password FROM users WHERE username=:username AND role='admin'",
            {"username": username}
        )

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'admin'
            return redirect('/admin/dashboard')

        flash("Invalid admin credentials!")

    return render_template(
        'base_login.html',
        title="Admin Login",
        heading="Admin Login",
        action_url="/admin/login",
        btn_class="btn-primary"
    )


@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = db_fetchone(
            "SELECT id, username, password, ref_id FROM users WHERE username=:username AND role='doctor'",
            {"username": username}
        )

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'doctor'
            session['ref_id'] = user[3]
            return redirect('/doctor/dashboard')

        flash("Invalid doctor credentials!")

    return render_template(
        'base_login.html',
        title="Doctor Login",
        heading="Doctor Login",
        action_url="/doctor/login",
        btn_class="btn-success"
    )


@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = db_fetchone(
            "SELECT id, username, password, ref_id FROM users WHERE username=:username AND role='patient'",
            {"username": username}
        )

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'patient'
            session['ref_id'] = user[3]
            return redirect('/patient/dashboard')

        flash("Invalid patient credentials!")

    return render_template(
        'base_login.html',
        title="Patient Login",
        heading="Patient Login",
        action_url="/patient/login",
        btn_class="btn-info"
    )


@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    total_patients = db_fetchone("SELECT COUNT(*) FROM patients")[0]
    total_doctors = db_fetchone("SELECT COUNT(*) FROM doctors")[0]
    total_appointments = db_fetchone("SELECT COUNT(*) FROM appointments")[0]

    return render_template(
        'admin_dashboard.html',
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_appointments=total_appointments
    )


@app.route('/doctor/dashboard')
@login_required('doctor')
def doctor_dashboard():
    return render_template('doctor_dashboard.html')


@app.route('/patient/dashboard')
@login_required('patient')
def patient_dashboard():
    return render_template('patient_dashboard.html')


@app.route('/patients')
@login_required('admin')
def patients():
    data = db_fetchall("SELECT id, name, age, gender, disease FROM patients")
    return render_template('patients.html', patients=data)


@app.route('/doctors')
@login_required('admin')
def doctors():
    data = db_fetchall("SELECT id, name, age, gender, specialization FROM doctors")
    return render_template('doctors.html', doctors=data)


@app.route('/appointments')
@login_required()
def appointments():
    role = session.get('role')

    query = """
        SELECT a.id, p.name, d.name, a.date, a.disease, a.status, a.time, a.is_emergency, a.mobile
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        LEFT JOIN doctors d ON a.doctor_id = d.id
    """

    if role == 'patient':
        rows = db_fetchall(
            query + " WHERE a.patient_id = :ref_id ORDER BY a.is_emergency DESC, a.date ASC",
            {"ref_id": session['ref_id']}
        )
    elif role == 'doctor':
        rows = db_fetchall(
            query + " WHERE a.doctor_id = :ref_id ORDER BY a.is_emergency DESC, a.date ASC",
            {"ref_id": session['ref_id']}
        )
    else:
        rows = db_fetchall(
            query + " ORDER BY a.is_emergency DESC, a.date ASC"
        )

    data = []
    for r in rows:
        r = list(r)
        r[6] = format_time_12h(r[6])
        data.append(r)

    return render_template('appointments.html', appointments=data)


@app.route('/patient/book', methods=['GET', 'POST'])
@login_required('patient')
def patient_book():
    if request.method == 'POST':
        date = request.form.get('date')
        disease = request.form.get('disease')
        mobile = request.form.get('mobile')
        patient_id = session['ref_id']
        is_emergency = 1 if request.form.get('emergency') else 0

        if not date or not disease or not mobile:
            flash("All fields are required!", "error")
            return redirect('/patient/book')

        try:
            db.session.execute(
                text("""
                    INSERT INTO appointments(patient_id, date, disease, mobile, status, is_emergency)
                    VALUES(:patient_id, :date, :disease, :mobile, 'Pending', :is_emergency)
                """),
                {
                    "patient_id": patient_id,
                    "date": date,
                    "disease": disease,
                    "mobile": mobile,
                    "is_emergency": is_emergency
                }
            )
            db.session.commit()

            flash("Appointment booked successfully!", "success")
            return redirect('/appointments')

        except Exception as e:
            db.session.rollback()
            flash(f"Booking failed: {e}", "error")
            return redirect('/patient/book')

    return render_template('patient_book.html')


@app.route('/admin/confirm', methods=['POST'])
@login_required('admin')
def confirm_appointment():
    appointment_id = request.form.get('id')
    doctor_id = request.form.get('doctor_id')
    time = request.form.get('time')

    db_execute("""
        UPDATE appointments
        SET doctor_id=:doctor_id, time=:time, status='Confirmed'
        WHERE id=:appointment_id
    """, {"doctor_id": doctor_id, "time": time, "appointment_id": appointment_id})

    return redirect('/appointments')


@app.route('/add_doctor', methods=['POST'])
@login_required('admin')
def add_doctor():
    name = request.form.get('name')
    age = request.form.get('age')
    gender = request.form.get('gender')
    specialization = request.form.get('specialization')

    username = request.form.get('username')
    password = generate_password_hash(request.form.get('password'))

    try:
        db.session.execute(
            text("""
                INSERT INTO doctors(name, age, gender, specialization)
                VALUES(:name, :age, :gender, :specialization)
            """),
            {"name": name, "age": age, "gender": gender, "specialization": specialization}
        )

        doctor_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()

        db.session.execute(
            text("""
                INSERT INTO users(username, password, role, ref_id)
                VALUES(:username, :password, 'doctor', :ref_id)
            """),
            {"username": username, "password": password, "ref_id": doctor_id}
        )

        db.session.commit()

        flash(f"Doctor added! Login username: {username}, password: 1234", "success")
        return redirect('/doctors')

    except Exception as e:
        db.session.rollback()
        flash(f"Doctor add failed: {e}", "error")
        return redirect('/doctors')


@app.route('/doctor/complete', methods=['POST'])
@login_required('doctor')
def complete_appointment():
    appointment_id = request.form.get('id')

    db_execute("""
        UPDATE appointments
        SET status = 'Completed'
        WHERE id = :appointment_id
    """, {"appointment_id": appointment_id})

    flash("Marked as completed!", "success")
    return redirect('/appointments')


@app.route('/patient/cancel', methods=['POST'])
@login_required('patient')
def cancel_appointment():
    appointment_id = request.form.get('id')
    patient_id = session.get('ref_id')

    db_execute("""
        DELETE FROM appointments
        WHERE id = :appointment_id AND patient_id = :patient_id AND status = 'Pending'
    """, {"appointment_id": appointment_id, "patient_id": patient_id})

    flash("Appointment cancelled!", "success")
    return redirect('/appointments')


@app.route('/delete_doctor/<int:id>')
@login_required('admin')
def delete_doctor(id):
    db_execute("DELETE FROM doctors WHERE id=:id", {"id": id})
    flash("Doctor deleted successfully!", "success")
    return redirect('/doctors')


@app.route('/update_doctor/<int:id>', methods=['GET', 'POST'])
@login_required('admin')
def update_doctor(id):
    if request.method == 'POST':
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        age = request.form.get('age')
        gender = request.form.get('gender')
        username = request.form.get('username')
        password = request.form.get('password')

        age = int(age) if age else None

        try:
            db.session.execute(
                text("""
                    UPDATE doctors
                    SET name=:name, specialization=:specialization, age=:age, gender=:gender
                    WHERE id=:id
                """),
                {"name": name, "specialization": specialization, "age": age, "gender": gender, "id": id}
            )

            if password:
                hashed_password = generate_password_hash(password)
                db.session.execute(
                    text("""
                        UPDATE users
                        SET username=:username, password=:password
                        WHERE ref_id=:ref_id AND role='doctor'
                    """),
                    {"username": username, "password": hashed_password, "ref_id": id}
                )
            else:
                db.session.execute(
                    text("""
                        UPDATE users
                        SET username=:username
                        WHERE ref_id=:ref_id AND role='doctor'
                    """),
                    {"username": username, "ref_id": id}
                )

            db.session.commit()
            flash("Doctor updated successfully!", "success")
            return redirect('/doctors')

        except Exception as e:
            db.session.rollback()
            flash(f"Update failed: {e}", "error")
            return redirect('/doctors')

    doctor = db_fetchone("SELECT * FROM doctors WHERE id=:id", {"id": id})
    user = db_fetchone("SELECT username FROM users WHERE ref_id=:id AND role='doctor'", {"id": id})

    return render_template('update_doctor.html', doctor=doctor, user=user)


@app.route('/delete_patient/<int:id>')
@login_required('admin')
def delete_patient(id):
    db_execute("DELETE FROM patients WHERE id=:id", {"id": id})
    flash("Patient deleted successfully!", "success")
    return redirect('/patients')


@app.route('/admin/delete_appointment', methods=['POST'])
@login_required('admin')
def delete_appointment():
    appointment_id = request.form.get('id')

    db_execute("DELETE FROM appointments WHERE id=:id", {"id": appointment_id})
    flash("Appointment deleted successfully!", "success")
    return redirect('/appointments')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True, port=10000)