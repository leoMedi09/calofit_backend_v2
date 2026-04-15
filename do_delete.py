import sys
from app.core.database import SessionLocal
from app.models.client import Client
from app.core.firebase import auth as firebase_admin_auth

db = SessionLocal()
email = "leonardojosemedinaflores0902@gmail.com"
client = db.query(Client).filter(Client.email == email).first()
if client:
    db.delete(client)
    db.commit()
    print("✅ BD OK")
else:
    print("ℹ️ BD No existe")

try:
    fb_user = firebase_admin_auth.get_user_by_email(email)
    firebase_admin_auth.delete_user(fb_user.uid)
    print("✅ FB OK")
except Exception as e:
    print(f"ℹ️ FB: {e}")
