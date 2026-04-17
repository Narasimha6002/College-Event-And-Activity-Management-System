from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import Coordinator, Event, User 
from email_utils import send_registration_confirmation_email

clu_bp = Blueprint("clu", __name__, template_folder="templates")

@clu_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "clu":
            return redirect(url_for("clu.dashboard"))
        # If logged in as something else, just proceed with login check or redirect
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = Coordinator.verify_password(username, password)
        if user:
            login_user(user)
            return redirect(url_for("clu.dashboard"))
        
        flash("Invalid Coordinator credentials", "error")
    
    return render_template("clu_login.html")

@clu_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
    
    # Simple stats for dashboard
    from models import Event
    event_count = Event.query.filter_by(created_by=current_user.id).count()
    pending_events = Event.query.filter_by(created_by=current_user.id, approval_status="Pending Approval").count()
    
    return render_template("clu_dashboard.html", event_count=event_count, pending_events=pending_events)

@clu_bp.route("/upload_photo", methods=["POST"])
@login_required
def upload_photo():
    if current_user.role != "clu":
        return jsonify({"error": "Unauthorized"}), 403
    
    if "photo" not in request.files:
        flash("No file part", "error")
        return redirect(url_for("clu.dashboard"))
    
    file = request.files["photo"]
    if file.filename == "":
        flash("No selected file", "error")
        return redirect(url_for("clu.dashboard"))
    
    if file:
        import os
        from werkzeug.utils import secure_filename
        from extensions import db
        
        filename = secure_filename(f"club_{current_user.id}_{file.filename}")
        upload_folder = os.path.join(current_app.root_path, "static", "uploads", "clubs")
        os.makedirs(upload_folder, exist_ok=True)
        
        file.save(os.path.join(upload_folder, filename))
        
        current_user.photo = filename
        db.session.commit()
        
        flash("Club photo updated successfully", "success")
        return redirect(url_for("clu.dashboard"))

    return redirect(url_for("clu.dashboard"))

@clu_bp.route("/create_event", methods=["GET", "POST"])
@login_required
def create_event():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        import os
        from werkzeug.utils import secure_filename
        from datetime import datetime, date

        # Helper: safely convert to int, return None if empty/invalid
        def int_or_none(val):
            try:
                return int(val) if val and str(val).strip() != '' else None
            except (ValueError, TypeError):
                return None

        # --- Date Validation ---
        today = date.today()
        reg_start_date = request.form.get("reg_start_date", "").strip()
        reg_end_date   = request.form.get("reg_end_date", "").strip()
        event_date     = request.form.get("event_date", "").strip()

        try:
            if reg_start_date and datetime.strptime(reg_start_date, "%Y-%m-%d").date() < today:
                flash("❌ Registration Start Date cannot be in the past. Please choose a future date.", "error")
                return redirect(url_for("clu.create_event"))

            if reg_end_date and datetime.strptime(reg_end_date, "%Y-%m-%d").date() < today:
                flash("❌ Registration End Date cannot be in the past. Please choose a future date.", "error")
                return redirect(url_for("clu.create_event"))

            if event_date and datetime.strptime(event_date, "%Y-%m-%d").date() < today:
                flash("❌ Event Date cannot be in the past. Please choose a valid future date.", "error")
                return redirect(url_for("clu.create_event"))

            if reg_end_date and event_date:
                if datetime.strptime(event_date, "%Y-%m-%d").date() < datetime.strptime(reg_end_date, "%Y-%m-%d").date():
                    flash("❌ Event Date must be after the Registration End Date.", "error")
                    return redirect(url_for("clu.create_event"))
        except ValueError:
            flash("❌ Invalid date format. Please use the date picker.", "error")
            return redirect(url_for("clu.create_event"))

        # Handle Payment QR Upload
        payment_qr_filename = None
        if "payment_qr" in request.files:
            file = request.files["payment_qr"]
            if file and file.filename != "":
                payment_qr_filename = secure_filename(f"qr_{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
                upload_folder = os.path.join(current_app.root_path, "static", "uploads", "payments")
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, payment_qr_filename))

        # Handle Poster Upload
        poster_filename = None
        if "poster" in request.files:
            file = request.files["poster"]
            if file and file.filename != "":
                poster_filename = secure_filename(f"poster_{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
                upload_folder = os.path.join(current_app.root_path, "static", "uploads", "events")
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, poster_filename))

        from models import Event
        event_data = {
            "title":            request.form.get("title"),
            "club_name":        request.form.get("club_name"),
            "category":         request.form.get("category"),
            "category_number":  int_or_none(request.form.get("category_number")),
            "description":      request.form.get("description"),
            "reg_start_date":   reg_start_date or None,
            "reg_end_date":     reg_end_date or None,
            "event_date":       event_date or None,
            "fee":              request.form.get("fee"),
            "event_type":       request.form.get("event_type"),
            "team_size":        int_or_none(request.form.get("team_size")),
            "no_of_teams":      int_or_none(request.form.get("no_of_teams")),
            "max_participants": int_or_none(request.form.get("max_participants")),
            "whatsapp_link":    request.form.get("whatsapp_link"),
            "google_form_link": request.form.get("google_form_link"),
            "payment_qr":       payment_qr_filename,
            "poster":           poster_filename,
            "approver_1":       request.form.get("approver_1"),
            "approver_2":       request.form.get("approver_2"),
            "created_by":       current_user.id,
            "created_at":       datetime.now()
        }

        Event.create_event(event_data)
        flash("✅ Event created successfully and sent for approval!", "success")
        return redirect(url_for("clu.my_events"))

    from models import HodDean
    hods = HodDean.query.all()
    return render_template("clu_create_event.html", hods=hods)

