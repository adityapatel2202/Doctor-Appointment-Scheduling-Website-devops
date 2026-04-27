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

@app.route("/book/<int:doctor_id>", methods=["GET", "POST"])
def book_appointment(doctor_id):
    if session.get("role") != "patient":
        return redirect(url_for("patient_login"))

    doctor = Doctor.query.get_or_404(doctor_id)

    # show only unbooked slots for this doctor
    available_slots = Slot.query.filter_by(doctor_id=doctor_id, is_booked=False).all()

    if request.method == "POST":
        slot_id = request.form["slot_id"]

        selected_slot = Slot.query.get(slot_id)

        if not selected_slot or selected_slot.is_booked:
            flash("This slot is no longer available.")
            return redirect(url_for("book_appointment", doctor_id=doctor_id))

        new_appointment = Appointment(
            patient_id=session["patient_id"],
            doctor_id=doctor_id,
            appointment_date=selected_slot.slot_date,
            appointment_time=selected_slot.slot_time,
            status="Pending"
        )

        selected_slot.is_booked = True

        db.session.add(new_appointment)
        db.session.commit()

        flash("Appointment booked successfully.")
        return redirect(url_for("my_appointments"))

    return render_template("book_appointment.html", doctor=doctor, slots=available_slots)

@app.route("/my-appointments")
def my_appointments():
    if session.get("role") != "patient":
        return redirect(url_for("patient_login"))

    appointments = Appointment.query.filter_by(patient_id=session["patient_id"]).all()

    appointment_data = []
    for appointment in appointments:
        doctor = Doctor.query.get(appointment.doctor_id)
        appointment_data.append({
            "id": appointment.id,
            "doctor_name": doctor.name if doctor else "Unknown",
            "specialization": doctor.specialization if doctor else "Unknown",
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.appointment_time,
            "status": appointment.status
        })

    return render_template("my_appointments.html", appointments=appointment_data)


@app.route("/cancel-appointment/<int:appointment_id>")
def cancel_appointment(appointment_id):
    if session.get("role") != "patient":
        return redirect(url_for("patient_login"))

    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.patient_id != session["patient_id"]:
        flash("Unauthorized action.")
        return redirect(url_for("my_appointments"))

    appointment.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled successfully.")
    return redirect(url_for("my_appointments"))


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


@app.route("/doctor/update-appointment/<int:appointment_id>/<string:new_status>")
def update_appointment_status(appointment_id, new_status):
    if session.get("role") != "doctor":
        return redirect(url_for("doctor_login"))

    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != session["doctor_id"]:
        flash("Unauthorized action.")
        return redirect(url_for("doctor_dashboard"))

    allowed_statuses = ["Accepted", "Rejected", "Cancelled", "Completed"]

    if new_status in allowed_statuses:
        appointment.status = new_status

        if new_status == "Cancelled":
            slot = Slot.query.filter_by(
                doctor_id=appointment.doctor_id,
                slot_date=appointment.appointment_date,
                slot_time=appointment.appointment_time
            ).first()

            if slot:
                slot.is_booked = False

        db.session.commit()
        flash(f"Appointment {new_status.lower()} successfully.")

    return redirect(url_for("doctor_dashboard"))


@app.route("/doctor/add-slot", methods=["GET", "POST"])
def add_slot():
    if session.get("role") != "doctor":
        return redirect(url_for("doctor_login"))

    if request.method == "POST":
        slot_date = request.form["slot_date"]
        slot_time = request.form["slot_time"]

        new_slot = Slot(
            doctor_id=session["doctor_id"],
            slot_date=slot_date,
            slot_time=slot_time,
            is_booked=False
        )
        db.session.add(new_slot)
        db.session.commit()

        flash("Slot added successfully.")
        return redirect(url_for("doctor_dashboard"))

    return render_template("manage_slots.html")


@app.route("/doctor/delete-slot/<int:slot_id>")
def delete_slot(slot_id):
    if session.get("role") != "doctor":
        return redirect(url_for("doctor_login"))

    slot = Slot.query.get_or_404(slot_id)

    if slot.doctor_id != session["doctor_id"]:
        flash("Unauthorized action.")
        return redirect(url_for("doctor_dashboard"))

    db.session.delete(slot)
    db.session.commit()
    flash("Slot deleted successfully.")
    return redirect(url_for("doctor_dashboard"))


# -------------------- Logout --------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("home"))


# -------------------- Run App --------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # # Add sample doctors only if table is empty
        # if Doctor.query.count() == 0:
        #     doctor1 = Doctor(
        #         name="Raj Mehta",
        #         specialization="Cardiologist",
        #         email="raj@doctor.com",
        #         password=generate_password_hash("1234")
        #     )
        #     doctor2 = Doctor(
        #         name="Neha Sharma",
        #         specialization="Dentist",
        #         email="neha@doctor.com",
        #         password=generate_password_hash("1234")
        #     )
        #     db.session.add(doctor1)
        #     db.session.add(doctor2)
        #     db.session.commit()

    app.run(debug=True)

