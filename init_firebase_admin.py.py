import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase
def init_firebase()
    try
        cred = credentials.Certificate(firebase_service_account.json)
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e
        print(fError {e})
        return None

def create_admin_user(db)
    Create initial admin user if not exists.
    admin_username = admin
    admin_ref = db.collection('users').document(admin_username)
    
    if not admin_ref.get().exists()
        admin_data = {
            full_name Administrator,
            email admin@litmusq.com,
            phone ,
            username admin_username,
            password admin123,  # Change this in production!
            is_approved True,
            role admin,
            created_at datetime.now().isoformat(),
            last_login None,
            is_active True
        }
        admin_ref.set(admin_data)
        print(✅ Admin user created successfully!)
        print(fUsername {admin_username})
        print(Password admin123)
    else
        print(✅ Admin user already exists)

if __name__ == __main__
    db = init_firebase()
    if db
        create_admin_user(db)