@clu_bp.route("/my_events")
@login_required
def my_events():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
    
    from models import Event
    events = Event.query.filter_by(created_by=current_user.id).all()
    return render_template("clu_my_events.html", events=events)

@clu_bp.route("/participants")
@login_required
def participants():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
        
    event_id = request.args.get("event_id")
    if not event_id:
        from models import Event
        events = Event.query.filter_by(created_by=current_user.id).all()
        return render_template("clu_participants.html", events_list=events, select_mode=True)
    
    from models import Event, Registration, User
    
    event = Event.query.get(int(event_id))
    if not event:
        flash("Event not found", "error")
        return redirect(url_for("clu.my_events"))
        
    registrations = Registration.query.filter_by(event_id=int(event_id)).all()
    
    # Fetch student details for each registration
    students_list = []
    for reg in registrations:
        student = User.query.get(reg.student_id)
        if student:
            student_info = {
                "name": student.name or student.username,
                "register_number": student.username,
                "department": student.department or "N/A",
                "payment_status": reg.payment_status,
                "attendance_status": reg.attendance_status,
                "transaction_id": reg.transaction_id,
                "reg_id": reg.id
            }
            students_list.append(student_info)
            
    return render_template("clu_participants.html", students=students_list, event=event)

@clu_bp.route("/approve_payment/<int:reg_id>", methods=["POST"])
@login_required
def approve_payment(reg_id):
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
        
    from models import Registration, Event, User
    from extensions import db
    
    reg = Registration.query.get_or_404(reg_id)
    event = Event.query.get_or_404(reg.event_id)
    
    # Verify the current coordinator owns this event
    if event.created_by != current_user.id:
        flash("Unauthorized", "error")
        return redirect(url_for("clu.dashboard"))
        
    if reg.payment_status == "Confirmed":
        flash("Registration is already confirmed.", "info")
        return redirect(url_for("clu.participants", event_id=event.id))

    # Check seat availability again before confirming
    if event.available_seats is not None and event.available_seats <= 0:
        flash("Error: Cannot confirm. Event is already full!", "error")
        return redirect(url_for("clu.participants", event_id=event.id))

    reg.payment_status = "Confirmed"
    if event.available_seats is not None:
        event.available_seats -= 1
    db.session.commit()
    
    # Send confirmation email
    student = User.query.get(reg.student_id)
    if student and student.email:
        send_registration_confirmation_email(student.email, student.name or student.username, event.title)
    
    flash("Payment approved. Student registration is now confirmed and email sent.", "success")
    return redirect(url_for("clu.participants", event_id=event.id))


