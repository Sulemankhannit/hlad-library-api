import smtplib
import ssl
from email.message import EmailMessage
from sqlmodel import Session
from app.db.session import engine
from app.models.user import LibraryUser
from app.core.config import settings

def send_email(user_id: str, subject: str, html_content: str):
    """
    Connects to an external SMTP server via TLS to dispatch a live email.
    Maintains its own isolated database session to prevent thread crashes.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return

    
    with Session(engine) as session:  # we need a sperate specific session for the bgtasks,as it runs sepratley
        user = session.get(LibraryUser, user_id)
        if not user:
            print(f"error: User {user_id} not found.")
            return
        
        target_email = user.email

   
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"HLAD Library <{settings.SMTP_USER}>"
    msg['To'] = target_email
    
    # We set the content as HTML so we can use bolding, colors, and links
    msg.set_content(html_content, subtype='html')

    #  Create a secure TLS context
    context = ssl.create_default_context()

    try:
        #  Open the socket with a STRICT 10-second timeout guardrail
        print(f"Initiating TLS handshake with {settings.SMTP_HOST}...")
        
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=10) as server:
            
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        print(f"Email successfully sent to {target_email}")

    except smtplib.SMTPException as e:
       
        print(f"SMTP Protocol Error: {str(e)}")
    except TimeoutError:
       
        print(f"Network Timeout: Gmail servers did not respond.")
    except Exception as e:
        
        print(f"System Error: {str(e)}")