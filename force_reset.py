from app import app
from models import User, Admin, Coordinator, HodDean
from extensions import db, bcrypt

def force_reset_demo_passwords():
    with app.app_context():
        print("Force resetting demo account passwords...")

        # Helper to ensure specific user exists and has a specific password
        def ensure_user(model, username, password, email=None, **kwargs):
            # Check by username
            user = model.query.filter_by(username=username).first()
            
            # Check if email is taken by ANOTHER user
            if email:
                email_user = model.query.filter_by(email=email).first()
                if email_user and email_user.username != username:
                    print(f"  Warning: Email {email} is used by {email_user.username}. Deleting conflicting user.")
                    db.session.delete(email_user)
                    db.session.commit()

            if user:
                user.set_password(password)
                for k, v in kwargs.items():
                    setattr(user, k, v)
                if email:
                    user.email = email
                print(f"  {model.__name__} '{username}' password reset to '{password}'")
            else:
                if model == Admin:
                    Admin.create_admin(username, password, kwargs.get('name', 'Admin'))
                elif model == HodDean:
                    HodDean.create_hod(username, password, kwargs.get('name', 'HOD'), kwargs.get('department', 'General'), kwargs.get('role', 'HOD'))
                elif model == Coordinator:
                    Coordinator.create_coordinator(username, password, kwargs.get('name', 'Coordinator'), kwargs.get('club_name', 'General'))
                elif model == User:
                    role = kwargs.pop('role', 'stu')
                    User.create_user(username, password, role, email=email, **kwargs)
                print(f"  {model.__name__} '{username}' created with password '{password}'")

        # 1. Admin
        ensure_user(Admin, "admin", "admin123", name="System Administrator")

        # 2. Student
        ensure_user(User, "student", "student123", email="student@example.com", name="Test Student", role="stu")

        # 3. Club
        from models import Club
        c = Club.query.filter_by(club_name="Tech Innovations").first()
        if not c:
            c = Club(club_name="Tech Innovations", description="Demo Club")
            db.session.add(c)
            db.session.commit()
        
        ensure_user(Coordinator, "club", "club123", name="Club Head", club_name="Tech Innovations")
        ensure_user(User, "club", "club123", email="club@example.com", role="clu", club_name="Tech Innovations")

        # 4. HOD
        ensure_user(HodDean, "hod", "hod123", name="Dr. Pavan Kumar", department="CSE", role="HOD")

        db.session.commit()
        print("\nAll demo passwords have been synchronized.")

if __name__ == "__main__":
    force_reset_demo_passwords()
