from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from models import User, Registration, Event
from extensions import db, bcrypt
from utils import generate_qr_code
from email_utils import send_registration_confirmation_email
import time

stu_bp = Blueprint("stu", __name__, template_folder="templates")

# STUDENT LOGIN
@stu_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("stu.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.verify_password(username, password)

        if user and user.role == "stu":
            login_user(user)
            return redirect(url_for("stu.dashboard"))
        
        flash("Invalid register number or password", "error")

    return render_template("stu_login.html")

# STUDENT REGISTER
@stu_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("stu.dashboard"))

    if request.method == "POST":
        register_number = request.form.get("register_number")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        user_otp = request.form.get("otp")

        if not register_number or not register_number.isdigit():
            flash("Register Number must contain only numbers.", "error")
            return redirect(url_for("stu.register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("stu.register"))

        if time.time() > session.get("otp_expiry", 0):
            flash("OTP expired. Please request again.", "error")
            return redirect(url_for("stu.register"))

        if email != session.get("registration_email") or user_otp != session.get("registration_otp"):
            flash("Invalid OTP.", "error")
            return redirect(url_for("stu.register"))

        # create user
        student_id = User.create_user(
            username=register_number,
            password=password,
            role="stu",
            email=email,
            name=register_number
        )

        # generate QR
        qr_path = generate_qr_code(str(student_id), register_number)
        User.update_qr_path(student_id, qr_path)

        # clear session
        session.pop("registration_otp", None)
        session.pop("registration_email", None)
        session.pop("otp_expiry", None)

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("stu.login"))

    return render_template("stu_register.html")

# STUDENT LOGOUT
@stu_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("stu.login"))

@stu_bp.route("/dashboard")
@login_required
def dashboard():
    participation_count = Registration.query.filter_by(student_id=current_user.id).count()
    upcoming_events = Event.query.filter_by(approval_status="Approved").count()
    return render_template("stu_dashboard.html", 
                           participation_count=participation_count,
                           upcoming_events=upcoming_events)

@stu_bp.route("/profile")
@login_required
def profile():
    return render_template("stu_profile.html")

@stu_bp.route("/events")
@login_required
def events():
    events_list = Event.query.filter_by(approval_status="Approved").all()
    
    # Check what user is already registered for
    user_reg_ids = [r.event_id for r in Registration.query.filter_by(student_id=current_user.id).all()]
    
    enriched_events = []
    for event in events_list:
        reg_count = Registration.query.filter_by(event_id=event.id).count()
        event_dict = {
            "id": event.id,
            "title": event.title,
            "club_name": event.club_name,
            "category": event.category,
            "description": event.description,
            "event_date": event.event_date,
            "fee": event.fee,
            "poster": event.poster,
            "whatsapp_link": event.whatsapp_link,
            "slots_remaining": event.available_seats if event.available_seats is not None else max(0, (event.max_participants or 100) - reg_count),
            "is_full": (event.available_seats == 0) if event.available_seats is not None else (reg_count >= (event.max_participants or 100)),
            "is_registered": event.id in user_reg_ids
        }
        enriched_events.append(event_dict)
        
    return render_template("stu_events.html", events=enriched_events)

@stu_bp.route("/register_event/<int:event_id>")
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if already registered
    existing = Registration.query.filter_by(event_id=event_id, student_id=current_user.id).first()
    if existing:
        flash("You are already registered for this event!", "info")
        return redirect(url_for("stu.registrations"))
    
    # Check seat availability
    if event.available_seats is not None and event.available_seats <= 0:
        flash("Sorry, this event is already full!", "error")
        return redirect(url_for("stu.events"))

    # Create a pending registration
    fee_str = str(event.fee).replace('.','',1) if event.fee else "0"
    fee = float(event.fee) if fee_str.isdigit() else 0.0
    
    reg = Registration(
        event_id=event_id,
        student_id=current_user.id,
        amount=fee,
        payment_status="Pending"
    )
    db.session.add(reg)
    
    # If free, confirm immediately and update capacity
    if fee <= 0:
        reg.payment_status = "Confirmed"
        if event.available_seats is not None:
            event.available_seats -= 1
        db.session.commit()
        
        # Send confirmation email
        send_registration_confirmation_email(current_user.email, current_user.name or current_user.username, event.title)
        
        flash("Successfully registered for the event! Confirmation email sent.", "success")
        return redirect(url_for("stu.registrations"))

    db.session.commit()

    # If event has a Google Form, go there first before payment
    if event.google_form_link:
        return redirect(url_for("stu.google_form_step", reg_id=reg.id))

    # Paid event — go to payment
    flash("Enrolled! Please complete the payment to confirm your seat.", "success")
    return redirect(url_for("stu.payment", reg_id=reg.id))


