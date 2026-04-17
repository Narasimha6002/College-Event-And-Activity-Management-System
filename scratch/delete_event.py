from app import app
from extensions import db
from models import Event

def delete_event(title):
    with app.app_context():
        event = Event.query.filter_by(title=title).first()
        if event:
            db.session.delete(event)
            db.session.commit()
            print(f"Event '{title}' deleted successfully.")
        else:
            print(f"Event '{title}' not found.")

if __name__ == "__main__":
    delete_event("ALGORITHMIS")
