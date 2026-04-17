import random
from flask_mail import Message
from extensions import mail


def generate_otp():
    """
    Generates a 6-digit OTP
    """
    return str(random.randint(100000, 999999))


def send_otp_email(recipient_email, otp_code):
    """
    Sends OTP email to the user
    """

    msg = Message(
        subject="CEAM - Email Verification OTP",
        recipients=[recipient_email]
    )

    msg.body = f"""
Hello,

Your OTP for the College Event & Activity Management System is:

{otp_code}

This OTP will expire in 10 minutes.

If you did not request this, please ignore this email.

Regards,
CEAM Team
"""

    try:
        mail.send(msg)
        print(f"OTP email sent to {recipient_email}")
        return True

    except Exception as e:
        print("\n" + "="*50)
        print("!!! REAL EMAIL FAILED (Bad Credentials or SMTP Issue) !!!")
        print(f"Error: {e}")
        print(f"FOR TESTING, USE THIS OTP -> {otp_code}")
        print(f"Target Email: {recipient_email}")
        print("="*50 + "\n")
        
        # Return True for local testing fallback so user is not blocked
        return True


def send_event_status_email(recipient_email, event_title, status):
    """
    Notifies the coordinator when their event is approved or rejected
    """
    msg = Message(
        subject=f"CEAM - Event Approval Status: {status}",
        recipients=[recipient_email]
    )

    status_message = "approved! It is now visible to students on their dashboard." if status.lower() == "approved" else f"rejected. Status: {status}"

    msg.body = f"""
Hello,

Your event "{event_title}" has been {status_message}

Regards,
CEAM Team
"""

    try:
        mail.send(msg)
        print(f"Status email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send status email: {e}")
        return False


def send_registration_confirmation_email(recipient_email, student_name, event_title):
    """
    Sends registration confirmation email to the student
    """
    msg = Message(
        subject=f"CEAM - Registration Confirmed: {event_title}",
        recipients=[recipient_email]
    )

    msg.body = f"""
Hello {student_name},

Success! Your registration for the event "{event_title}" has been confirmed.

We are excited to have you join us. Please check the event details in your dashboard for the venue and timing.

Regards,
CEAM Team
"""

    try:
        mail.send(msg)
        print(f"Confirmation email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        return False


def send_event_reminder_email(recipient_email, student_name, event_title, event_date):
    """
    Notifies the student about an upcoming event
    """
    msg = Message(
        subject=f"CEAM Reminder: {event_title} is Tomorrow!",
        recipients=[recipient_email]
    )

    msg.body = f"""
Hello {student_name},

This is a reminder that the event "{event_title}" you registered for is happening tomorrow, {event_date}.

Don't forget to check the event details and venue!

Regards,
CEAM Team
"""

    try:
        mail.send(msg)
        print(f"Reminder email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send reminder email: {e}")
        return False