@stu_bp.route("/google_form_step/<int:reg_id>")
@login_required
def google_form_step(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    if reg.student_id != current_user.id:
        flash("Unauthorized", "error")
        return redirect(url_for("stu.dashboard"))
    event = Event.query.get_or_404(reg.event_id)
    return render_template("stu_google_form_step.html", reg=reg, event=event)


@stu_bp.route("/payment/<int:reg_id>")
@login_required
def payment(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    if reg.student_id != current_user.id:
        flash("Unauthorized access", "error")
        return redirect(url_for("stu.dashboard"))
    
    event = Event.query.get(reg.event_id)
    return render_template("stu_payment_gateway.html", reg=reg, event=event)

@stu_bp.route("/confirm_payment/<int:reg_id>", methods=["POST"])
@login_required
def confirm_payment(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    txn_id = request.form.get("transaction_id")
    
    if not txn_id:
        flash("Please provide Transaction ID.", "error")
        return redirect(url_for("stu.payment", reg_id=reg_id))
        
    reg.transaction_id = txn_id
    reg.payment_status = "Payment Under Verification"
    db.session.commit()
    
    flash("Payment submitted! It will be verified by the coordinator.", "success")
    return redirect(url_for("stu.payments"))

@stu_bp.route("/registrations")
@login_required
def registrations():
    regs = Registration.query.filter_by(student_id=current_user.id).all()
    enriched_regs = []
    for r in regs:
        event = Event.query.get(r.event_id)
        enriched_regs.append({
            "reg": r,
            "event": event
        })
    return render_template("stu_registrations.html", registrations=enriched_regs)

@stu_bp.route("/attendance")
@login_required
def attendance():
    regs = Registration.query.filter_by(student_id=current_user.id).all()
    attendance_data = []
    for r in regs:
        event = Event.query.get(r.event_id)
        if event:
            attendance_data.append({
                "event_name": event.title,
                "club_name": event.club_name,
                "date": event.event_date,
                "status": r.attendance_status
            })
    return render_template("stu_attendance.html", attendance_logs=attendance_data)

@stu_bp.route("/certificates")
@login_required
def certificates():
    from models import Certificate
    certs = Certificate.query.filter_by(student_id=current_user.id).all()
    enriched_certs = []
    for c in certs:
        event = Event.query.get(c.event_id)
        enriched_certs.append({
            "cert": c,
            "event_title": event.title if event else "Unknown Event",
            "date": event.event_date if event else "N/A"
        })
    return render_template("stu_certificates.html", certificates=enriched_certs)

@stu_bp.route("/download_certificate/<int:cert_id>")
@login_required
def download_certificate(cert_id):
    from models import Certificate
    import os
    from flask import send_from_directory
    
    cert = Certificate.query.get_or_404(cert_id)
    if cert.student_id != current_user.id:
        flash("Unauthorized", "error")
        return redirect(url_for("stu.certificates"))
        
    directory = os.path.join(current_app.root_path, os.path.dirname(cert.file_path))
    filename = os.path.basename(cert.file_path)
    return send_from_directory(directory, filename, as_attachment=True)

@stu_bp.route("/payments")
@login_required
def payments():
    regs = Registration.query.filter_by(student_id=current_user.id).all()
    payment_history = []
    total_paid = 0.0
    
    for r in regs:
        if r.amount > 0:
            event = Event.query.get(r.event_id)
            payment_history.append({
                "reg": r,
                "event_title": event.title if event else "Unknown Event"
            })
            if r.payment_status == "Confirmed":
                total_paid += r.amount
                
    return render_template("stu_payments.html", 
                           payments=payment_history, 
                           total_paid=total_paid)

@stu_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_credits":
            ee = request.form.get("ee_credits", 0)
            g2 = request.form.get("group2_credits", 0)
            g3 = request.form.get("group3_credits", 0)
            User.update_credits(current_user.id, ee, g2, g3)
            flash("Credits updated successfully!", "success")
            
        elif action == "change_password":
            current_pwd = request.form.get("current_password")
            new_pwd = request.form.get("new_password")
            confirm_pwd = request.form.get("confirm_password")
            
            if not bcrypt.check_password_hash(current_user.password, current_pwd):
                flash("Current password incorrect.", "error")
            elif new_pwd != confirm_pwd:
                flash("New passwords do not match.", "error")
            else:
                User.update_password(current_user.id, new_pwd)
                flash("Password changed successfully!", "success")
                
        return redirect(url_for("stu.settings"))
        
    return render_template("stu_settings.html")