@clu_bp.route("/mark_present_manual/<int:reg_id>", methods=["POST"])
@login_required
def mark_present_manual(reg_id):
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
        
    from models import Registration, Event, AttendanceLog
    from extensions import db
    from datetime import datetime
    
    reg = Registration.query.get_or_404(reg_id)
    event = Event.query.get_or_404(reg.event_id)
    
    if event.created_by != current_user.id:
        flash("Unauthorized", "error")
        return redirect(url_for("clu.my_events"))
        
    if reg.attendance_status != "Present":
        # Mark registration as present
        reg.attendance_status = "Present"
        
        # Log attendance in AttendanceLog if not exists
        existing_log = AttendanceLog.query.filter_by(event_id=event.id, student_id=reg.student_id).first()
        if not existing_log:
            new_log = AttendanceLog(
                event_id=event.id,
                student_id=reg.student_id,
                marked_by=current_user.id,
                timestamp=datetime.now()
            )
            db.session.add(new_log)
            
        db.session.commit()
        flash("Attendance marked as Present.", "success")
    else:
        flash("Student is already marked Present.", "info")
        
    return redirect(url_for("clu.participants", event_id=event.id))


@clu_bp.route("/attendance_scanner")
@login_required
def attendance_scanner():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
    
    from models import Event
    # Get active events for this club to scan for
    events = Event.query.filter_by(created_by=current_user.id, approval_status="Approved").all()
    return render_template("clu_attendance_scanner.html", events=events)

