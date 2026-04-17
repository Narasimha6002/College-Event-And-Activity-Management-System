from app import app
from extensions import db
from models import Event, Registration

def delete_event_cascade(title):
    with app.app_context():
        event = Event.query.filter_by(title=title).first()
        if event:
            # Delete registrations first
            Registration.query.filter_by(event_id=event.id).delete()
            # Delete event
            db.session.delete(event)
            db.session.commit()
            print(f"Event '{title}' and its registrations deleted successfully.")
        else:
            print(f"Event '{title}' not found.")

if __name__ == "__main__":
    delete_event_cascade("ALGORITHMIS")
