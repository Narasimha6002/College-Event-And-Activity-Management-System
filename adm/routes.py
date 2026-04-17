import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import Admin, Club, Coordinator, HodDean, User
from extensions import db, bcrypt
from werkzeug.utils import secure_filename
from datetime import datetime

adm_bp = Blueprint("adm", __name__, template_folder="templates")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@adm_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and isinstance(current_user, Admin):
        return redirect(url_for("adm.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = Admin.verify_password(username, password)
        if user:
            login_user(user)
            return redirect(url_for("adm.dashboard"))
        
        flash("Invalid username or password", "error")

    return render_template("adm_login.html")

@adm_bp.route("/dashboard")
@login_required
def dashboard():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    stats = {
        'clubs': Club.query.count(),
        'coordinators': Coordinator.query.count(),
        'hods': HodDean.query.count(),
        'students': User.query.filter_by(role='stu').count()
    }
    return render_template("adm_dashboard.html", stats=stats)

@adm_bp.route("/manage_clubs", methods=["GET", "POST"])
@login_required
def manage_clubs():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    if request.method == "POST":
        name = request.form.get("club_name")
        desc = request.form.get("description")
        logo = request.files.get("club_logo")
        
        filename = None
        if logo and allowed_file(logo.filename):
            filename = secure_filename(f"{int(datetime.now().timestamp())}_{logo.filename}")
            upload_path = os.path.join('static', 'uploads', 'clubs')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            logo.save(os.path.join(upload_path, filename))
        
        new_club = Club(club_name=name, description=desc, club_logo=filename)
        db.session.add(new_club)
        db.session.commit()
        flash("Club created successfully!", "success")
        return redirect(url_for("adm.manage_clubs"))

    clubs = Club.query.all()
    return render_template("adm_clubs.html", clubs=clubs)

@adm_bp.route("/delete_club/<int:club_id>")
@login_required
def delete_club(club_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    club = Club.query.get_or_404(club_id)
    db.session.delete(club)
    db.session.commit()
    flash("Club deleted.", "info")
    return redirect(url_for("adm.manage_clubs"))

@adm_bp.route("/create-accounts")
@login_required
def create_accounts():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    return render_template("adm_create_accounts.html")

@adm_bp.route("/create_coordinator", methods=["GET", "POST"])
@login_required
def create_coordinator():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        club_name = request.form.get("club_name")
        
        if Coordinator.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
        else:
            Coordinator.create_coordinator(username, password, name, club_name)
            flash("Coordinator account created!", "success")
            return redirect(url_for("adm.dashboard"))

    clubs = Club.query.all()
    return render_template("adm_create_coordinator.html", clubs=clubs)

@adm_bp.route("/create_hod", methods=["GET", "POST"])
@login_required
def create_hod():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        dept = request.form.get("department")
        role = request.form.get("role")
        
        if HodDean.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
        else:
            HodDean.create_hod(username, password, name, dept, role)
            flash("HOD/Dean account created!", "success")
            return redirect(url_for("adm.dashboard"))

    return render_template("adm_create_hod.html")

@adm_bp.route("/manage_users")
@login_required
def manage_users():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    # Combined user list with normalized fields
    all_users = []
    
    # 1. Students
    for s in User.query.filter_by(role='stu').all():
        all_users.append({
            'id': s.id,
            'type': 'stu',
            'category': 'Student',
            'name': s.name,
            'username': s.username,
            'email': s.email,
            'status': s.status,
            'extra': f"Reg: {s.reg_no}" if hasattr(s, 'reg_no') else ""
        })
    
    # 2. Coordinators
    for c in Coordinator.query.all():
        all_users.append({
            'id': c.id,
            'type': 'cl',
            'category': 'Club Head',
            'name': c.name,
            'username': c.username,
            'email': '-',
            'status': c.status,
            'extra': f"Club: {c.club_name}"
        })
        
    # 3. HODs / Deans
    for h in HodDean.query.all():
        all_users.append({
            'id': h.id,
            'type': 'hd',
            'category': h.role if h.role else 'Academic Official',
            'name': h.name,
            'username': h.username,
            'email': '-',
            'status': 'active', # HODs always active in this model
            'extra': f"Dept: {h.department}"
        })
    
    return render_template("adm_users.html", users=all_users)

@adm_bp.route("/view_user/<string:user_type>/<int:user_id>")
@login_required
def view_user(user_type, user_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    user_data = None
    if user_type == 'stu':
        user = User.query.get(user_id)
        if user:
            user_data = {'name': user.name, 'username': user.username, 'role': 'Student', 'email': user.email, 'status': user.status}
    elif user_type == 'cl':
        user = Coordinator.query.get(user_id)
        if user:
            user_data = {'name': user.name, 'username': user.username, 'role': 'Club Head', 'club': user.club_name, 'status': user.status}
    elif user_type == 'hd':
        user = HodDean.query.get(user_id)
        if user:
            user_data = {'name': user.name, 'username': user.username, 'role': user.role, 'dept': user.department}
            
    if not user_data:
        flash("User not found.", "error")
        return redirect(url_for("adm.manage_users"))
        
    return render_template("adm_view_user.html", user=user_data, user_type=user_type, user_id=user_id)

@adm_bp.route("/change_password/<string:user_type>/<int:user_id>", methods=["GET", "POST"])
@login_required
def change_password(user_type, user_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
        
    user = None
    if user_type == 'stu': user = User.query.get(user_id)
    elif user_type == 'cl': user = Coordinator.query.get(user_id)
    elif user_type == 'hd': user = HodDean.query.get(user_id)
    
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("adm.manage_users"))

    if request.method == "POST":
        new_password = request.form.get("password")
        if not new_password:
            flash("Password cannot be empty.", "error")
        else:
            user.set_password(new_password)
            db.session.commit()
            flash(f"Password updated successfully for {user.name}!", "success")
            return redirect(url_for("adm.manage_users"))
            
    return render_template("adm_change_password.html", user=user, user_type=user_type)

@adm_bp.route("/toggle_user_status/<string:user_type>/<int:user_id>")
@login_required
def toggle_user_status(user_type, user_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    user = None
    if user_type == 'stu':
        user = User.query.get(user_id)
    elif user_type == 'cl':
        user = Coordinator.query.get(user_id)
    
    if user and hasattr(user, 'status'):
        user.status = 'inactive' if user.status == 'active' else 'active'
        db.session.commit()
        flash(f"User status updated.", "success")
    
    return redirect(url_for("adm.manage_users"))

@adm_bp.route("/delete_user/<string:user_type>/<int:user_id>")
@login_required
def delete_user(user_type, user_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    user = None
    if user_type == 'stu': user = User.query.get(user_id)
    elif user_type == 'cl': user = Coordinator.query.get(user_id)
    elif user_type == 'hd': user = HodDean.query.get(user_id)
    
    if user:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted.", "info")
    
    return redirect(url_for("adm.manage_users"))

@adm_bp.route("/events")
@login_required
def events_overview():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    from models import Event, Registration
    from sqlalchemy import func

    # Fetch all events with participant and revenue data
    events = Event.query.order_by(Event.created_at.desc()).all()

    event_data = []
    total_revenue = 0.0
    total_participants = 0

    for event in events:
        reg_count = Registration.query.filter_by(event_id=event.id).count()
        confirmed = Registration.query.filter_by(event_id=event.id, payment_status='Confirmed').count()
        revenue_result = db.session.query(func.sum(Registration.amount)).filter_by(
            event_id=event.id, payment_status='Confirmed'
        ).scalar() or 0.0

        total_revenue += revenue_result
        total_participants += reg_count

        event_data.append({
            'event': event,
            'participants': reg_count,
            'confirmed_payments': confirmed,
            'revenue': revenue_result,
        })

    summary = {
        'total': len(events),
        'approved': Event.query.filter_by(approval_status='Approved').count(),
        'pending': Event.query.filter_by(approval_status='Pending Approval').count(),
        'rejected': Event.query.filter_by(approval_status='Rejected').count(),
        'total_participants': total_participants,
        'total_revenue': total_revenue,
    }

    return render_template("adm_events.html", event_data=event_data, summary=summary)

@adm_bp.route("/export_events_report")
@login_required
def export_events_report():
    if not isinstance(current_user, Admin):
        return redirect(url_for("adm.login"))
    
    import csv
    import io
    from flask import make_response
    from models import Event, Registration
    from sqlalchemy import func

    # Fetch all events
    events = Event.query.order_by(Event.created_at.desc()).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Event Title', 'Club', 'Category', 'Date', 'Status', 'Participants', 'Confirmed Payments', 'Revenue (₹)'])
    
    for event in events:
        reg_count = Registration.query.filter_by(event_id=event.id).count()
        confirmed = Registration.query.filter_by(event_id=event.id, payment_status='Confirmed').count()
        revenue = db.session.query(func.sum(Registration.amount)).filter_by(
            event_id=event.id, payment_status='Confirmed'
        ).scalar() or 0.0
        
        writer.writerow([
            event.title,
            event.club_name,
            event.category,
            event.event_date,
            event.approval_status,
            reg_count,
            confirmed,
            f"{revenue:.2f}"
        ])

    output.seek(0)
    
    # Create response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=event_report_{timestamp}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

@adm_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("adm.login"))
