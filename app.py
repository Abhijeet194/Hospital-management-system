from flask import Flask, render_template, request, redirect, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg2.extras
import psycopg2
import os
from datetime import timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"



def get_db():
    uri = os.environ.get("DATABASE_URL")

    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(uri)
    conn.autocommit = True
    return conn


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

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute(
            "INSERT INTO patients(name, age, gender) VALUES(%s,%s,%s)",
            (name, age, gender)
        )
        conn.commit()

        patient_id = cur.lastrowid

        hashed_password = generate_password_hash(password)

        cur.execute(
            "INSERT INTO users(username, password, role, ref_id) VALUES(%s,%s,%s,%s)",
            (username, hashed_password, 'patient', patient_id)
        )

        conn.commit()
        conn.close()

        flash("Registration successful! Please login.", "success")
        return redirect('/patient/login')

    return render_template('patient_register.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, password FROM users WHERE username=%s AND role='admin'",
            (username,)
        )
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
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

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, password, ref_id FROM users WHERE username=%s AND role='doctor'",
            (username,)
        )
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = 'doctor'
            session['ref_id'] = user['ref_id']
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

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, password, ref_id FROM users WHERE username=%s AND role='patient'",
            (username,)
        )
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = 'patient'
            session['ref_id'] = user['ref_id']
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

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT COUNT(*) FROM patients")
    total_patients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cur.fetchone()[0]

    conn.close()

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
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, name, age, gender, disease FROM patients")
    data = cur.fetchall()
    conn.close()
    return render_template('patients.html', patients=data)


@app.route('/doctors')
@login_required('admin')
def doctors():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, name, age, gender, specialization FROM doctors")
    data = cur.fetchall()
    conn.close()
    return render_template('doctors.html', doctors=data)


@app.route('/appointments')
@login_required()
def appointments():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    role = session.get('role')

    query = """
        SELECT a.id, p.name, d.name, a.date, a.disease, a.status, a.time, a.is_emergency, a.mobile
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        LEFT JOIN doctors d ON a.doctor_id = d.id
    """

    if role == 'patient':
        cur.execute(query + " WHERE a.patient_id = %s ORDER BY a.is_emergency DESC, a.date ASC", (session['ref_id'],))
    elif role == 'doctor':
        cur.execute(query + " WHERE a.doctor_id = %s ORDER BY a.is_emergency DESC, a.date ASC", (session['ref_id'],))
    else:
        cur.execute(query + " ORDER BY a.is_emergency DESC, a.date ASC")

    rows = cur.fetchall()
    conn.close()

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

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO appointments(patient_id, date, disease, mobile, status, is_emergency)
            VALUES(%s, %s, %s, %s, 'Pending', %s)
        """, (patient_id, date, disease, mobile, is_emergency))

        conn.commit()
        conn.close()

        flash("Appointment booked successfully!", "success")
        return redirect('/appointments')

    return render_template('patient_book.html')


@app.route('/admin/confirm', methods=['POST'])
@login_required('admin')
def confirm_appointment():
    appointment_id = request.form.get('id')
    doctor_id = request.form.get('doctor_id')
    time = request.form.get('time')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        UPDATE appointments
        SET doctor_id=%s, time=%s, status='Confirmed'
        WHERE id=%s
    """, (doctor_id, time, appointment_id))
    conn.commit()
    conn.close()

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

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        INSERT INTO doctors(name, age, gender, specialization)
        VALUES(%s, %s, %s, %s)
    """, (name, age, gender, specialization))

    doctor_id = cur.lastrowid

    cur.execute("""
        INSERT INTO users(username, password, role, ref_id)
        VALUES(%s, %s, 'doctor', %s)
    """, (username, password, doctor_id))

    conn.commit()
    conn.close()

    flash(f"Doctor added! Login username: {username}, password: 1234", "success")
    return redirect('/doctors')


@app.route('/doctor/complete', methods=['POST'])
@login_required('doctor')
def complete_appointment():
    appointment_id = request.form.get('id')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        UPDATE appointments
        SET status = 'Completed'
        WHERE id = %s
    """, (appointment_id,))
    conn.commit()
    conn.close()

    flash("Marked as completed!", "success")
    return redirect('/appointments')


@app.route('/patient/cancel', methods=['POST'])
@login_required('patient')
def cancel_appointment():
    appointment_id = request.form.get('id')
    patient_id = session.get('ref_id')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        DELETE FROM appointments
        WHERE id = %s AND patient_id = %s AND status = 'Pending'
    """, (appointment_id, patient_id))

    conn.commit()
    conn.close()

    flash("Appointment cancelled!", "success")
    return redirect('/appointments')


@app.route('/delete_doctor/<int:id>')
@login_required('admin')
def delete_doctor(id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("DELETE FROM doctors WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    flash("Doctor deleted successfully!", "success")
    return redirect('/doctors')


@app.route('/update_doctor/<int:id>', methods=['GET', 'POST'])
@login_required('admin')
def update_doctor(id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'POST':
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        age = request.form.get('age')
        gender = request.form.get('gender')
        username = request.form.get('username')
        password = request.form.get('password')

        age = int(age) if age else None

        cur.execute("""
            UPDATE doctors
            SET name=%s, specialization=%s, age=%s, gender=%s
            WHERE id=%s
        """, (name, specialization, age, gender, id))

        if password:
            hashed_password = generate_password_hash(password)
            cur.execute("""
                UPDATE users
                SET username=%s, password=%s
                WHERE ref_id=%s AND role='doctor'
            """, (username, hashed_password, id))
        else:
            cur.execute("""
                UPDATE users
                SET username=%s
                WHERE ref_id=%s AND role='doctor'
            """, (username, id))

        conn.commit()
        conn.close()

        flash("Doctor updated successfully!", "success")
        return redirect('/doctors')

    cur.execute("SELECT * FROM doctors WHERE id=%s", (id,))
    doctor = cur.fetchone()

    cur.execute("SELECT username FROM users WHERE ref_id=%s AND role='doctor'", (id,))
    user = cur.fetchone()

    conn.close()

    return render_template('update_doctor.html', doctor=doctor, user=user)


@app.route('/delete_patient/<int:id>')
@login_required('admin')
def delete_patient(id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("DELETE FROM patients WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    flash("Patient deleted successfully!", "success")
    return redirect('/patients')


@app.route('/admin/delete_appointment', methods=['POST'])
@login_required('admin')
def delete_appointment():
    appointment_id = request.form.get('id')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("DELETE FROM appointments WHERE id=%s", (appointment_id,))
    conn.commit()
    conn.close()

    flash("Appointment deleted successfully!", "success")
    return redirect('/appointments')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))