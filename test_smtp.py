import smtplib
from dotenv import load_dotenv
import os

load_dotenv()
try:
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
    server.starttls()
    server.login(os.getenv("SENDER_EMAIL"), os.getenv("SENDER_PASSWORD"))
    
    # Send a tiny test email
    msg = "Subject: Test\n\nThis is a test email."
    server.sendmail(os.getenv("SENDER_EMAIL"), os.getenv("RECIPIENT_EMAIL"), msg)
    server.quit()
    print("Test email sent successfully via SMTP.")
except Exception as e:
    print(f"SMTP Error: {e}")
