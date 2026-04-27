from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# -------------------- Models --------------------

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    appointment_date = db.Column(db.String(20), nullable=False)
    appointment_time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="Pending")


class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    slot_date = db.Column(db.String(20), nullable=False)
    slot_time = db.Column(db.String(20), nullable=False)
    is_booked = db.Column(db.Boolean, default=False)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    qualification = db.Column(db.String(100), nullable=True)
    experience = db.Column(db.String(50), nullable=True)


# -------------------- Home --------------------

@app.route("/")
def home():
    return render_template("index.html")


# -------------------- Patient --------------------

@app.route("/patient/register", methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing_patient = Patient.query.filter_by(email=email).first()
        if existing_patient:
            flash("Email already registered.")
            return redirect(url_for("patient_register"))

        new_patient = Patient(
            name=name,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_patient)
        db.session.commit()

        flash("Patient registration successful. Please login.")
        return redirect(url_for("patient_login"))

    return render_template("patient_register.html")


@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        patient = Patient.query.filter_by(email=email).first()
        if patient and check_password_hash(patient.password, password):
            session.clear()
            session["patient_id"] = patient.id
            session["patient_name"] = patient.name
            session["role"] = "patient"
            return redirect(url_for("patient_dashboard"))
        else:
            flash("Invalid patient email or password.")

    return render_template("patient_login.html")


@app.route("/patient/dashboard")
def patient_dashboard():
    if session.get("role") != "patient":
        return redirect(url_for("patient_login"))

    doctors = Doctor.query.all()
    return render_template("patient_dashboard.html", doctors=doctors)

# -------------------- Doctor --------------------


@app.route("/doctor/register", methods=["GET", "POST"])
def doctor_register():
    if request.method == "POST":
        name = request.form["name"]
        specialization = request.form["specialization"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        qualification = request.form["qualification"]
        experience = request.form["experience"]

        existing_doctor = Doctor.query.filter_by(email=email).first()
        if existing_doctor:
            flash("Doctor email already registered.")
            return redirect(url_for("doctor_register"))

        new_doctor = Doctor(
            name=name,
            specialization=specialization,
            email=email,
            password=generate_password_hash(password),
            phone=phone,
            qualification=qualification,
            experience=experience
        )

        db.session.add(new_doctor)
        db.session.commit()

        flash("Doctor registration successful. Please login.")
        return redirect(url_for("doctor_login"))

    return render_template("doctor_register.html")

@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        doctor = Doctor.query.filter_by(email=email).first()
        if doctor and check_password_hash(doctor.password, password):
            session.clear()
            session["doctor_id"] = doctor.id
            session["doctor_name"] = doctor.name
            session["role"] = "doctor"
            return redirect(url_for("doctor_dashboard"))
        else:
            flash("Invalid doctor email or password.")

    return render_template("doctor_login.html")


@app.route("/doctor/profile", methods=["GET", "POST"])
def doctor_profile():
    if session.get("role") != "doctor":
        return redirect(url_for("doctor_login"))

    doctor = Doctor.query.get_or_404(session["doctor_id"])

    if request.method == "POST":
        doctor.name = request.form["name"]
        doctor.email = request.form["email"]
        doctor.specialization = request.form["specialization"]
        doctor.phone = request.form["phone"]
        doctor.qualification = request.form["qualification"]
        doctor.experience = request.form["experience"]

        db.session.commit()
        flash("Doctor profile updated successfully.")
        return redirect(url_for("doctor_profile"))

    return render_template("doctor_profile.html", doctor=doctor)

@app.route("/doctor/dashboard")
def doctor_dashboard():
    if session.get("role") != "doctor":
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()

    appointment_data = []
    for appointment in appointments:
        patient = Patient.query.get(appointment.patient_id)
        appointment_data.append({
            "id": appointment.id,
            "patient_name": patient.name if patient else "Unknown",
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.appointment_time,
            "status": appointment.status
        })

    slots = Slot.query.filter_by(doctor_id=doctor_id, is_booked=False).all()

    return render_template(
        "doctor_dashboard.html",
        appointments=appointment_data,
        slots=slots
    )




