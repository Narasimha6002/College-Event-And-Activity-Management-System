from flask_login import UserMixin
from extensions import db, login_manager, bcrypt
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('ad_'):
        try:
            return Admin.query.get(int(user_id.replace('ad_', '')))
        except:
            return None
    elif user_id.startswith('cl_'):
        try:
            return Coordinator.query.get(int(user_id.replace('cl_', '')))
        except:
            return None
    elif user_id.startswith('hd_'):
        try:
            return HodDean.query.get(int(user_id.replace('hd_', '')))
        except:
            return None
    elif user_id.startswith('st_'):
        try:
            return User.query.get(int(user_id.replace('st_', '')))
        except:
            return None
    # Fallback for old sessions
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    
    # Extended Student Fields
    register_number = db.Column(db.String(80), unique=True, nullable=True)
    name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    year = db.Column(db.String(10))
    dob = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    whatsapp = db.Column(db.String(100))
    photo = db.Column(db.String(200))
    qr_code_path = db.Column(db.String(200))
    ee_credits = db.Column(db.Integer, default=0)
    group2_credits = db.Column(db.Integer, default=0)
    group3_credits = db.Column(db.Integer, default=0)
    
    # Club fields
    club_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default="active") # active/inactive

    def get_id(self):
        return f"st_{self.id}"

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    @staticmethod
    def create_user(username, password, role, email=None, **kwargs):
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(username=username, password=hashed_password, role=role, email=email, **kwargs)
        db.session.add(user)
        db.session.commit()
        return user.id

    @staticmethod
    def verify_password(identifier, password):
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        if user and bcrypt.check_password_hash(user.password, password):
            return user
        return None

    @staticmethod
    def find_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def update_password(user_id, new_password):
        user = User.query.get(int(user_id))
        if user:
            user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
            db.session.commit()

    @staticmethod
    def update_qr_path(user_id, qr_path):
        user = User.query.get(int(user_id))
        if user:
            user.qr_code_path = qr_path
            db.session.commit()

    @staticmethod
    def update_credits(user_id, ee, g2, g3):
        user = User.query.get(int(user_id))
        if user:
            user.ee_credits = int(ee)
            user.group2_credits = int(g2)
            user.group3_credits = int(g3)
            db.session.commit()

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    club_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    category_number = db.Column(db.Integer)
    description = db.Column(db.Text)
    reg_start_date = db.Column(db.String(50))
    reg_end_date = db.Column(db.String(50))
    event_date = db.Column(db.String(50))
    fee = db.Column(db.String(50))
    event_type = db.Column(db.String(50))
    team_size = db.Column(db.Integer)
    no_of_teams = db.Column(db.Integer)
    max_participants = db.Column(db.Integer)
    whatsapp_link = db.Column(db.String(200))
    google_form_link = db.Column(db.String(200))
    payment_qr = db.Column(db.String(200))
    poster = db.Column(db.String(200))
    approver_1 = db.Column(db.String(100))
    approver_2 = db.Column(db.String(100))
    approval_status = db.Column(db.String(50), default="Pending Approval")
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    available_seats = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create_event(data):
        if 'available_seats' not in data and 'max_participants' in data:
            data['available_seats'] = data['max_participants']
        event = Event(**data)
        db.session.add(event)
        db.session.commit()
        return event

class Recruitment(db.Model):
    __tablename__ = 'recruitment'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    eligibility = db.Column(db.String(200))
    positions = db.Column(db.Integer)
    deadline = db.Column(db.String(50))
    google_form_link = db.Column(db.String(200))
    whatsapp_link = db.Column(db.String(200))
    poster = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create_post(data):
        post = Recruitment(**data)
        db.session.add(post)
        db.session.commit()
        return post

class HelperRequirement(db.Model):
    __tablename__ = 'helper_requirements'
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(200))
    role = db.Column(db.Text)
    num_required = db.Column(db.Integer)
    deadline = db.Column(db.String(50))
    whatsapp_link = db.Column(db.String(200))
    poster = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create_requirement(data):
        req = HelperRequirement(**data)
        db.session.add(req)
        db.session.commit()
        return req

class Registration(db.Model):
    __tablename__ = 'registrations'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    amount = db.Column(db.Float, default=0.0)
    transaction_id = db.Column(db.String(100), unique=True, nullable=True)
    payment_status = db.Column(db.String(50), default="Pending")
    attendance_status = db.Column(db.String(50), default="Absent")
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def register(event_id, student_id, payment_status="Pending"):
        reg = Registration(event_id=event_id, student_id=student_id, payment_status=payment_status)
        db.session.add(reg)
        db.session.commit()
        return reg

class Certificate(db.Model):
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(200))
    file_path = db.Column(db.String(200))
    register_number = db.Column(db.String(50))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class AttendanceLog(db.Model):
    __tablename__ = 'attendance_logs'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class HodDean(db.Model, UserMixin):
    __tablename__ = 'hod_dean'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    role = db.Column(db.String(50)) # e.g., 'HOD', 'Dean'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return f"hd_{self.id}"

    @staticmethod
    def verify_password(username, password):
        user = HodDean.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            return user
        return None

    @staticmethod
    def create_hod(username, password, name, department, role='HOD'):
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        hod = HodDean(username=username, password=hashed, name=name, department=department, role=role)
        db.session.add(hod)
        db.session.commit()
        return hod

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

class Admin(db.Model, UserMixin):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default="adm")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return f"ad_{self.id}"

    @staticmethod
    def verify_password(username, password):
        user = Admin.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            return user
        return None

    @staticmethod
    def create_admin(username, password, name):
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        adm = Admin(username=username, password=hashed, name=name)
        db.session.add(adm)
        db.session.commit()
        return adm

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

class Club(db.Model):
    __tablename__ = 'clubs'
    id = db.Column(db.Integer, primary_key=True)
    club_name = db.Column(db.String(100), unique=True, nullable=False)
    club_logo = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Coordinator(db.Model, UserMixin):
    __tablename__ = 'coordinators'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    club_name = db.Column(db.String(100))
    role = db.Column(db.String(20), default="clu")
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return f"cl_{self.id}"

    @staticmethod
    def verify_password(username, password):
        user = Coordinator.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            return user
        return None

    @staticmethod
    def create_coordinator(username, password, name, club_name):
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        cl = Coordinator(username=username, password=hashed, name=name, club_name=club_name)
        db.session.add(cl)
        db.session.commit()
        return cl

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