@clu_bp.route("/mark_attendance", methods=["POST"])
@login_required
def mark_attendance():
    if current_user.role != "clu":
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json()
    qr_data = data.get("qr_data") # Format: STUDENT:id|REG:reg
    event_id = data.get("event_id")
    
    if not qr_data or not event_id:
        return jsonify({"error": "Missing data"}), 400
        
    from models import Event
    event = Event.query.get(event_id)
    if not event or event.created_by != current_user.id:
        return jsonify({"error": "Unauthorized or Invalid Event"}), 403
        
    try:
        # Parse QR data
        parts = qr_data.split("|")
        student_id = parts[0].replace("STUDENT:", "")
        
        from models import Registration, AttendanceLog, User
        from extensions import db
        from datetime import datetime
        
        # Check if student is registered for this event
        registration = Registration.query.filter_by(
            event_id=int(event_id),
            student_id=int(student_id)
        ).first()
        
        if not registration:
            return jsonify({"error": "Student not registered for this event"}), 404
            
        if registration.attendance_status == "Present":
            return jsonify({"error": "Attendance already marked"}), 400
            
        # Mark attendance
        registration.attendance_status = "Present"
        
        # Add to dedicated attendance logs
        log = AttendanceLog(
            event_id=int(event_id),
            student_id=int(student_id),
            marked_by=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        
        student = User.query.get(int(student_id))
        student_name = student.name or student.username
        
        return jsonify({
            "success": True, 
            "message": f"Attendance marked for {student_name}",
            "student_name": student_name
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clu_bp.route("/upload_certificates", methods=["GET", "POST"])
@login_required
def upload_certificates():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
    
    from models import Event, User, Certificate
    from extensions import db
    
    events = Event.query.filter_by(created_by=current_user.id, approval_status="Approved").all()

    if request.method == "POST":
        event_id = request.form.get("event_id")
        if not event_id:
            flash("Please select an event", "error")
            return redirect(url_for("clu.upload_certificates"))
            
        files = request.files.getlist("certificates")
        if not files or not files[0].filename:
            flash("No files uploaded", "error")
            return redirect(url_for("clu.upload_certificates"))
            
        import os
        from werkzeug.utils import secure_filename
        
        success_count = 0
        error_count = 0
        
        upload_folder = os.path.join(current_app.root_path, "static", "uploads", "certificates", event_id)
        os.makedirs(upload_folder, exist_ok=True)
        
        for file in files:
            filename = secure_filename(file.filename)
            reg_number = os.path.splitext(filename)[0].strip()
            
            # Verify if student exists
            student = User.query.filter_by(username=reg_number, role="stu").first()
            if student:
                # Save file
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # Update or insert certificate record
                cert = Certificate.query.filter_by(event_id=int(event_id), student_id=student.id).first()
                if not cert:
                    cert = Certificate(event_id=int(event_id), student_id=student.id)
                    db.session.add(cert)
                
                cert.filename = filename
                cert.file_path = f"static/uploads/certificates/{event_id}/{filename}"
                cert.register_number = reg_number
                db.session.commit()
                
                success_count += 1
            else:
                error_count += 1
                
        flash(f"Upload complete: {success_count} success, {error_count} failed mapping.", "info")
        return redirect(url_for("clu.upload_certificates"))

    return render_template("clu_upload_certificates.html", events=events)

@clu_bp.route("/recruitment", methods=["GET", "POST"])
@login_required
def recruitment():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
    
    from models import Recruitment
    from datetime import datetime
    
    if request.method == "POST":
        import os
        from werkzeug.utils import secure_filename
        
        poster_filename = None
        if "poster" in request.files:
            file = request.files["poster"]
            if file and file.filename != "":
                poster_filename = secure_filename(f"recruit_{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
                upload_folder = os.path.join(current_app.root_path, "static", "uploads", "recruitment")
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, poster_filename))

        data = {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "eligibility": request.form.get("eligibility"),
            "positions": int(request.form.get("positions", 0)),
            "deadline": request.form.get("deadline"),
            "google_form_link": request.form.get("google_form_link"),
            "whatsapp_link": request.form.get("whatsapp_link"),
            "poster": poster_filename,
            "created_by": current_user.id
        }
        Recruitment.create_post(data)
        flash("Recruitment post created successfully!", "success")
        return redirect(url_for("clu.recruitment"))

    posts = Recruitment.query.filter_by(created_by=current_user.id).all()
    return render_template("clu_recruitment.html", posts=posts)

@clu_bp.route("/helpers", methods=["GET", "POST"])
@login_required
def helpers():
    if current_user.role != "clu":
        return redirect(url_for("auth.login"))
    
    from models import HelperRequirement
    from datetime import datetime
    
    if request.method == "POST":
        import os
        from werkzeug.utils import secure_filename
        from datetime import datetime

        poster_filename = None
        if "poster" in request.files:
            file = request.files["poster"]
            if file and file.filename != "":
                poster_filename = secure_filename(f"helper_{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
                upload_folder = os.path.join(current_app.root_path, "static", "uploads", "helpers")
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, poster_filename))

        data = {
            "event_name": request.form.get("event_name"),
            "role": request.form.get("role"),
            "num_required": int(request.form.get("num_required", 0)),
            "deadline": request.form.get("deadline"),
            "whatsapp_link": request.form.get("whatsapp_link"),
            "poster": poster_filename,
            "created_by": current_user.id
        }
        HelperRequirement.create_requirement(data)
        flash("Helper requirement posted successfully!", "success")
        return redirect(url_for("clu.helpers"))

    requirements = HelperRequirement.query.filter_by(created_by=current_user.id).all()
    return render_template("clu_helpers.html", requirements=requirements)

@clu_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("clu.login"))
