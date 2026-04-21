from flask import Flask, render_template, request, redirect, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "your_secret_key_here"


app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'hospital_db'

mysql = MySQL(app)


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

        cur = mysql.connection.cursor()

       
        cur.execute(
            "INSERT INTO patients(name, age, gender) VALUES(%s,%s,%s)",
            (name, age, gender)
        )
        mysql.connection.commit()

        patient_id = cur.lastrowid

        
        hashed_password = generate_password_hash(password)

        cur.execute(
            "INSERT INTO users(username, password, role, ref_id) VALUES(%s,%s,%s,%s)",
            (username, hashed_password, 'patient', patient_id)
        )

        mysql.connection.commit()
        cur.close()

        flash("Registration successful! Please login.", "success")
        return redirect('/patient/login')

    return render_template('patient_register.html')



@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE username=%s AND role='admin'", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'admin'
            return redirect('/admin/dashboard')

        flash("Invalid admin credentials!")

    return render_template('base_login.html', title="Admin Login")


@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password, ref_id FROM users WHERE username=%s AND role='doctor'", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'doctor'
            session['ref_id'] = user[3]
            return redirect('/doctor/dashboard')

        flash("Invalid doctor credentials!")

    return render_template('base_login.html', title="Doctor Login")



@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password, ref_id FROM users WHERE username=%s AND role='patient'", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'patient'
            session['ref_id'] = user[3]
            return redirect('/patient/dashboard')

        flash("Invalid patient credentials!")

    return render_template('base_login.html', title="Patient Login")


@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM patients")
    total_patients = cur.fetchone()[0]

  
    cur.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cur.fetchone()[0]

   
    cur.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cur.fetchone()[0]

    cur.close()

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
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, age, gender, disease FROM patients")
    data = cur.fetchall()
    cur.close()
    return render_template('patients.html', patients=data)


@app.route('/doctors')
@login_required('admin')
def doctors():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, age, gender, specialization FROM doctors")
    data = cur.fetchall()
    cur.close()
    return render_template('doctors.html', doctors=data)



@app.route('/appointments')
@login_required()
def appointments():
    cur = mysql.connection.cursor()
    role = session.get('role')

    query = """
        SELECT a.id, p.name, d.name, a.date, a.disease, a.status, a.time, a.is_emergency
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
    cur.close()

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
        patient_id = session['ref_id']

 
        is_emergency = 1 if request.form.get('emergency') else 0

     
        if not date or not disease:
            flash("All fields are required!", "error")
            return redirect('/patient/book')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO appointments(patient_id, date, disease, status, is_emergency)
            VALUES(%s, %s, %s, 'Pending', %s)
        """, (patient_id, date, disease, is_emergency))
        mysql.connection.commit()
        cur.close()

        flash("Appointment booked successfully!", "success")
        return redirect('/appointments')

    return render_template('patient_book.html')


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

    return redirect('/appointments')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')



if __name__ == '__main__':
    app.run(debug=True, port=8000)