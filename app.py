from flask import Flask, render_template, request, redirect, flash, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# ================= DATABASE CONFIG =================
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'hospital_db'

mysql = MySQL(app)

# ================= LOGIN DECORATOR =================
def login_required(role=None):
    def wrapper(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                return redirect('/login')

            if role and session.get('role') != role:
                return redirect('/login')

            return func(*args, **kwargs)

        return decorated_function
    return wrapper

# ================= TIME FORMAT FUNCTION (12 HOUR) =================
def format_time_12h(value):
    if value is None:
        return None

    try:
        # MySQL TIME often comes as timedelta
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            if total_seconds < 0:
                total_seconds = 0

            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds % 3600) // 60
            suffix = "AM" if hours < 12 else "PM"
            hour_12 = hours % 12 or 12
            return f"{hour_12:02d}:{minutes:02d} {suffix}"

        # datetime.time or datetime-like object
        if hasattr(value, "strftime"):
            return value.strftime("%I:%M %p")

        # string values like '14:30:00' or '14:30'
        s = str(value).strip()
        try:
            if len(s) >= 8:
                return datetime.strptime(s[:8], "%H:%M:%S").strftime("%I:%M %p")
            return datetime.strptime(s, "%H:%M").strftime("%I:%M %p")
        except:
            return s

    except:
        return str(value)

# ================= HOME =================
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login')
def login():
    return render_template('select_login.html')

# ================= ADMIN LOGIN =================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("All fields are required!", "error")
            return render_template('base_login.html', title="Admin Login")

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id, username, password FROM users WHERE username=%s AND role='admin'",
            (username,)
        )
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'admin'
            flash("Admin login successful!", "success")
            return redirect('/admin/dashboard')

        flash("Invalid admin credentials!", "error")

    return render_template('base_login.html', title="Admin Login")

# ================= DOCTOR LOGIN =================
@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("All fields are required!", "error")
            return render_template('base_login.html', title="Doctor Login")

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id, username, password, ref_id FROM users WHERE username=%s AND role='doctor'",
            (username,)
        )
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'doctor'
            session['ref_id'] = user[3]
            flash("Doctor login successful!", "success")
            return redirect('/doctor/dashboard')

        flash("Invalid doctor credentials!", "error")

    return render_template('base_login.html', title="Doctor Login")

# ================= PATIENT LOGIN =================
@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("All fields are required!", "error")
            return render_template('base_login.html', title="Patient Login")

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id, username, password, ref_id FROM users WHERE username=%s AND role='patient'",
            (username,)
        )
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'patient'
            session['ref_id'] = user[3]
            flash("Patient login successful!", "success")
            return redirect('/patient/dashboard')

        flash("Invalid patient credentials!", "error")

    return render_template('base_login.html', title="Patient Login")

# ================= DASHBOARDS =================
@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/doctor/dashboard')
@login_required('doctor')
def doctor_dashboard():
    return render_template('doctor_dashboard.html')

@app.route('/patient/dashboard')
@login_required('patient')
def patient_dashboard():
    return render_template('patient_dashboard.html')

# ================= PATIENTS MANAGEMENT =================
@app.route('/patients')
@login_required('admin')
def patients():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, age, gender, disease FROM patients")
    data = cur.fetchall()
    cur.close()
    return render_template('patients.html', patients=data)

@app.route('/add_patient', methods=['POST'])
@login_required('admin')
def add_patient():
    name = request.form.get('name', '').strip()
    age = request.form.get('age', '').strip()
    gender = request.form.get('gender', '').strip()
    disease = request.form.get('disease', '').strip()

    if not name:
        flash("Patient name is required!", "error")
        return redirect('/patients')

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO patients(name, age, gender, disease) VALUES(%s, %s, %s, %s)",
        (name, age, gender, disease)
    )
    mysql.connection.commit()
    cur.close()

    flash("Patient added successfully!", "success")
    return redirect('/patients')

# ================= DOCTORS MANAGEMENT =================
@app.route('/doctors')
@login_required('admin')
def doctors():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, age, gender, specialization FROM doctors")
    data = cur.fetchall()
    cur.close()
    return render_template('doctors.html', doctors=data)

@app.route('/add_doctor', methods=['POST'])
@login_required('admin')
def add_doctor():
    name = request.form.get('name', '').strip()
    age = request.form.get('age', '').strip()
    gender = request.form.get('gender', '').strip()
    specialization = request.form.get('specialization', '').strip()

    if not name:
        flash("Doctor name is required!", "error")
        return redirect('/doctors')

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO doctors(name, age, gender, specialization) VALUES(%s, %s, %s, %s)",
        (name, age, gender, specialization)
    )
    mysql.connection.commit()
    cur.close()

    flash("Doctor added successfully!", "success")
    return redirect('/doctors')

# ================= APPOINTMENTS =================
@app.route('/appointments')
@login_required()
def appointments():
    cur = mysql.connection.cursor()
    role = session.get('role')

    query = """
        SELECT
            a.id,
            p.name,
            d.name,
            a.date,
            a.disease,
            a.status,
            a.time
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        LEFT JOIN doctors d ON a.doctor_id = d.id
    """

    if role == 'patient':
        cur.execute(query + " WHERE a.patient_id = %s", (session['ref_id'],))
    elif role == 'doctor':
        cur.execute(query + " WHERE a.doctor_id = %s", (session['ref_id'],))
    else:
        cur.execute(query)

    rows = cur.fetchall()
    cur.close()

    data = []
    for row in rows:
        row = list(row)
        row[6] = format_time_12h(row[6])
        data.append(row)

    return render_template('appointments.html', appointments=data)

# ================= PATIENT BOOK APPOINTMENT =================
@app.route('/patient/book', methods=['GET', 'POST'])
@login_required('patient')
def patient_book():
    if request.method == 'POST':
        date = request.form.get('date')
        disease = request.form.get('disease')
        patient_id = session.get('ref_id')

        if not date or not disease:
            flash("All fields are required!", "error")
            return redirect('/patient/book')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO appointments(patient_id, date, disease, status, doctor_id, time)
            VALUES(%s, %s, %s, 'Pending', NULL, NULL)
        """, (patient_id, date, disease))
        mysql.connection.commit()
        cur.close()

        flash("Appointment request sent!", "success")
        return redirect('/appointments')

    return render_template('patient_book.html')

# ================= CONFIRM APPOINTMENT =================
@app.route('/admin/confirm', methods=['POST'])
@login_required('admin')
def confirm_appointment():
    appointment_id = request.form.get('id')
    doctor_id = request.form.get('doctor_id')
    time = request.form.get('time')

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE appointments
        SET doctor_id=%s, time=%s, status='Confirmed'
        WHERE id=%s
    """, (doctor_id, time, appointment_id))
    mysql.connection.commit()
    cur.close()

    flash("Appointment confirmed!", "success")
    return redirect('/appointments')

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect('/login')

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True, port=8000)