import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import json
from streamlit_autorefresh import st_autorefresh
import psutil
from functools import lru_cache
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore
import json

# =============================
# Configuration & Theme
# =============================
QUESTION_DATA_FOLDER = "Question_Data_Folder"
LOGIN_FILE_PATH = "login/admin_login_details.xlsx"  # Keep for backward compatibility
EDITOR_LOGIN_FILE_PATH = "login/editor_login_details.xlsx"  # Add this line
USER_PROGRESS_FOLDER = "user_progress"
FORMATTED_QUESTIONS_FILE = "formatted_questions.json"

# Admin users will be loaded from Excel file, not hardcoded
ADMIN_USERS = []  # Will be populated from Excel file
EDITOR_USERS = []  # Add this line - Will be populated from Excel file

# =============================
# Add performance config
# =============================
class PerformanceConfig:
    MAX_MEMORY_MB = 500
    CLEANUP_INTERVAL_MINUTES = 5
    MAX_QUESTIONS_PER_LOAD = 200

# =============================
# Firebase Configuration
# =============================
def initialize_firebase():
    """Initialize Firebase connection."""
    try:
        if not firebase_admin._apps:
            # Read from Streamlit secrets
            firebase_config = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            # Note: No databaseURL needed for Firestore
        return firestore.client()
    except Exception as e:
        st.error(f"❌ Firebase initialization failed: {e}")
        return None

# Initialize Firebase
db = initialize_firebase()

# LitmusQ Color Theme
LITMUSQ_THEME = {
    "primary": "#1E3A8A",      # Dark blue
    "secondary": "#DC2626",    # Red
    "accent": "#3B82F6",       # Light blue
    "background": "#F8FAFC",
    "text": "#1E293B",
    "success": "#059669",      # Green for correct answers
    "warning": "#D97706",      # Amber for warnings
    "light_bg": "#EFF6FF"      # Light blue background
}

# =============================
# Custom CSS Injection
# =============================
def inject_metric_mobile_css():
    st.markdown("""
    <style>
    /* MOBILE-ONLY: shrink metric text */
    @media (max-width: 480px) {

        /* Metric title (label) */
        div[data-testid="metric-container"] > label {
            font-size: 0.70rem !important;   /* smaller title */
        }

        /* Metric value */
        div[data-testid="metric-container"] > div {
            font-size: 1.0rem !important;    /* smaller numbers */
            padding: 0 !important;
        }

        /* Metric delta (if any) */
        div[data-testid="metric-container"] span {
            font-size: 0.65rem !important;
        }

        /* Reduce column padding */
        .st-emotion-cache-1y4p8pa, .st-emotion-cache-16txtl3 {
            padding-left: 0.3rem !important;
            padding-right: 0.3rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

inject_metric_mobile_css()

def inject_mobile_css():
    st.markdown("""
    <style>
    /* Reduce padding for mobile */
    @media (max-width: 480px) {
        .block-container {
            padding: 0.8rem 0.5rem !important;
        }

        /* Reduce large headers */
        h1, h2, h3, .stMarkdown h1 {
            font-size: 1.35rem !important;
        }

        /* Columns should stack naturally */
        .css-1kyxreq { flex-direction: column !important; }

        /* Cards spacing */
        .achievement-card {
            padding: 0.6rem !important;
        }

        /* Reduce metric font sizes */
        div[data-testid="metric-container"] > label {
            font-size: 0.8rem !important;
        }
        div[data-testid="metric-container"] > div {
            font-size: 1rem !important;
        }

        /* Make test history buttons bigger for touch */
        button[kind="primary"] {
            padding: 0.35rem 0.4rem !important;
            font-size: 0.85rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

inject_mobile_css()

def inject_custom_css():
    st.markdown(f"""
    <style>

    /* =========================================================
       GLOBAL SAFE SPACING (NO OVERLAPS, NO HUGE MARGINS)
    ==========================================================*/

    /* Main content container – prevents header overlap */
    .block-container {{
        padding-top: 0.1rem !important;   /* header clearance */
        padding-left: 1.5rem !important;
        padding-right: 0.5rem !important;
        padding-bottom: 0.1rem !important;
    }}

    /* Vertical spacing between Streamlit elements */
    .stElementContainer {{
        margin-top: 0.1rem !important;
        margin-bottom: 0.2rem !important;
        padding: 0 !important;
    }}

    /* prevent widget crowding */
    .stMarkdown, .stRadio, .stButton, .stSelectbox,
    .stNumberInput, .stTextInput, .stTextArea, .stFileUploader {{
        margin-top: 0rem !important;
        margin-bottom: 0rem !important;
    }}

    /* fix vertical block spacing safely */
    .stVerticalBlock {{
        margin: 0.1rem 0 !important;
        padding: 0 !important;
        gap: 0.1rem !important;
    }}

    /* headings */
    h1, h2, h3, h4, h5, h6 {{
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
        padding: 0 !important;
    }}

    /* markdown inner spacing */
    .stMarkdown p,
    .stMarkdown ul,
    .stMarkdown ol,
    .stMarkdown li {{
        margin: 0.2rem 0 !important;
        padding-left: 10px;
    }}

    /* horizontal rule */
    hr {{
        margin: 0.5rem 0 !important;
    }}



    /* =========================================================
       RADIO BUTTONS (FULL WIDTH + THEME COLORS)
    ==========================================================*/

    .stRadio > div {{
        padding: 0rem !important;
        width: 100% !important;
    }}

    .stRadio > div > label {{
        width: 100% !important;
        margin: 0rem 0 !important;
        padding: 0rem !important;
        transition: all 0.2s ease;
        border: 5px solid transparent !important;
    }}


    /* =========================================================
       PRIMARY BUTTONS
    ==========================================================*/

    .stButton > button {{
        background-color: {LITMUSQ_THEME['primary']};
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.2rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.25s ease !important;
    }}

    .stButton > button:hover {{
        background-color: {LITMUSQ_THEME['accent']};
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }}



    /* =========================================================
       SECONDARY BUTTONS
    ==========================================================*/

    .secondary-button > button {{
        background-color: {LITMUSQ_THEME['light_bg']};
        color: {LITMUSQ_THEME['primary']};
        border: 2px solid {LITMUSQ_THEME['primary']};
        border-radius: 8px;
        padding: 0.2rem 1rem;
        font-weight: 500;
    }}



    /* =========================================================
       DANGER BUTTONS
    ==========================================================*/

    .danger-button > button {{
        background-color: {LITMUSQ_THEME['secondary']};
        color: white !important;
        border-radius: 8px;
        padding: 0.2rem 1rem;
        font-weight: 500;
        border: none !important;
    }}

    .danger-button > button:hover {{
        background-color: #b91c1c !important;
    }}



    /* =========================================================
       EXPANDERS – THEME COLORED
    ==========================================================*/

    .streamlit-expanderHeader {{
        background-color: {LITMUSQ_THEME['light_bg']} !important;
        border: 1px solid {LITMUSQ_THEME['primary']} !important;
        border-radius: 8px !important;
        padding: 0.9rem !important;
        font-weight: 600 !important;
        color: {LITMUSQ_THEME['primary']} !important;
        margin-bottom: 0.5rem !important;
    }}

    .streamlit-expanderHeader:hover {{
        background-color: {LITMUSQ_THEME['accent']}22 !important;
        border-color: {LITMUSQ_THEME['accent']} !important;
    }}

    .streamlit-expanderContent {{
        background-color: {LITMUSQ_THEME['background']};
        border: 1px solid #E2E8F0;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        padding: 1rem !important;
    }}



    /* =========================================================
       CUSTOM HEADER
    ==========================================================*/

    .litmusq-header {{
        background: linear-gradient(
            135deg,
            {LITMUSQ_THEME['primary']},
            {LITMUSQ_THEME['secondary']}
        );
        color: white;
        padding: 0.2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }}



    /* =========================================================
       QUESTION CARD
    ==========================================================*/

    .question-card {{
        background-color: {LITMUSQ_THEME['light_bg']};
        padding: 1.3rem;
        border-radius: 12px;
        border-left: 4px solid {LITMUSQ_THEME['primary']};
        margin: 0.8rem 0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }}



    /* =========================================================
       BADGE ELEMENT
    ==========================================================*/

    .badge {{
        display: inline-block;
        padding: 0.3rem 0.8rem;
        background-color: {LITMUSQ_THEME['accent']};
        color: white;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 0.1rem;
    }}



    /* =========================================================
       FORMATTED CONTENT
    ==========================================================*/

    .formatted-content {{
        line-height: 1.6;
        margin: 0.5rem 0;
    }}

    .formatted-content b {{
        color: {LITMUSQ_THEME['primary']};
    }}

    .formatted-content i {{
        color: {LITMUSQ_THEME['secondary']};
    }}

    .formatted-content u {{
        color: {LITMUSQ_THEME['accent']};
        text-decoration: underline !important;
    }}



    /* =========================================================
       MOBILE OPTIMIZATION
    ==========================================================*/

    @media (max-width: 768px) {{
        .stRadio > div {{
            padding: 0.6rem !important;
        }}

        .stRadio > div > label {{
            padding: 0.4rem !important;
        }}

        .question-card {{
            padding: 1rem !important;
        }}
    }}
    
    </style>
    """, unsafe_allow_html=True)

# =============================
# Firebase User Management Functions
# =============================

def register_user(full_name, email, phone, username, password):
    """Register a new user in Firebase."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return False
        
        # 🔒 1. Check admin Excel usernames
        admin_credentials = load_admin_credentials()
        if username in admin_credentials:
            st.error("❌ Username already exists (admin user). Please choose a different username.")
            return False
        
        # 🔒 2. Check editor Excel usernames
        editor_credentials = load_editor_credentials()
        if username in editor_credentials:
            st.error("❌ Username already exists (editor user). Please choose a different username.")
            return False
        
        # 🔒 3. Check Firebase for duplicate username
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', username).limit(1).get()
        
        if len(query) > 0:
            st.error("❌ Username already exists. Please choose a different one.")
            return False
        
        # 🔒 4. Check Firebase for duplicate email
        email_query = users_ref.where('email', '==', email).limit(1).get()
        if len(email_query) > 0:
            st.error("❌ Email already registered. Please use a different email.")
            return False
        
        # Create new user document
        user_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "username": username,
            "password": password,
            "is_approved": False,     
            "role": "student",  # Default role for registered users
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "is_active": True
        }
        
        users_ref.document(username).set(user_data)
        
        initialize_user_progress(username)
        
        return True
        
    except Exception as e:
        st.error(f"Registration failed: {e}")
        return False

def authenticate_user_all(username, password):
    """Authenticate user against either admin (Excel) or regular users (Firebase)."""
    # First check if it's an admin user (from Excel)
    admin_credentials = load_admin_credentials()
    if username in admin_credentials:
        if admin_credentials[username] == password:
            return True, "success", "admin"  # Excel = Admin
        else:
            return False, "Invalid password", None
    
    # Then check if it's an editor user (from Excel)
    editor_credentials = load_editor_credentials()
    if username in editor_credentials:
        if editor_credentials[username] == password:
            return True, "success", "editor"  # Excel = Editor
        else:
            return False, "Invalid password", None
    
    # If not admin or editor, check regular users in Firebase
    auth_success, message = authenticate_user_firebase(username, password)
    if auth_success:
        return True, "success", "regular"  # Firebase = Regular
    else:
        return False, message, None
        
def authenticate_user_firebase(username, password):
    """Authenticate regular user against Firebase with approval check."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return False, "System error"
        
        # Get user document
        user_ref = db.collection('users').document(username)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return False, "Invalid username or password"
        
        user_data = user_doc.to_dict()
        
        # Check if user is approved
        if not user_data.get('is_approved', False):
            return False, "Account pending admin approval"
        
        # Check if user is active
        if not user_data.get('is_active', True):
            return False, "Account disabled"
        
        # Check password
        if user_data.get('password') == password:
            # Update last login
            user_ref.update({"last_login": datetime.now().isoformat()})
            return True, "success"
        else:
            return False, "Invalid password"
            
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, "System error"

def get_all_users():
    """Get all registered users from Firebase with role information."""
    try:
        if db is None:
            return []
        
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        users = []
        admin_credentials = load_admin_credentials()
        editor_credentials = load_editor_credentials()
        
        for doc in docs:
            user_data = doc.to_dict()
            username = doc.id
            
            # Determine user type/role
            if username in admin_credentials:
                user_data['user_type'] = 'admin'
                user_data['role'] = 'admin'
                user_data['is_approved'] = True  # Admins are auto-approved
            elif username in editor_credentials:
                user_data['user_type'] = 'editor'
                user_data['role'] = 'editor'
                user_data['is_approved'] = True  # Editors are auto-approved
            else:
                # Firebase users default to student unless specified otherwise
                user_data['user_type'] = 'regular'
                user_data['role'] = user_data.get('role', 'student')
            
            user_data['id'] = username
            users.append(user_data)
        
        return users
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []

def update_user_status(username, is_active):
    """Update user active status."""
    try:
        if db is None:
            return False
        
        # Check if user is an admin or editor (from Excel)
        admin_credentials = load_admin_credentials()
        editor_credentials = load_editor_credentials()
        
        if username in admin_credentials or username in editor_credentials:
            st.error("Cannot modify admin or editor users")
            return False
        
        user_ref = db.collection('users').document(username)
        user_ref.update({
            "is_active": is_active,
            "updated_at": datetime.now().isoformat()
        })
        return True
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return False

def delete_user(username):
    """Delete a user from the system."""
    try:
        if db is None:
            return False
        
        # Check if user is an admin (from Excel)
        admin_credentials = load_admin_credentials()
        if username in admin_credentials:
            st.error("Cannot delete admin users")
            return False
        
        # Check if user is an editor (from Excel)
        editor_credentials = load_editor_credentials()
        if username in editor_credentials:
            st.error("Cannot delete editor users")
            return False
        
        user_ref = db.collection('users').document(username)
        user_ref.delete()
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False

def update_user_approval(username, is_approved):
    """Update user approval status."""
    try:
        if db is None:
            return False
        
        # Check if user is an admin (from Excel)
        admin_credentials = load_admin_credentials()
        if username in admin_credentials:
            st.error("Cannot modify admin users")
            return False
        
        # Check if user is an editor (from Excel)
        editor_credentials = load_editor_credentials()
        if username in editor_credentials:
            st.error("Cannot modify editor users")
            return False
        
        user_ref = db.collection('users').document(username)
        user_ref.update({
            "is_approved": is_approved,
            "updated_at": datetime.now().isoformat()
        })
        return True
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return False

def load_admin_credentials():
    """Load admin username and password from Excel file."""
    try:
        df = pd.read_excel(LOGIN_FILE_PATH, engine="openpyxl")
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        if "username" not in df.columns or "password" not in df.columns:
            st.error("Login file must contain 'Username' and 'Password' columns")
            return {}
        
        admin_credentials = {}
        for _, row in df.iterrows():
            username = str(row["username"]).strip()
            password = str(row["password"]).strip()
            if username and password:
                admin_credentials[username] = password
                
        # Update global ADMIN_USERS list
        global ADMIN_USERS
        ADMIN_USERS = list(admin_credentials.keys())
        
        return admin_credentials
    except Exception as e:
        st.error(f"Failed to load admin credentials: {e}")
        return {}

# Add this new function for editor credentials
def load_editor_credentials():
    """Load editor username and password from Excel file."""
    try:
        if not os.path.exists(EDITOR_LOGIN_FILE_PATH):
            st.error(f"Editor login file not found at {EDITOR_LOGIN_FILE_PATH}")
            return {}
            
        df = pd.read_excel(EDITOR_LOGIN_FILE_PATH, engine="openpyxl")
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        if "username" not in df.columns or "password" not in df.columns:
            st.error("Editor login file must contain 'Username' and 'Password' columns")
            return {}
        
        editor_credentials = {}
        for _, row in df.iterrows():
            username = str(row["username"]).strip()
            password = str(row["password"]).strip()
            if username and password:
                editor_credentials[username] = password
                
        # Update global EDITOR_USERS list
        global EDITOR_USERS
        EDITOR_USERS = list(editor_credentials.keys())
        
        return editor_credentials
    except Exception as e:
        st.error(f"Failed to load editor credentials: {e}")
        return {}
        
        
# =============================
# Firebase Formatted Questions Functions
# =============================
@lru_cache(maxsize=1)
def load_formatted_questions_cached():
    """Cached version of load_formatted_questions."""
    return load_formatted_questions()

def load_formatted_questions():
    """Load formatted questions from Firebase."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return {}
        
        # Try to load from Firebase
        doc_ref = db.collection('formatted_questions').document('all_questions')
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            # Check if local file exists as backup
            if os.path.exists(FORMATTED_QUESTIONS_FILE):
                with open(FORMATTED_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Upload to Firebase for future use
                    save_formatted_questions(data)
                    return data
    except Exception as e:
        st.error(f"Error loading formatted questions: {e}")
    return {}

def save_formatted_questions(formatted_data):
    """Save formatted questions to Firebase."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return False
        
        # Save to Firebase
        doc_ref = db.collection('formatted_questions').document('all_questions')
        doc_ref.set(formatted_data)
        
        # Also save locally as backup
        with open(FORMATTED_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, indent=2, ensure_ascii=False)
            
        return True
    except Exception as e:
        st.error(f"Error saving formatted questions: {e}")
        return False
    
# =============================
# Branded Header
# =============================
def show_litmusq_header(subtitle="Professional MCQ Assessment Platform"):
    st.markdown(f"""
    <div class="litmusq-header" style="text-align: center;">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">🧪 LitmusQ</h1>
        <p style="margin: 0; opacity: 0.9; font-size: 1.2rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# =============================
# Authentication Helpers
# =============================
def load_login_credentials():
    """Load username and password from Excel file."""
    try:
        df = pd.read_excel(LOGIN_FILE_PATH, engine="openpyxl")
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        if "username" not in df.columns or "password" not in df.columns:
            st.error("Login file must contain 'Username' and 'Password' columns")
            return {}
        
        credentials = {}
        for _, row in df.iterrows():
            username = str(row["username"]).strip()
            password = str(row["password"]).strip()
            if username and password:
                credentials[username] = password
                
        return credentials
    except Exception as e:
        st.error(f"Failed to load login credentials: {e}")
        return {}

def authenticate_user(username, password, credentials):
    return credentials.get(username) == password


def show_login_screen():
    """Enhanced login screen with LitmusQ branding and registration."""
    st.markdown("<div style='margin-top: 4rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("Assess Better. Learn Faster.")
    
    # Load admin credentials once at login screen
    admin_credentials = load_admin_credentials()
    
    # Add temporary CSS fix for login screen
    st.markdown("""
    <style>
    div[data-testid="stAppViewContainer"] {
        padding-top: 0rem !important;
    }
    .litmusq-header {
        margin-top: 0rem !important;
        padding-top: 1rem !important;
    }
    .registration-form {
        background: linear-gradient(135deg, #f8fafc, #e2e8f0);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create tabs for Login and Registration
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        # Login form
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")
            submit_button = st.form_submit_button("🚀 Login to LitmusQ", use_container_width=True)
            
            if submit_button:
                if not username or not password:
                    st.error("Please enter both username and password")
                    return False
                    
                # Authenticate user (checks both admin and regular users)
                auth_success, message, user_type = authenticate_user_all(username, password)
                
                if auth_success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_type = user_type  # Set based on authentication source
                    
                    # Initialize user progress for regular users only
                    if user_type == "regular":
                        initialize_user_progress(username)
                        st.success(f"✅ Welcome back, {username}!")
                    elif user_type == "admin":
                        st.success(f"✅ Welcome, Admin {username}!")
                    
                    st.rerun()
                else:
                    if message == "Account pending admin approval":
                        st.warning("⏳ Your account is pending admin approval. Please contact the administrator.")
                    elif message == "Account disabled":
                        st.error("❌ Your account has been disabled. Please contact the administrator.")
                    else:
                        st.error(f"❌ {message}")
                    return False
    
    with tab2:
        # Registration form
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("👤 Full Name", placeholder="Enter your full name")
                email = st.text_input("📧 Email Address", placeholder="Enter your email")
                phone = st.text_input("📱 Phone Number", placeholder="Enter your phone number")
            
            with col2:
                username = st.text_input("👤 Username", placeholder="Choose a username")
                password = st.text_input("🔒 Password", type="password", placeholder="Choose a password")
                confirm_password = st.text_input("✅ Confirm Password", type="password", placeholder="Confirm your password")
            
            # Terms and conditions
            agree_terms = st.checkbox("I agree to the Terms and Conditions")
            
            register_button = st.form_submit_button("📝 Register Account", use_container_width=True, type="secondary")
            
            if register_button:
                # Validate inputs
                if not all([full_name, email, username, password, confirm_password]):
                    st.error("Please fill in all required fields")
                    return False
                
                if password != confirm_password:
                    st.error("Passwords do not match")
                    return False
                
                if len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                    return False
                
                if not agree_terms:
                    st.error("You must agree to the Terms and Conditions")
                    return False
                
                # Email validation
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email):
                    st.error("Please enter a valid email address")
                    return False
                
                # Phone validation (optional)
                if phone and not phone.replace('+', '').replace(' ', '').isdigit():
                    st.warning("Phone number should contain only digits and optional + sign")
                
                success = register_user(full_name, email, phone, username, password)

                if success:
                    # Clear registration fields
                    for key in ["full_name", "email", "phone", "reg_username", "reg_password", "reg_confirm"]:
                        st.session_state[key] = ""

                    st.info("User Created. You will be able to log in once your account is approved by admin.")
                
                    st.stop()   # <-- VERY IMPORTANT: prevents form rerun and keeps messages visible
                    
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col2:
        st.markdown(
            "<div style='text-align: center; color: #64748B;'>"
            "🧪 LitmusQ v1.0 • Secure MCQ Test Platform"
            "</div>", 
            unsafe_allow_html=True
        )
    
    return False
    
def is_admin_user():
    """Check if current user is admin based on session state."""
    # Check user_type in session state (set during authentication)
    user_type = st.session_state.get('user_type')
    return user_type == 'admin'

def is_editor_user():
    """Check if current user is editor based on session state."""
    # Check user_type in session state (set during authentication)
    user_type = st.session_state.get('user_type')
    return user_type == 'editor'

def is_admin_or_editor():
    """Check if current user is admin or editor."""
    user_type = st.session_state.get('user_type')
    return user_type in ['admin', 'editor']
    
def show_admin_panel():
    """Admin panel for managing users."""
    st.markdown("<div style='margin-top: 3.5rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("Admin Dashboard")
    
    # Check if user is admin
    if not is_admin_user():
        st.error("❌ Access Denied. This section is only available for administrators.")
        st.info("Please contact your system administrator if you need access.")
        return
    
    # Initialize subtab state
    if 'admin_subtab' not in st.session_state:
        st.session_state.admin_subtab = "users"
    
    # Create subtabs
    subtab1, subtab2, subtab3 = st.tabs(["👥 User Management", "📈 Analytics", "🛠️Settings"])
    
    with subtab1:
        show_user_management()
    
    with subtab2:
        show_admin_analytics()
    
    with subtab3:
        show_system_settings()

def show_user_management():
    """Display and manage all registered users."""

    # Get all users
    users = get_all_users()
    
    if not users:
        st.info("No users found in the system.")
        return
    
    # Convert to DataFrame for display
    user_list = []
    for user in users:
        # Get role from user data (already populated in get_all_users)
        role = user.get('role', 'student')
        user_type = user.get('user_type', 'regular')
        
        user_list.append({
            "Username": user.get('username', ''),
            "Full Name": user.get('full_name', ''),
            "Email": user.get('email', ''),
            "Phone": user.get('phone', ''),
            "Approved": user.get('is_approved', False),
            "Active": user.get('is_active', True),
            "Role": role,  # Use role from user data
            "User Type": user_type,  # Add user type column
            "Created": user.get('created_at', ''),
            "Last Login": user.get('last_login', 'Never')
        })
    
    df = pd.DataFrame(user_list)
    
    # Display statistics
    total_users = len(users)
    approved_users = sum(1 for user in users if user.get('is_approved', False))
    active_users = sum(1 for user in users if user.get('is_active', True))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", total_users)
    with col2:
        st.metric("Approved Users", approved_users)
    with col3:
        st.metric("Active Users", active_users)
    with col4:
        st.metric("Pending Approval", total_users - approved_users)
    
    st.markdown("---")
    
    # Search and filter
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("🔍 Search users", placeholder="Search by name, username, or email")
    with col2:
        filter_approved = st.selectbox("Approval Status", ["All", "Approved", "Pending"])
    with col3:
        filter_active = st.selectbox("Active Status", ["All", "Active", "Inactive"])
    
    # Apply filters
    if search_term:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
    
    if filter_approved == "Approved":
        df = df[df["Approved"] == True]
    elif filter_approved == "Pending":
        df = df[df["Approved"] == False]
    
    if filter_active == "Active":
        df = df[df["Active"] == True]
    elif filter_active == "Inactive":
        df = df[df["Active"] == False]
    
    # Display user table
    st.markdown(f"📋 User List ({len(df)} users)")
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    
    # Create a container for the table
    table_container = st.container()
    
    with table_container:
        # Display each user in an editable card
        for idx, row in df.iterrows():
            with st.expander(f"👤 {row['Full Name']} ({row['Username']})", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Full Name:** {row['Full Name']}")
                    st.markdown(f"**Email:** {row['Email']}")
                    st.markdown(f"**Phone:** {row['Phone']}")
                    st.markdown(f"**Role:** {row['Role']}")
                
                with col2:
                    st.markdown(f"**Created:** {row['Created'][:10] if row['Created'] else 'N/A'}")
                    # Check if the value is a string before trying to slice it, otherwise display 'Never'
                    last_login_value = row['Last Login']
                    last_login_display = last_login_value[:19] if isinstance(last_login_value, str) else 'Never'
                    st.markdown(f"**Last Login:** {last_login_display}")
                    
                    # Status indicators
                    status_col1, status_col2 = st.columns(2)
                    with status_col1:
                        approval_status = "✅ Approved" if row['Approved'] else "⏳ Pending"
                        st.markdown(f"**Approval:** {approval_status}")
                    
                    with status_col2:
                        active_status = "🟢 Active" if row['Active'] else "🔴 Inactive"
                        st.markdown(f"**Status:** {active_status}")
                
                # Action buttons
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                
                with action_col1:
                    # Toggle approval
                    new_approval = not row['Approved']
                    if st.button("✅ Approve" if not row['Approved'] else "⏸ Revoke", 
                               key=f"approve_{row['Username']}",
                               use_container_width=True):
                        if update_user_approval(row['Username'], new_approval):
                            st.success(f"User {'approved' if new_approval else 'revoked'} successfully!")
                            st.rerun()
                
                with action_col2:
                    # Toggle active status
                    new_active = not row['Active']
                    if st.button("🟢 Activate" if not row['Active'] else "🔴 Deactivate",
                               key=f"active_{row['Username']}",
                               use_container_width=True):
                        if update_user_status(row['Username'], new_active):
                            st.success(f"User {'activated' if new_active else 'deactivated'} successfully!")
                            st.rerun()
                
                with action_col3:
                    # Edit user (placeholder)
                    if st.button("📝 Edit", key=f"edit_{row['Username']}", use_container_width=True):
                        st.info("Edit functionality coming soon!")
                
                with action_col4:
                    # Delete user (with confirmation)
                    if st.button("🗑️ Delete", key=f"delete_{row['Username']}", use_container_width=True):
                        st.session_state.user_to_delete = row['Username']
                        st.rerun()
                
                # Handle deletion confirmation
                if hasattr(st.session_state, 'user_to_delete') and st.session_state.user_to_delete == row['Username']:
                    st.warning(f"⚠️ Are you sure you want to delete user {row['Username']}?")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("✅ Yes, Delete", key=f"confirm_delete_{row['Username']}"):
                            if delete_user(row['Username']):
                                st.success("User deleted successfully!")
                                del st.session_state.user_to_delete
                                st.rerun()
                    with confirm_col2:
                        if st.button("❌ Cancel", key=f"cancel_delete_{row['Username']}"):
                            del st.session_state.user_to_delete
                            st.rerun()
    
    # Bulk actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve All Pending", use_container_width=True):
            pending_users = [user for user in users if not user.get('is_approved', False)]
            for user in pending_users:
                update_user_approval(user['username'], True)
            st.success(f"Approved {len(pending_users)} pending users!")
            st.rerun()
    
    with col2:
        if st.button("📧 Export User List", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="litmusq_users.csv",
                mime="text/csv"
            )
            
def show_admin_analytics():
    """Display admin analytics dashboard."""
    st.markdown("📈 **User Analytics**")
    
    users = get_all_users()
    
    if not users:
        st.info("No user data available.")
        return
    
    # Calculate statistics
    total_users = len(users)
    approved_users = sum(1 for user in users if user.get('is_approved', False))
    active_users = sum(1 for user in users if user.get('is_active', True))
    
    # Registration trend (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_users = sum(1 for user in users 
                      if datetime.fromisoformat(user.get('created_at', '2000-01-01')) > thirty_days_ago)
    
    # Reduce st.metric font size
    st.markdown("""
        <style>
            /* Metric label */
            div[data-testid="stMetricLabel"] > label {
                font-size: 0.8rem !important;
            }
            /* Metric value */
            div[data-testid="stMetricValue"] {
                font-size: 1rem !important;
            }
            /* Delta text */
            div[data-testid="stMetricDelta"] {
                font-size: 0.7rem !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", total_users)
    with col2:
        st.metric("Approval Rate", f"{(approved_users/total_users*100):.1f}%")
    with col3:
        st.metric("Active Users", active_users)
    with col4:
        st.metric("Recent Registrations (30d)", recent_users)

    
    # User registration timeline
    st.markdown("**📅 Registration Timeline**")
    st.markdown("<br>", unsafe_allow_html=True)
    # Group by date
    reg_dates = {}
    for user in users:
        created_date = user.get('created_at', '')[:10]  # Get YYYY-MM-DD
        if created_date:
            reg_dates[created_date] = reg_dates.get(created_date, 0) + 1
    
    if reg_dates:
        dates = sorted(reg_dates.keys())[-30:]  # Last 30 days
        counts = [reg_dates[d] for d in dates]
        
        # Create a simple bar chart
        chart_data = pd.DataFrame({
            'Date': dates,
            'Registrations': counts
        })
        st.bar_chart(chart_data.set_index('Date'))
    

def show_system_settings():
    """System settings for admin."""
    with st.form("system_settings"):
        # Email notifications
        enable_emails = st.checkbox("Enable email notifications", value=True)
        admin_email = st.text_input("Admin Email", placeholder="admin@example.com")
        
        # User settings
        auto_approve = st.checkbox("Auto-approve new users", value=False)
        require_email_verification = st.checkbox("Require email verification", value=False)
        max_login_attempts = st.number_input("Max login attempts before lockout", min_value=1, max_value=10, value=3)
        
        # Security settings
        session_timeout = st.number_input("Session timeout (minutes)", min_value=5, max_value=240, value=60)
        password_min_length = st.number_input("Minimum password length", min_value=6, max_value=20, value=8)
        require_special_char = st.checkbox("Require special characters in password", value=True)
        
        # Save button
        if st.form_submit_button("💾 Save Settings", use_container_width=True):
            st.success("Settings saved successfully!")
            # Note: In production, save these to Firebase
            
def get_question_key(file_path, sheet_name, question_index, field="question"):
    """Generate a unique key for each question/option."""
    return f"{file_path}::{sheet_name}::{question_index}::{field}"

def render_formatted_content(content):
    """Render formatted content with HTML/CSS styling."""
    if not content or not isinstance(content, str):
        return content or ""
    
    # If content contains HTML tags, render as HTML
    if any(tag in content for tag in ['<b>', '<strong>', '<i>', '<em>', '<u>', '<br>', '<span', '<div', '<p>']):
        return st.markdown(f'<div class="formatted-content">{content}</div>', unsafe_allow_html=True)
    else:
        return st.write(content)



def show_question_editor():
    """Admin interface for editing question formatting."""
    st.markdown("<div style='margin-top: 3.5rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("📝 Question Editor")
    
    # Check if user is admin OR editor
    if not is_admin_or_editor():  # Changed from is_admin_user()
        st.error("❌ Access Denied. This section is only available for administrators and editors.")
        st.info("Please contact your system administrator if you need access.")
        return
    
    # Load existing formatted questions
    formatted_questions = load_formatted_questions()
    
    # Folder selection
    folder_structure = st.session_state.get('folder_structure', {})
    
    if not folder_structure:
        st.error("No question banks found. Please ensure Question_Data_Folder exists.")
        return
    
    # Get current path - MUST BE DEFINED BEFORE USING IT
    current_path = st.session_state.get('editor_current_path', [])
    
    # Display current location breadcrumb
    if current_path:
        breadcrumb = "Home > " + " > ".join(current_path)
    else:
        breadcrumb = "Home"
    
    st.write(f"**📍:** `{breadcrumb}`") 
    st.markdown("<div style='margin-top: 0.2;'></div>", unsafe_allow_html=True)


    # Add back navigation - MOVED HERE AFTER current_path is defined

    if st.button("⬅️ Back", use_container_width=True, key="editor_back"):
            st.session_state.editor_current_path = current_path[:-1]
            st.rerun()
    
    # Remove the else part so no disabled button appears
    # (nothing is shown when at root)
    
    if st.button("🏠 Back to Root", use_container_width=True, key="back_to_root"):
        st.session_state.editor_current_path = []
        st.rerun()
    
    
    # Display folder navigation for editor
    def get_current_level(structure, path):
        """Get the current level in folder structure based on path."""
        current_level = structure
        for folder in path:
            if folder in current_level:
                current_level = current_level[folder]
            else:
                return None
        return current_level
    
    current_level = get_current_level(folder_structure, current_path)
    
    if current_level is None:
        st.error("Invalid path in folder structure")
        st.session_state.editor_current_path = []
        st.rerun()
        return
    
    # Display items at current level
    items_displayed = 0
    
    # Display folders first
    for item_name, item_content in current_level.items():
        if item_name == '_files':
            continue
            
        # Check if it's a folder (has sub-items that aren't _files)
        is_folder = any(k != '_files' for k in item_content.keys())
        has_qb = '_files' in item_content and 'QB.xlsx' in item_content['_files']
        
        button_label = f"{item_name}"
        if st.button(
            button_label, 
            key=f"editor_nav_{len(current_path)}_{item_name}",
            use_container_width=True,
            help=f"Click to {'open question bank' if has_qb else 'explore folder'}"
        ):
            st.session_state.editor_current_path = current_path + [item_name]
            st.rerun()
        items_displayed += 1
    
    # Show content if current path has a QB
    if current_path:
        has_qb = '_files' in current_level and 'QB.xlsx' in current_level['_files']
        
        if has_qb:
            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
            st.markdown("📝 **Question Bank Editor**")
            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
            qb_path = os.path.join(QUESTION_DATA_FOLDER, *current_path, 'QB.xlsx')
            if os.path.exists(qb_path):
                questions_data = load_questions(qb_path)
                
                if questions_data:
                    # Sheet selection
                    sheet_names = list(questions_data.keys())
                    selected_sheet = st.selectbox("Select Question Paper", sheet_names, key="editor_sheet")
                    
                    if selected_sheet:
                        df = questions_data[selected_sheet]
                        
                        if len(df) > 0:
                            # Question selection
                            question_indices = list(range(len(df)))
                            selected_index = st.selectbox(
                                "Select Question", 
                                question_indices,
                                format_func=lambda x: f"Question {x+1}: {df.iloc[x]['Question'][:100]}..."
                            )
                            
                            if selected_index is not None:
                                show_question_editing_interface(
                                    df.iloc[selected_index], 
                                    selected_index,
                                    qb_path,
                                    selected_sheet,
                                    formatted_questions
                                )
                        else:
                            st.warning("No questions found in this sheet.")
                else:
                    st.error("Failed to load question bank data.")
            else:
                st.error(f"Question bank file not found: {qb_path}")
        elif items_displayed == 0:
            st.info("This folder is empty.")
    else:
        if items_displayed == 0:
            st.info("No question banks or folders found in the root directory.")
        
def show_question_editing_interface(question_row, question_index, file_path, sheet_name, formatted_questions):
    """Show editing interface for a specific question."""
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    st.markdown(f"✏️ **Editing Question {question_index + 1}**")
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    
    # Store original content in session state for reliable access
    session_key = f"original_{file_path}_{sheet_name}_{question_index}"
    if session_key not in st.session_state:
        st.session_state[session_key] = {
            "question": question_row['Question'],
            "option_a": question_row.get('Option A', ''),
            "option_b": question_row.get('Option B', ''),
            "option_c": question_row.get('Option C', ''),
            "option_d": question_row.get('Option D', ''),
            "explanation": question_row.get('Explanation', '')
        }
    
    original_content = st.session_state[session_key]
    
    # Display original question for reference
    with st.expander("👀 Original Question (Read-only)", expanded=False):
        st.write(f"**Question:** {original_content['question']}")
        st.write(f"**Option A:** {original_content['option_a']}")
        st.write(f"**Option B:** {original_content['option_b']}")
        st.write(f"**Option C:** {original_content['option_c']}")
        st.write(f"**Option D:** {original_content['option_d']}")
        if original_content['explanation']:
            st.write(f"**Explanation:** {original_content['explanation']}")
    
    # Generate keys for this question
    question_key = get_question_key(file_path, sheet_name, question_index, "question")
    option_a_key = get_question_key(file_path, sheet_name, question_index, "option_a")
    option_b_key = get_question_key(file_path, sheet_name, question_index, "option_b")
    option_c_key = get_question_key(file_path, sheet_name, question_index, "option_c")
    option_d_key = get_question_key(file_path, sheet_name, question_index, "option_d")
    explanation_key = get_question_key(file_path, sheet_name, question_index, "explanation")
    
    # Load existing formatted content
    default_question = formatted_questions.get(question_key, original_content['question'])
    default_a = formatted_questions.get(option_a_key, original_content['option_a'])
    default_b = formatted_questions.get(option_b_key, original_content['option_b'])
    default_c = formatted_questions.get(option_c_key, original_content['option_c'])
    default_d = formatted_questions.get(option_d_key, original_content['option_d'])
    default_explanation = formatted_questions.get(explanation_key, original_content['explanation'])
    
    # Formatting guide
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    with st.expander("📋 Formatting Guide", expanded=False):
        st.markdown("""
        **Supported Formatting:**
        - **Bold:** `<b>text</b>` or `<strong>text</strong>`
        - *Italic:* `<i>text</i>` or `<em>text</em>`
        - <u>Underline:</u> `<u>text</u>`
        - Line breaks: `<br>`
        - Colors: `<span style='color: red;'>text</span>`
        - Font size: `<span style='font-size: 20px;'>text</span>`
        
        **Examples:**
        - `This is <b>bold</b> and <i>italic</i>`
        - `First line<br>Second line`
        - `<span style='color: blue;'>Blue text</span>`
        - `<span style='font-size: 18px; color: red;'>Large red text</span>`
        """)
    
    # Use a form for the editing interface
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    with st.form(f"edit_question_{question_index}"):
        st.markdown("**Edit Content**")
        
        edited_question = st.text_area(
            "**Question Text**",
            value=default_question,
            height=150,
            key=f"q_{question_index}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            edited_a = st.text_area("Option A", value=default_a, height=100, key=f"a_{question_index}")
            edited_b = st.text_area("Option B", value=default_b, height=100, key=f"b_{question_index}")
        with col2:
            edited_c = st.text_area("Option C", value=default_c, height=100, key=f"c_{question_index}")
            edited_d = st.text_area("Option D", value=default_d, height=100, key=f"d_{question_index}")
        
        edited_explanation = st.text_area(
            "Explanation", 
            value=default_explanation, 
            height=150,
            key=f"exp_{question_index}"
        )
        
        # Preview
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("👁️**Live Previe**")
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("**Question:**")
        render_formatted_content(edited_question)
        
        st.markdown("**Options:**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("A)")
            render_formatted_content(edited_a)
            st.markdown("B)")
            render_formatted_content(edited_b)
        with col2:
            st.markdown("C)")
            render_formatted_content(edited_c)
            st.markdown("D)")
            render_formatted_content(edited_d)
        
        if edited_explanation:
            st.markdown("**Explanation:**")
            render_formatted_content(edited_explanation)
        
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        # Create three columns for action buttons INSIDE THE FORM
        save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
        reset_btn = st.form_submit_button("🔁 Reset to Original", use_container_width=True, type="secondary")
        clear_btn = st.form_submit_button("🗑️ Clear Formatting", use_container_width=True, type="secondary")
    
    # Handle button actions after the form
    if save_btn:
        # Save formatted content
        formatted_questions[question_key] = edited_question
        formatted_questions[option_a_key] = edited_a
        formatted_questions[option_b_key] = edited_b
        formatted_questions[option_c_key] = edited_c
        formatted_questions[option_d_key] = edited_d
        formatted_questions[explanation_key] = edited_explanation
        
        if save_formatted_questions(formatted_questions):
            st.success("✅ Changes saved successfully!")
            # Clear cache to force reload
            if 'formatted_questions_cache' in st.session_state:
                del st.session_state.formatted_questions_cache
            # Clear widget state so new defaults appear
            for k in [
                f"q_{question_index}",
                f"a_{question_index}",
                f"b_{question_index}",
                f"c_{question_index}",
                f"d_{question_index}",
                f"exp_{question_index}",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    
    elif reset_btn:
        # Reset to original content
        formatted_questions[question_key] = original_content['question']
        formatted_questions[option_a_key] = original_content['option_a']
        formatted_questions[option_b_key] = original_content['option_b']
        formatted_questions[option_c_key] = original_content['option_c']
        formatted_questions[option_d_key] = original_content['option_d']
        formatted_questions[explanation_key] = original_content['explanation']
        
        if save_formatted_questions(formatted_questions):
            st.success("✅ Reset to original content!")
            # Clear cache to force reload
            if 'formatted_questions_cache' in st.session_state:
                del st.session_state.formatted_questions_cache
            # Clear widget state so new defaults appear
            for k in [
                f"q_{question_index}",
                f"a_{question_index}",
                f"b_{question_index}",
                f"c_{question_index}",
                f"d_{question_index}",
                f"exp_{question_index}",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    
    elif clear_btn:
        # Remove formatting (delete keys from formatted_questions)
        keys_to_delete = []
        for key in [question_key, option_a_key, option_b_key, option_c_key, option_d_key, explanation_key]:
            if key in formatted_questions:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del formatted_questions[key]
        
        if save_formatted_questions(formatted_questions):
            st.success("✅ Formatting cleared!")
            # Clear cache to force reload
            if 'formatted_questions_cache' in st.session_state:
                del st.session_state.formatted_questions_cache
            # Clear widget state so new defaults appear
            for k in [
                f"q_{question_index}",
                f"a_{question_index}",
                f"b_{question_index}",
                f"c_{question_index}",
                f"d_{question_index}",
                f"exp_{question_index}",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

def get_formatted_content(file_path, sheet_name, question_index, field, original_content):
    """Get formatted content if available, otherwise return original."""
    # For retests, we might not have the original file path
    if hasattr(st.session_state, 'is_retest') and st.session_state.is_retest:
        # Try to get from formatted questions cache first
        formatted_questions = load_formatted_questions()
        key = get_question_key(file_path, sheet_name, question_index, field)
        formatted_content = formatted_questions.get(key, original_content)
        
        # If not found in formatted questions, use the original content
        # (which for retests should be the stored question content)
        return formatted_content
    else:
        # Original behavior for non-retests
        formatted_questions = load_formatted_questions()
        key = get_question_key(file_path, sheet_name, question_index, field)
        return formatted_questions.get(key, original_content)

# =============================
# Firebase User Progress & Analytics
# =============================
def get_user_progress_doc_id(username):
    """Get Firebase document ID for user progress."""
    return f"user_{username}"

def initialize_user_progress(username):
    """Initialize user progress data in Firebase."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return
        
        doc_ref = db.collection('user_progress').document(get_user_progress_doc_id(username))
        doc = doc_ref.get()
        
        if not doc.exists:
            default_progress = {
                "username": username,
                "tests_taken": 0,
                "total_score": 0,
                "average_score": 0,
                "test_history": [],
                "achievements": [],
                "weak_areas": [],
                "strong_areas": [],
                "join_date": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            doc_ref.set(default_progress)
            st.success(f"✅ Initialized progress for {username}")
    except Exception as e:
        st.error(f"Error initializing user progress: {e}")

def save_user_progress(username, progress_data):
    """Save user progress to Firebase with proper type conversion."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return False
        
        # Add timestamp
        progress_data["last_updated"] = datetime.now().isoformat()
        
        # Convert numpy types to Python native types before saving to Firestore
        progress_data = convert_numpy_to_python(progress_data)
        
        doc_ref = db.collection('user_progress').document(get_user_progress_doc_id(username))
        doc_ref.set(progress_data, merge=True)
        return True
    except Exception as e:
        st.error(f"Error saving progress: {e}")
        return False

def convert_numpy_to_python(data):
    """Recursively convert numpy types to Python native types for Firestore compatibility."""
    if isinstance(data, dict):
        return {key: convert_numpy_to_python(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_to_python(item) for item in data]
    elif isinstance(data, (np.bool_, np.bool)):
        return bool(data)
    elif isinstance(data, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(data)
    elif isinstance(data, (np.floating, np.float64, np.float32, np.float16)):
        return float(data)
    elif isinstance(data, np.ndarray):
        return convert_numpy_to_python(data.tolist())
    elif hasattr(np, 'string_') and isinstance(data, np.string_):
        # For older versions of NumPy
        return str(data)
    elif hasattr(np, 'bytes_') and isinstance(data, np.bytes_):
        # For NumPy 2.0+
        return data.decode('utf-8') if isinstance(data, bytes) else str(data)
    elif isinstance(data, np.datetime64):
        # Convert numpy datetime64 to ISO string
        return pd.Timestamp(data).isoformat()
    elif pd.isna(data):
        return None
    else:
        return data
        
def ensure_python_types(data):
    """Ensure all data is in Python native types for Firestore compatibility."""
    if isinstance(data, dict):
        return {key: ensure_python_types(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [ensure_python_types(item) for item in data]
    elif isinstance(data, (np.bool_, np.bool)):
        return bool(data)
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    elif isinstance(data, np.ndarray):
        return ensure_python_types(data.tolist())
    elif hasattr(np, 'string_') and isinstance(data, np.string_):
        # For older versions of NumPy
        return str(data)
    elif hasattr(np, 'bytes_') and isinstance(data, np.bytes_):
        # For NumPy 2.0+
        return data.decode('utf-8') if isinstance(data, bytes) else str(data)
    elif pd.isna(data):
        return None
    else:
        return data
        
def load_user_progress(username):
    """Load user progress from Firebase and ensure Python types."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return None
        
        doc_ref = db.collection('user_progress').document(get_user_progress_doc_id(username))
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            # Ensure all data is in Python native types
            return ensure_python_types(data)
    except Exception as e:
        st.error(f"Error loading progress: {e}")
    return None

def clear_user_progress(username):
    """Clear all performance data for the user from Firebase."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return False
        
        doc_ref = db.collection('user_progress').document(get_user_progress_doc_id(username))
        doc = doc_ref.get()
        
        if doc.exists:
            # Reset to default progress instead of deleting
            default_progress = {
                "username": username,
                "tests_taken": 0,
                "total_score": 0,
                "average_score": 0,
                "test_history": [],
                "achievements": [],
                "weak_areas": [],
                "strong_areas": [],
                "join_date": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            doc_ref.set(default_progress)
            st.success("✅ All your performance data has been cleared successfully!")
            return True
        else:
            # Initialize if document doesn't exist
            initialize_user_progress(username)
            st.info("ℹ️ No performance data found to clear.")
            return True
    except Exception as e:
        st.error(f"❌ Error clearing performance data: {e}")
        return False

def update_user_progress(test_results):
    """Update user progress with new test results."""
    username = st.session_state.username
    progress = load_user_progress(username)
    
    if progress:
        # Update basic stats with proper type conversion
        progress["tests_taken"] = int(progress.get("tests_taken", 0)) + 1
        progress["total_score"] = float(progress.get("total_score", 0)) + float(test_results["Marks Obtained"])
        progress["average_score"] = float(progress["total_score"]) / float(progress["tests_taken"])
        
        # Store detailed question data for each test
        if 'detailed_answers' in test_results:
            detailed_answers = test_results['detailed_answers']
        else:
            detailed_answers = []
        
        # Get the actual questions used in this test
        questions_used = []
        df = st.session_state.quiz_questions
        
        for i in range(len(df)):
            row = df.iloc[i]
            questions_used.append({
                "question_index": int(i),
                "question_text": str(row.get('Question', '')),
                "option_a": str(row.get('Option A', '')),
                "option_b": str(row.get('Option B', '')),
                "option_c": str(row.get('Option C', '')),
                "option_d": str(row.get('Option D', '')),
                "correct_option": str(test_results.get('detailed_answers', [{}])[i].get('correct_answer', '') if i < len(test_results.get('detailed_answers', [])) else ''),
                "explanation": str(row.get('Explanation', ''))
            })
        
        # Add to test history with proper types
        test_history_entry = {
            "exam_name": str(test_results["Exam Name"]),
            "date": datetime.now().isoformat(),
            "score": float(test_results["Marks Obtained"]),
            "total_marks": float(test_results["Total Marks"]),
            "percentage": float((test_results["Marks Obtained"] / test_results["Total Marks"]) * 100) if test_results["Total Marks"] > 0 else 0.0,
            "correct_answers": int(test_results["Correct"]),
            "total_questions": int(test_results["Total Questions"]),
            "detailed_answers": detailed_answers,
            "questions_used": questions_used,  # Store the actual questions
            "is_retest": bool(test_results.get("is_retest", False)),
            "original_test_id": test_results.get("original_test_id"),
            "retest_type": test_results.get("retest_type", "full"),  # Store retest type
            "test_id": str(datetime.now().timestamp())
        }
        
        # Ensure test_history exists
        if "test_history" not in progress:
            progress["test_history"] = []
        
        progress["test_history"].append(test_history_entry)
        
        # Update achievements
        update_achievements(progress, test_results)
        
        # Save updated progress
        save_user_progress(username, progress)

def update_achievements(progress, test_results):
    """Update user achievements based on test performance."""
    achievements = progress.get("achievements", [])
    
    # First test achievement
    if progress["tests_taken"] == 1 and "first_test" not in achievements:
        achievements.append("first_test")
    
    # Perfect score achievement
    if (test_results["Marks Obtained"] == test_results["Total Marks"] and 
        "perfect_score" not in achievements):
        achievements.append("perfect_score")
    
    # Speed demon (if time was limited and finished early)
    if (st.session_state.quiz_duration > 0 and 
        st.session_state.end_time and 
        datetime.now() < st.session_state.end_time - timedelta(minutes=5) and
        "speed_demon" not in achievements):
        achievements.append("speed_demon")
    
    progress["achievements"] = achievements

def show_clear_data_section():
    """Show section to clear performance data."""
    st.markdown("---")
    # Confirmation workflow
    if not st.session_state.get('show_clear_confirmation', False):
        if st.button("🚮 Clear All My Performance Data", type="secondary", key="clear_data_init", use_container_width="True"):
            st.session_state.show_clear_confirmation = True
            st.rerun()
    else:
        st.markdown(
            "<p style='color: #d9534f; font-weight: 600;'>⚠️ Are you sure you want to delete ALL your performance data? This action cannot be undone!</p>",
            unsafe_allow_html=True
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ Yes, Delete Everything", type="primary", key="confirm_clear", use_container_width="True"):
                success = clear_user_progress(st.session_state.username)
                st.session_state.show_clear_confirmation = False
                if success:
                    st.rerun()
        with col2:
            if st.button("❌ Cancel", key="cancel_clear", use_container_width="True"):
                st.session_state.show_clear_confirmation = False
                st.rerun()
        st.markdown(
            "<p style='color: #286b33; font-weight: 600;'>Note: Your login credentials will remain unchanged. Only your performance data will be deleted.</p>",
            unsafe_allow_html=True
        )

def show_student_dashboard():
    st.markdown("<div style='margin-top: 3.5rem;'></div>", unsafe_allow_html=True)
    """Display student dashboard with progress analytics."""
    show_litmusq_header("Your Learning Dashboard")
    
    # Home button
    if st.button("🏠 Home", use_container_width=True, key="dashboard_home"):
        st.session_state.current_screen = "home"
        st.rerun()
    
    username = st.session_state.username
    progress = load_user_progress(username)
    
    if not progress:
        st.info("📊 Start taking tests to see your progress analytics!")
        # Show clear data section even if no data exists
        show_clear_data_section()
        return
    
    # Key Metrics - ensure all values are proper Python types
    st.subheader("📈 Performance Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        tests_taken = int(progress.get("tests_taken", 0))
        st.metric("Tests Taken", tests_taken)
    
    with col2:
        avg_score = float(progress.get("average_score", 0))
        st.metric("Average Score", f"{avg_score:.1f}")
    
    with col3:
        test_history = progress.get("test_history", [])
        total_correct = sum(int(entry.get("correct_answers", 0)) for entry in test_history)
        total_questions = sum(int(entry.get("total_questions", 0)) for entry in test_history)
        accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        st.metric("Overall Accuracy", f"{accuracy:.1f}%")
    
    with col4:
        achievements = progress.get("achievements", [])
        if isinstance(achievements, list):
            st.metric("Achievements", len(achievements))
        else:
            st.metric("Achievements", 0)
    
    st.markdown("---")
    
    # Recent Test History
    test_history = progress.get("test_history", [])
    if test_history:
        st.subheader("📋 Recent Tests")
        recent_tests = test_history[-10:]  # Show last 10 tests
        
        for idx, test in enumerate(reversed(recent_tests)):
            test_date = datetime.fromisoformat(str(test.get("date", ""))).strftime("%Y-%m-%d %H:%M")
            percentage = float(test.get("percentage", 0))
            
            # Create columns for layout
            col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 1, 1])
            
            with col1:
                exam_name = str(test.get('exam_name', 'Unknown Test'))
                if test.get('is_retest', False):
                    exam_name += "📝"
                st.write(f"**{exam_name}**")
            
            with col2:
                score = float(test.get('score', 0))
                total_marks = float(test.get('total_marks', 0))
                st.write(f"Score: {score:.0f}/{total_marks:.0f}")
            
            with col3:
                st.write(f"Accuracy: {percentage:.1f}%")
            
            with col4:
                st.write(test_date)
            
            with col5:
                # Take Retest button
                test_id = test.get('test_id', f"test_{idx}")
                if st.button("🔄", key=f"retest_{test_id}", 
                           help="Take Re-Test"):
                    st.session_state.retest_config = test
                    st.session_state.current_screen = "retest_config"
                    st.rerun()
            
            with col6:
                # Delete Entry button
                if st.button("🗑️", key=f"delete_{test_id}", 
                           help="Delete this test entry"):
                    if delete_test_entry(username, test_id):
                        st.success("Test entry deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete test entry")
            
            # Progress bar
            st.progress(int(percentage))

    # Achievements
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    if progress.get("achievements"):
        st.subheader("🏆 Your Achievements")
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        achievement_data = {
            "first_test": {"emoji": "🎯", "name": "First Test", "desc": "Completed your first test"},
            "perfect_score": {"emoji": "🏆", "name": "Perfect Score", "desc": "Scored 100% on a test"},
            "speed_demon": {"emoji": "⚡", "name": "Speed Demon", "desc": "Finished test with 5+ minutes remaining"}
        }
        
        cols = st.columns(3)
        for idx, achievement in enumerate(progress["achievements"]):
            with cols[idx % 3]:
                if achievement in achievement_data:
                    data = achievement_data[achievement]
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: {LITMUSQ_THEME['light_bg']}; 
                                border-radius: 10px; border: 2px solid {LITMUSQ_THEME['primary']};">
                        <div style="font-size: 2rem;">{data['emoji']}</div>
                        <h4>{data['name']}</h4>
                        <p style="font-size: 0.8rem; color: #64748B;">{data['desc']}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Clear Data Section
    show_clear_data_section()

# =============================
# Enhanced Folder Navigation
# =============================
def scan_folder_structure():
    """Scan the Question_Data_Folder and return the folder structure."""
    if not os.path.exists(QUESTION_DATA_FOLDER):
        st.error(f"Question data folder '{QUESTION_DATA_FOLDER}' not found!")
        return {}
    
    folder_structure = {}
    
    for root, dirs, files in os.walk(QUESTION_DATA_FOLDER):
        rel_path = os.path.relpath(root, QUESTION_DATA_FOLDER)
        if rel_path == ".":
            current_level = folder_structure
        else:
            path_parts = rel_path.split(os.sep)
            current_level = folder_structure
            for part in path_parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
        
        for dir_name in dirs:
            current_level[dir_name] = {}
        
        current_level['_files'] = files
    
    return folder_structure

def display_folder_navigation(folder_structure, current_path=None, level=0):
    """Display folder structure as clickable navigation - SIMPLIFIED VERSION."""
    if current_path is None:
        current_path = []
    
    for item_name, item_content in folder_structure.items():
        if item_name == '_files':
            continue
            
        has_children = any(k != '_files' for k in item_content.keys())
        has_qb = '_files' in item_content and 'QB.xlsx' in item_content['_files']
        
        # SIMPLIFIED: Use the same approach as question editor
        button_label = f"{item_name}"
        if has_qb:
            button_label = f"{item_name} 📚"
        
        if st.button(
            button_label, 
            key=f"nav_{'->'.join(current_path + [item_name])}", 
            use_container_width=True,
            help=f"Click to {'open question bank' if has_qb else 'explore folder'}"
        ):
            st.session_state.current_path = current_path + [item_name]
            st.session_state.current_screen = "folder_view"
            st.rerun()
            
def calculate_default_duration(df, time_per_question=1.5):
    """Calculate default exam duration based on number of questions and time per question."""
    # Check for "Time in Minute/Question" in column headers
    time_columns = [col for col in df.columns if "Time in Minute/Question" in str(col)]
    
    if time_columns:
        try:
            time_col = time_columns[0]
            time_values = df[time_col].dropna()
            if not time_values.empty:
                time_per_question = float(time_values.iloc[0])
        except:
            pass
    
    default_duration = int(len(df) * time_per_question)
    return default_duration
    
def show_folder_view_screen():
    """Show contents of the currently selected folder."""
    current_path = st.session_state.get('current_path', [])
    st.markdown("<div style='margin-top: 4rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("Select Exam")
    
    # Home and Navigation buttons
    if st.button("🏠 Home", use_container_width=True, key="folder_home"):
        st.session_state.current_screen = "home"
        st.rerun()
    if st.button("← Back", use_container_width=True, key="folder_back"):

        # If breadcrumb length <= 1 → treat as Home
        if len(current_path) <= 1:
            st.session_state.current_path = []   # reset to root
            st.session_state.current_screen = "home"
        else:
            st.session_state.current_path = current_path[:-1]

        st.rerun()

    
    breadcrumb = " > ".join(current_path) if current_path else ""
    st.write(f"**📍:** `{breadcrumb}`")
    st.markdown("<div style='margin-top: 0.2;'></div>", unsafe_allow_html=True)

    folder_structure = st.session_state.folder_structure
    current_level = folder_structure
    for folder in current_path:
        current_level = current_level.get(folder, {})
    
    has_qb = '_files' in current_level and 'QB.xlsx' in current_level['_files']
    
    if has_qb:
        qb_path = os.path.join(QUESTION_DATA_FOLDER, *current_path, 'QB.xlsx')
        try:
            questions_data = load_questions(qb_path)
            if questions_data:
                st.session_state.current_qb_path = qb_path
                st.session_state.current_qb_data = questions_data
                
                sheet_names = list(questions_data.keys())
                if sheet_names:
                    st.markdown("<br>", unsafe_allow_html=True)
                    # Mobile-friendly card layout for each test
                    for idx, sheet_name in enumerate(sheet_names):
                        df = questions_data[sheet_name]
                        
                        # Extract metadata from the DataFrame
                        total_questions = len(df)
                        
                        # 1. Calculate Duration
                        time_per_question = 1.5  # Default
                        time_columns = [col for col in df.columns if "Time in Minute/Question" in str(col)]
                        if time_columns:
                            try:
                                time_col = time_columns[0]
                                time_values = df[time_col].dropna()
                                if not time_values.empty:
                                    time_per_question = float(time_values.iloc[0])
                            except:
                                pass
                        
                        total_duration_minutes = int(total_questions * time_per_question)
                        duration_display = f"{total_duration_minutes} min"
                        if total_duration_minutes > 60:
                            hours = total_duration_minutes // 60
                            minutes = total_duration_minutes % 60
                            duration_display = f"{hours}h {minutes}m"
                        
                        # 2. Get Marks/Question
                        marks_per_question = "1"  # Default
                        marks_columns = [col for col in df.columns if "Marks/Question" in str(col) or "Marks Per Question" in str(col)]
                        if not marks_columns:
                            # Also check for just "Marks" column
                            marks_columns = [col for col in df.columns if "Marks" in str(col)]
                        
                        if marks_columns:
                            try:
                                marks_col = marks_columns[0]
                                marks_values = df[marks_col].dropna()
                                if not marks_values.empty:
                                    # Try to get unique value (assuming all questions have same marks)
                                    unique_marks = marks_values.unique()
                                    if len(unique_marks) == 1:
                                        marks_per_question = str(unique_marks[0])
                            except:
                                pass
                        
                        # 3. Get Negative Marks/Question
                        negative_marks_per_question = "0"  # Default
                        negative_columns = [col for col in df.columns if "Negative Marks/Question" in str(col) or "Negative Marks Per Question" in str(col)]
                        
                        if negative_columns:
                            try:
                                negative_col = negative_columns[0]
                                negative_values = df[negative_col].dropna()
                                if not negative_values.empty:
                                    # Try to get unique value
                                    unique_negative = negative_values.unique()
                                    if len(unique_negative) == 1:
                                        negative_marks_per_question = str(unique_negative[0])
                            except:
                                pass
                        
                        # Create columns for the test card
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            # Exam name in primary color
                            st.markdown(f"<h4 style='color: {LITMUSQ_THEME['primary']}; margin: 0;'>{sheet_name}</h4>", 
                                       unsafe_allow_html=True)
                            
                            # Display all metadata in a single line with icons
                            # Alternative compact display (replace the metadata_html section):
                            metadata_html = f"""
                            <div style="text-align: center;">
                                <div style="color: {LITMUSQ_THEME['text']}; font-weight: 600; margin: 0.5rem 0;">
                                    <span style="color: {LITMUSQ_THEME['success']};">Q: {total_questions}</span> • 
                                    <span style="color: {LITMUSQ_THEME['primary']};">⏱️ {duration_display}</span> • 
                                    <span style="color: {LITMUSQ_THEME['warning']};">📊 {marks_per_question}M/Q</span> • 
                                    <span style="color: {LITMUSQ_THEME['secondary']};">⚠️ {negative_marks_per_question}N/Q</span>
                                </div>
                            </div>
                            """
                            
                            st.markdown(metadata_html, unsafe_allow_html=True)
                        
                        with col2:
                            # Create unique key using current path, sheet name, and index
                            current_path_str = '_'.join(current_path) if current_path else 'root'
                            unique_key = f"direct_start_{current_path_str}_{sheet_name}_{idx}"
                            
                            # Quick Start Test button (direct to quiz)
                            if st.button("**Quick Start Test**", 
                                        key=f"quick_{unique_key}",
                                        use_container_width=True,
                                        type="secondary"):
                                # Set default configuration values
                                st.session_state.selected_sheet = sheet_name
                                
                                # Set default configuration values (same as exam_config defaults)
                                st.session_state.num_questions = min(100, len(df))
                                st.session_state.use_final_key = True
                                
                                # Set duration
                                st.session_state.exam_duration = total_duration_minutes
                                
                                # Set other default settings
                                st.session_state.shuffle_questions = False
                                st.session_state.show_live_progress = True
                                st.session_state.enable_auto_save = True
                                st.session_state.full_screen_mode = True
                                
                                # Set live progress and auto-save settings
                                st.session_state.live_progress_enabled = True
                                st.session_state.auto_save_enabled = True
                                
                                # Start the quiz directly with default values
                                start_quiz(df, 
                                           min(100, len(df)),  # Default number of questions
                                           total_duration_minutes,   # Calculated duration
                                           True,               # Use final key
                                           sheet_name)         # Exam name
                                
                                st.session_state.current_screen = "quiz"
                                st.rerun()
                        
                            """
                            # Original button - goes to exam_config
                            if st.button("**Configure & Start Test**", 
                                         key=f"config_{unique_key}",
                                         use_container_width=True,
                                         type="primary"):
                                st.session_state.selected_sheet = sheet_name
                                st.session_state.current_screen = "exam_config"
                                st.rerun()
                            """
                        
                        st.markdown("---")  # Separator between tests
                
                else:
                    st.error("No sheets found in the question bank file.")
                    
        except Exception as e:
            st.error(f"❌ Error loading question bank: {e}")
    
    # Show subfolders
    subfolders = {k: v for k, v in current_level.items() if k != '_files'}
    if subfolders:
        display_folder_navigation(subfolders, current_path)
    elif not has_qb:
        st.info("ℹ️ This folder is empty. Add subfolders or a QB.xlsx file.")
# =============================
# Enhanced Exam Configuration
# =============================
def show_exam_config_screen():
    """Configure exam settings before starting."""
    current_path = st.session_state.get('current_path', [])
    sheet_name = st.session_state.get('selected_sheet')
    qb_data = st.session_state.get('current_qb_data', {})
    
    if sheet_name not in qb_data:
        st.error("Invalid sheet selected. Returning to folder view.")
        st.session_state.current_screen = "folder_view"
        st.rerun()
        return
    
    df_exam = qb_data[sheet_name]
    
    st.markdown("<div style='margin-top: 4rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("Select Exam")

    # Add Home and Back buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="config_home"):
            st.session_state.current_screen = "home"
            st.rerun()
    with col2:
        if st.button("← Return to Test List", use_container_width=True, key="config_back"):
            st.session_state.current_screen = "folder_view"
            st.rerun()
    st.subheader(f"Configure Test: {sheet_name}")
    st.write(f"**📍:** `{' > '.join(current_path)}`")
    st.markdown("<div style='margin-top: 0.2;'></div>", unsafe_allow_html=True)
    st.metric("Total No. of Questions", len(df_exam))
    
    # Enhanced metrics with expandable cards
    col1, col2 = st.columns(2)
    
    with col1:
        # MODIFICATION 1: Check for "Subjects Covered" column first, then "Subject" column
        subjects_column = None
        if "Subjects Covered" in df_exam.columns:
            subjects_column = "Subjects Covered"
        elif "Subject" in df_exam.columns:
            subjects_column = "Subject"
        
        if subjects_column:
            # Get unique subjects (case-insensitive and strip whitespace)
            subjects = df_exam[subjects_column].dropna().apply(lambda x: str(x).strip().title()).unique()
            unique_subjects = sorted(subjects)
            
            column_name_display = "Subjects Covered" if subjects_column == "Subjects Covered" else "Subject"
            with st.expander(f"📚 {column_name_display}: **{len(unique_subjects)}**", expanded=False):
                for i, subject in enumerate(unique_subjects, 1):
                    st.write(f"• {subject}")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.metric("Subjects Covered", "N/A")
    
    with col2:
        if "Exam Year" in df_exam.columns:
            # Get unique years (handle different formats)
            years = df_exam["Exam Year"].dropna().apply(lambda x: str(x).strip()).unique()
            
            # Convert to numeric for proper sorting and remove duplicates
            unique_years = []
            for year in years:
                try:
                    # Try to convert to integer for proper sorting
                    numeric_year = int(year)
                    if numeric_year not in unique_years:
                        unique_years.append(numeric_year)
                except ValueError:
                    # If not numeric, keep as string and ensure uniqueness
                    if year not in unique_years:
                        unique_years.append(year)
            
            # Sort years properly
            try:
                # Sort numeric years in descending order (most recent first)
                numeric_years = [y for y in unique_years if isinstance(y, int)]
                string_years = [y for y in unique_years if isinstance(y, str)]
                sorted_years = sorted(numeric_years, reverse=True) + sorted(string_years)
            except:
                # Fallback: sort everything as strings
                sorted_years = sorted(unique_years, key=str, reverse=True)
            
            with st.expander(f"📅 Years Covered: **{len(sorted_years)}**", expanded=False):
                for year in sorted_years:
                    st.write(f"• {year}")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.metric("Years Covered", "N/A")
    
    # Configuration options
    use_final_key = True
    
    with st.expander("🎛️ Advanced Options"):
        # MODIFICATION 2: Dynamic time per question from Excel
        time_per_question = 1.5  # Default value
        
        # Look for "Time in Minute/Question" in column headers
        time_columns = [col for col in df_exam.columns if "Time in Minute/Question" in str(col)]
        
        if time_columns:
            # Get the first row value from the time column (assumes it's the same for all rows)
            time_col = time_columns[0]
            try:
                # Get the first non-null value
                time_values = df_exam[time_col].dropna()
                if not time_values.empty:
                    # Try to convert to float, use default if conversion fails
                    time_per_question = float(time_values.iloc[0])
                    st.markdown(
                        f"""
                        <div style="
                            font-size: 1.2rem;
                            font-weight: 600;
                            padding: 6px 0;
                            color: #541747;
                        ">
                            ⏱️ You have {time_per_question} minutes to answer each question.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            except (ValueError, TypeError) as e:
                st.warning(f"Could not read time per question from Excel. Using default 1.5 minutes. Error: {e}")
                time_per_question = 1.5
        else:
            # Check if there's a cell with this value in the first few rows
            # Sometimes this might be in a metadata row rather than a column header
            for i in range(min(5, len(df_exam))):
                row = df_exam.iloc[i]
                for cell_value in row:
                    if isinstance(cell_value, str) and "Time in Minute/Question" in cell_value:
                        try:
                            # Extract number from string like "Time in Minute/Question: 2"
                            import re
                            match = re.search(r'[\d.]+', cell_value)
                            if match:
                                time_per_question = float(match.group())
                                st.info(f"⏱️ Found time per question in metadata: {time_per_question} minutes")
                                break
                        except:
                            pass
        
        # Calculate default duration based on dynamic time per question
        default_duration = int(len(df_exam) * time_per_question)
        
        # Move both inputs inside the expander
        col1, col2 = st.columns(2)
        with col1:
            num_questions = st.number_input(
                "❓ Number of Questions", 
                min_value=1, 
                max_value=len(df_exam),
                value=min(100, len(df_exam)), 
                step=1,
                key="num_questions"
            )
        
        with col2:
            exam_duration = st.number_input(
                "⏰ Duration (minutes)", 
                min_value=0, 
                max_value=600, 
                value=default_duration, 
                help=f"Set to 0 for no time limit (Based on {time_per_question} min/question = {default_duration} min)",
                key="exam_duration_input"
            )
        
        # Store the time per question for reference
        st.session_state.time_per_question = time_per_question
        
        # Existing advanced options
        shuffle_questions = st.checkbox("🔀 Shuffle Questions", value=False, key="shuffle_questions")
        show_live_progress = st.checkbox("📊 Show Live Progress", value=True, key="show_live_progress")
        enable_auto_save = st.checkbox("💾 Auto-save Progress", value=True, key="enable_auto_save")
        full_screen_mode = st.checkbox("🖥️ Full Screen Mode", value=True, key="full_screen_mode")
    
    # Start test button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Test Now", type="primary", use_container_width=True, key="start_test"):
            # Store advanced settings using different variable names
            st.session_state.live_progress_enabled = show_live_progress
            st.session_state.auto_save_enabled = enable_auto_save
            
            start_quiz(df_exam, num_questions, exam_duration, use_final_key, sheet_name)
            st.session_state.current_screen = "quiz"
            st.rerun()
    
    st.markdown(
        "<p style='font-size:16px; color:red; font-weight:600; text-align:center;'>⚠️ Do not minimize or switch apps during the test.</p>",
        unsafe_allow_html=True
    )

# =============================
# Enhanced Question Display in Quiz
# =============================
def show_enhanced_question_interface():
    """Display the current question with formatted content using buttons for selection."""
    df = st.session_state.quiz_questions
    current_idx = st.session_state.current_idx
    
    if current_idx >= len(df):
        st.error("Invalid question index")
        return
        
    row = df.iloc[current_idx]
    
    if st.session_state.question_status[current_idx]['status'] == 'not_visited':
        update_question_status(current_idx, 'not_answered')
    
    # Get formatted content
    file_path = st.session_state.get('current_qb_path', '')
    sheet_name = st.session_state.get('selected_sheet', '')
    
    formatted_question = get_formatted_content(
        file_path, sheet_name, current_idx, "question", row['Question']
    )
    formatted_a = get_formatted_content(file_path, sheet_name, current_idx, "option_a", row.get('Option A', ''))
    formatted_b = get_formatted_content(file_path, sheet_name, current_idx, "option_b", row.get('Option B', ''))
    formatted_c = get_formatted_content(file_path, sheet_name, current_idx, "option_c", row.get('Option C', ''))
    formatted_d = get_formatted_content(file_path, sheet_name, current_idx, "option_d", row.get('Option D', ''))
    
    # Enhanced question card with formatted content
    st.markdown(f"**Q. {current_idx + 1}**")
    
    
    # Render formatted question
    render_formatted_content(formatted_question)
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("**Select your answer:**")
    
    current_answer = st.session_state.question_status[current_idx]['answer']
    
    # -------- RADIO BUTTON ANSWER SELECTION --------

    options_dict = {
        "A": formatted_a,
        "B": formatted_b,
        "C": formatted_c,
        "D": formatted_d
    }
    
    # None selected by default
    default_radio_value = (
        current_answer if current_answer in options_dict else None
    )
    
    selected_option = st.radio(
        "options",
        options=["A", "B", "C", "D", None],
        format_func=lambda x: "Clear Response" if x is None else f"{x}) {options_dict[x]}",
        index=["A", "B", "C", "D", None].index(default_radio_value),
        key=f"radio_{current_idx}",
        label_visibility="collapsed"
    )

    
    # Update session state when user selects an option
    if selected_option is not None:
        update_question_status(current_idx, 'answered', selected_option)
        st.session_state.answers[current_idx] = selected_option
    
    
    st.markdown("---")
    st.markdown("<div style='margin-top: 0.2rem;'></div>", unsafe_allow_html=True)
    
    
    # Enhanced action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.button(
            "◀ Previous",
            use_container_width=True,
            disabled=current_idx == 0,
            key=f"prev_{current_idx}",
            type="secondary",
            on_click=lambda: setattr(st.session_state, 'current_idx', current_idx - 1)
        )
    
    with col2:
        st.button(
            "Next ▶",
            use_container_width=True,
            disabled=current_idx == len(df) - 1,
            key=f"next_{current_idx}",
            type="secondary",
            on_click=lambda: setattr(st.session_state, 'current_idx', current_idx + 1)
        )
    
    with col3:
        button_text = "🟨 Mark Review" if not st.session_state.question_status[current_idx]['marked'] else "↩️ Unmark Review"
        st.button(
            button_text,
            use_container_width=True,
            key=f"mark_{current_idx}",
            type="secondary",
            on_click=lambda: toggle_mark_review(current_idx)
        )
    
    with col4:
        st.button(
            "📤 Submit Test",
            use_container_width=True,
            key=f"submit_{current_idx}",
            type="secondary",
            on_click=lambda: setattr(st.session_state, 'submitted', True)
        )
        
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    
    if st.session_state.end_time and not st.session_state.submitted:
        # Calculate remaining time
        time_left = st.session_state.end_time - datetime.now()
        seconds_left = int(time_left.total_seconds())
        
        # Auto-submit when time reaches zero
        if seconds_left <= 0:
            st.session_state.submitted = True
            st.rerun()
            return  # Exit early to prevent further rendering
        
        # Create timer with JavaScript
        html_code = f"""
        <div id="timer" style="
            font-size: 24px;
            font-weight: bold;
            color: {'red' if seconds_left < 300 else 'green'};
            text-align: center;
        "></div>

        <script>
            let timeLeft = {seconds_left};

            function updateTimer() {{
                if (timeLeft <= 0) {{
                    document.getElementById('timer').innerHTML = "⏰ 00:00:00";
                    // Trigger automatic submission when timer reaches zero
                    const submitButton = document.querySelector('[data-testid="baseButton-secondary"]');
                    if (submitButton) {{
                        submitButton.click();
                    }}
                    return;
                }}

                let h = String(Math.floor(timeLeft / 3600)).padStart(2, '0');
                let m = String(Math.floor((timeLeft % 3600) / 60)).padStart(2, '0');
                let s = String(timeLeft % 60).padStart(2, '0');

                document.getElementById('timer').innerHTML = "⏰ " + h + ":" + m + ":" + s;

                timeLeft--;
                setTimeout(updateTimer, 1000);
            }}

            updateTimer();
        </script>
        """
        components.html(html_code, height=60)
    else:
        st.metric("⏰ Time Left", "No Limit")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

# =============================
# Professional Test Interface
# =============================
def initialize_question_status():
    """Initialize question status for all questions."""
    total_questions = len(st.session_state.quiz_questions)
    st.session_state.question_status = {}
    
    for i in range(total_questions):
        st.session_state.question_status[i] = {
            'status': 'not_visited',
            'marked': False,
            'answer': None,
            'time_spent': 0,
            'visited_at': None
        }
    
    st.session_state.current_idx = 0
    st.session_state.start_time = datetime.now()

def update_question_status(question_idx, status, answer=None):
    """Update the status of a question."""
    if question_idx in st.session_state.question_status:
        st.session_state.question_status[question_idx]['status'] = status
        if answer is not None:
            st.session_state.question_status[question_idx]['answer'] = answer
        else:
            st.session_state.question_status[question_idx]['answer'] = None
            
        if status != 'not_visited' and status != 'cleared':
            st.session_state.question_status[question_idx]['visited_at'] = datetime.now()
        else:
            # Reset visited_at when going back to not visited or cleared
            st.session_state.question_status[question_idx]['visited_at'] = None

def toggle_mark_review(question_idx):
    """Toggle mark for review status."""
    if question_idx in st.session_state.question_status:
        current_marked = st.session_state.question_status[question_idx]['marked']
        st.session_state.question_status[question_idx]['marked'] = not current_marked
        
        current_status = st.session_state.question_status[question_idx]['status']
        current_answer = st.session_state.question_status[question_idx]['answer']
        
        if not current_marked:
            if current_answer is not None:
                st.session_state.question_status[question_idx]['status'] = 'answered_marked'
            else:
                if current_status == 'cleared':
                    st.session_state.question_status[question_idx]['status'] = 'cleared_marked'
                else:
                    st.session_state.question_status[question_idx]['status'] = 'marked_review'
        else:
            if current_answer is not None:
                st.session_state.question_status[question_idx]['status'] = 'answered'
            else:
                if current_status == 'cleared_marked':
                    st.session_state.question_status[question_idx]['status'] = 'cleared'
                else:
                    st.session_state.question_status[question_idx]['status'] = 'not_answered'

def get_question_display_info(q_num):
    """Get display information for a question in the palette."""
    if q_num not in st.session_state.question_status:
        return LITMUSQ_THEME['background'], str(q_num + 1), "Not visited"
    
    status_info = st.session_state.question_status[q_num]
    has_answer = status_info['answer'] is not None
    is_marked = status_info['marked']
    status = status_info['status']
    
    # Determine text and emoji based on status
    if status == 'cleared':
        emoji = "⛔"  # White square emoji
        text = f"{q_num + 1}"  # Show number
        tooltip = "Response cleared"
    elif has_answer and is_marked:
        emoji = "🟩"
        text = f"{q_num + 1}"  # Show number
        tooltip = "Answered & marked for review"
    elif has_answer:
        emoji = "✅"
        text = f"{q_num + 1}"  # Show number
        tooltip = "Answered"
    elif is_marked:
        emoji = "🟨"
        text = f"{q_num + 1}"  # Show number
        tooltip = "Marked for Review"
    elif status == 'not_answered':
        emoji = "❌"
        text = f"{q_num + 1}"  # Show number
        tooltip = "Not Answered"
    else:  # not_visited
        emoji = ""  # No emoji for not visited
        text = f"{q_num + 1}"  # Show question number only
        tooltip = "Not Visited"
    
    return emoji, text, tooltip

# In the show_question_palette function, update the button creation:
def show_question_palette():
    """Display the question palette with exam info above it."""
    # Show exam info above the palette
    st.sidebar.markdown(f"### 📝 {st.session_state.exam_name}")
    st.sidebar.markdown(f"**Question {st.session_state.current_idx + 1} of {len(st.session_state.quiz_questions)}**")

    # Show answered and marked counts
    if 'question_status' in st.session_state:
        total = len(st.session_state.quiz_questions)
        answered = sum(1 for status in st.session_state.question_status.values() 
                       if status['answer'] is not None)
        marked = sum(1 for status in st.session_state.question_status.values() 
                     if status['marked'])
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("✅ Answered", f"{answered}/{total}") 
        with col2:
            st.metric("🟨 Marked", f"{marked}")
    
    # Legend
    st.sidebar.markdown("""
    <style>
    .legend-item {
        display: flex;
        align-items: center;
        margin: 5px 0;
        font-size: 12px;
    }
    .color-box {
        width: 15px;
        height: 15px;
        margin-right: 8px;
        border: 1px solid #ccc;
        border-radius: 3px;
    }
    </style>
    
    <div class="legend-item">
        <span>⛔: Response cleared</span>
    </div>
    <div class="legend-item">
        <span>❌: Not Answered</span>
    </div>
    <div class="legend-item">
        <span>✅: Answered</span>
    </div>
    <div class="legend-item">
        <span>🟨: Marked for Review</span>
    </div>
    <div class="legend-item">
        <span>🟩: Answered & marked for review</span>
    </div>
    """, unsafe_allow_html=True)
    

    # Question palette grid
    total_questions = len(st.session_state.quiz_questions)
    if total_questions == 0:
        st.sidebar.warning("No questions loaded")
        return
    
    cols = 5
    rows = (total_questions + cols - 1) // cols
    
    for row in range(rows):
        columns = st.sidebar.columns(cols)
        for col_idx in range(cols):
            q_num = row * cols + col_idx
            if q_num < total_questions:
                with columns[col_idx]:
                    emoji, number, tooltip = get_question_display_info(q_num)
                    
                    # Create button text with both emoji and number
                    button_text = f"{emoji} {number}".strip()
                    
                    # Determine if current question
                    border_color = LITMUSQ_THEME['secondary'] if q_num == st.session_state.current_idx else "#cccccc"
                    
                    # Get appropriate background color
                    status_info = st.session_state.question_status.get(q_num, {})
                    has_answer = status_info.get('answer') is not None
                    is_marked = status_info.get('marked', False)
                    status = status_info.get('status', 'not_visited')
                    
                    if status == 'cleared':
                        bg_color = LITMUSQ_THEME['background']
                    elif has_answer and is_marked:
                        bg_color = "#FFD700"  # Gold
                    elif has_answer:
                        bg_color = LITMUSQ_THEME['success']  # Green
                    elif is_marked:
                        bg_color = LITMUSQ_THEME['primary']  # Blue
                    elif status == 'not_answered':
                        bg_color = LITMUSQ_THEME['secondary']  # Red
                    else:  # not_visited
                        bg_color = LITMUSQ_THEME['background']  # White
                    
                    button_style = f"""
                    <style>
                    .qbtn-{q_num} {{
                        background-color: {bg_color} !important;
                        border: 2px solid {border_color} !important;
                        border-radius: 5px !important;
                        color: #000000 !important;
                        font-weight: bold !important;
                    }}
                    </style>
                    """
                    st.markdown(button_style, unsafe_allow_html=True)
                    
                    if st.button(
                        button_text, 
                        key=f"palette_{q_num}", 
                        use_container_width=True,
                        help=f"Q{q_num + 1}: {tooltip}"
                    ):
                        st.session_state.current_idx = q_num
                        if st.session_state.question_status[q_num]['status'] == 'not_visited':
                            update_question_status(q_num, 'not_answered')
                        st.rerun()
                        
def live_timer_component(seconds_left: int):
    html_code = f"""
    <div id="timer" style="
        font-size: 28px;
        font-weight: bold;
        color: red;
        text-align: center;
    "></div>

    <script>
        let timeLeft = {seconds_left};

        function updateTimer() {{
            if (timeLeft <= 0) {{
                document.getElementById('timer').innerHTML = "⏰ 00:00:00";
                return;
            }}

            let h = String(Math.floor(timeLeft / 3600)).padStart(2, '0');
            let m = String(Math.floor((timeLeft % 3600) / 60)).padStart(2, '0');
            let s = String(timeLeft % 60).padStart(2, '0');

            document.getElementById('timer').innerHTML = "⏰ " + h + ":" + m + ":" + s;

            timeLeft--;
            setTimeout(updateTimer, 1000);
        }}

        updateTimer();
    </script>
    """
    components.html(html_code, height=60)

def show_live_timer():
    """Display live timer with auto-refresh."""
    if not st.session_state.end_time or st.session_state.submitted:
        return "00:00:00"
    
    time_left = st.session_state.end_time - datetime.now()
    
    if time_left.total_seconds() <= 0:
        st.session_state.submitted = True
        return "00:00:00"
    
    hours, remainder = divmod(int(time_left.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_time_color(seconds_left):
    """Get color based on time remaining."""
    if seconds_left < 300:  # 5 minutes
        return LITMUSQ_THEME['secondary']  # Red
    elif seconds_left < 900:  # 15 minutes
        return LITMUSQ_THEME['warning']    # Amber
    else:
        return LITMUSQ_THEME['success']    # Green



def auto_submit_on_timeout():
    """Auto-submit the test when time is up using JavaScript."""
    if st.session_state.end_time and not st.session_state.submitted:
        time_left = st.session_state.end_time - datetime.now()
        seconds_left = int(time_left.total_seconds())
        
        # If time is already up, submit immediately
        if seconds_left <= 0:
            st.session_state.submitted = True
            st.rerun()
            return
        
        # Inject JavaScript to auto-submit when timer reaches zero
        js_code = f"""
        <script>
        // Check every second if time is up
        function checkTime() {{
            // Calculate remaining seconds
            let now = new Date();
            let endTime = new Date('{st.session_state.end_time.isoformat()}');
            let secondsLeft = Math.max(0, Math.floor((endTime - now) / 1000));
            
            if (secondsLeft <= 0) {{
                // Time's up! Auto-submit
                document.body.innerHTML += '<form id="autoSubmitForm" style="display:none;">' +
                    '<input type="hidden" name="auto_submit" value="true">' +
                '</form>';
                document.getElementById('autoSubmitForm').submit();
            }}
        }}
        
        // Check every second
        setInterval(checkTime, 1000);
        </script>
        """
        components.html(js_code, height=0)    

def clear_response(question_idx):
    """Clear response for a question."""
    # Set a special status for cleared responses
    st.session_state.question_status[question_idx]['status'] = 'cleared'
    st.session_state.question_status[question_idx]['answer'] = None
    st.session_state.question_status[question_idx]['marked'] = False
    
    # Also clear from answers dictionary
    if question_idx in st.session_state.answers:
        del st.session_state.answers[question_idx]
    
    # Clear the radio button selection
    if f"question_{question_idx}" in st.session_state:
        del st.session_state[f"question_{question_idx}"]
    
    st.rerun()

def show_quiz_header_with_timer():
    """Show a custom header with timer for quiz interface."""
    if st.session_state.end_time and not st.session_state.submitted:
        time_left = st.session_state.end_time - datetime.now()
        seconds_left = max(0, int(time_left.total_seconds()))
        
        # Calculate initial time display
        h = str(seconds_left // 3600).zfill(2)
        m = str((seconds_left % 3600) // 60).zfill(2)
        s = str(seconds_left % 60).zfill(2)
        
        # Determine color based on time remaining
        timer_color = '#ff6b6b' if seconds_left < 300 else 'white'
        timer_bg = 'rgba(255,107,107,0.3)' if seconds_left < 300 else 'rgba(255,255,255,0.2)'
        
        # Create a custom HTML header with timer
        st.markdown(f"""
        <style>
        .fixed-quiz-header {{
            position: fixed;
            top: 0;
            left: 0;
            margin-top: 3.5rem;
            margin-bottom:0.2rem;
            width: 100%;
            height:2rem;
            background: linear-gradient(135deg, {LITMUSQ_THEME['primary']}, {LITMUSQ_THEME['secondary']});
            color: white;
            padding: 0.8rem 1rem;
            z-index: 9999;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .content-wrapper {{
            padding-top: 70px; /* Make space for fixed header */
        }}
        </style>
        
        <div class="fixed-quiz-header">
            <div style="font-size: 1rem;">
                {st.session_state.exam_name}
            </div>
            <div id="header-timer" style="
                font-size: 1rem;
                padding: 0.3rem 1rem;
                border-radius: 50px;
                min-width: 120px;
                text-align: center;
                color: {timer_color};
                transition: all 0.3s ease;
            ">
                ⏰ {h}:{m}:{s}
            </div>
        </div>
        
        <div class="content-wrapper"></div>
        
        <script>
            let timeLeft = {seconds_left};

            function updateTimer() {{
                const timerEl = document.getElementById("header-timer");
                
                if (!timerEl) {{
                    setTimeout(updateTimer, 500);
                    return;
                }}
                
                if (timeLeft <= 0) {{
                    timerEl.innerHTML = "⏰ 00:00:00";
                    timerEl.style.color = "red";
                    
                    // Trigger automatic submission when timer reaches zero
                    const submitButton = document.querySelector('[data-testid="baseButton-secondary"]');
                    if (submitButton) {{
                        submitButton.click();
                    }}
                    return;
                }}

                let h = String(Math.floor(timeLeft / 3600)).padStart(2, '0');
                let m = String(Math.floor((timeLeft % 3600) / 60)).padStart(2, '0');
                let s = String(timeLeft % 60).padStart(2, '0');

                timerEl.innerHTML = "⏰ " + h + ":" + m + ":" + s;
                
                // Update color when less than 5 minutes
                if (timeLeft < 300) {{
                    timerEl.style.color = "red";
                }}

                timeLeft--;
                setTimeout(updateTimer, 1000);
            }}

            updateTimer();
        </script>
        """, unsafe_allow_html=True)
    else:
        # Show header without timer if no time limit
        st.markdown(f"""
        <style>
        .fixed-quiz-header {{
            position: fixed;
            top: 0;
            left: 0;
            margin-top: 3.5rem;
            width: 100%;
            background: linear-gradient(135deg, {LITMUSQ_THEME['primary']}, {LITMUSQ_THEME['secondary']});
            color: white;
            padding: 0.8rem 1rem;
            z-index: 9999;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .content-wrapper {{
            padding-top: 70px;
        }}
        </style>
        
        <div class="fixed-quiz-header">
            <div style="font-size: 1rem;">
                {st.session_state.exam_name}
            </div>
        </div>
        <div class="content-wrapper"></div>
        """, unsafe_allow_html=True)

# In show_quiz_screen function, add this at the beginning:
def show_quiz_screen():
    """Main quiz interface with professional layout."""
    # Show header with timer
    show_quiz_header_with_timer()
    
    # Rest of your existing code...
    if not st.session_state.quiz_started:
        st.error("Quiz not properly initialized. Returning to home.")
        st.session_state.current_screen = "home"
        st.rerun()
        return
    
    if 'question_status' not in st.session_state or not st.session_state.question_status:
        initialize_question_status()
    
    # Auto-check for timeout and auto-submit
    if st.session_state.end_time and not st.session_state.submitted:
        time_left = st.session_state.end_time - datetime.now()
        seconds_left = int(time_left.total_seconds())
        
        # If time is up, auto-submit
        if seconds_left <= 0:
            st.session_state.submitted = True
            st.rerun()
            return
        
        # Set up auto-refresh with reduced frequency
        if seconds_left <= 0:
            # Time's up - auto-submit immediately
            st.session_state.submitted = True
            st.rerun()
        elif seconds_left < 5:  # Last minute: every 5 seconds
            st_autorefresh(interval=1000, key="timer_refresh_last_minute")
        elif seconds_left < 300:  # Last 5 minutes: every 60 seconds
            st_autorefresh(interval=60000, key="timer_refresh_last_5min")
        elif seconds_left < 1800:  # Last 30 minutes: every 5 minutes
            st_autorefresh(interval=300000, key="timer_refresh_last_30min")
        else:  # More than 30 minutes: every 10 minutes
            st_autorefresh(interval=1000000, key="timer_refresh_long_exam")
    
    if st.session_state.get('show_leave_confirmation', False):
        st.sidebar.warning("Leave test? Progress will be lost.")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Yes, Leave", use_container_width=True, key="confirm_leave"):
                st.session_state.current_screen = "home"
                st.session_state.show_leave_confirmation = False
                st.rerun()
        with col2:
            if st.button("Cancel", use_container_width=True, key="cancel_leave"):
                st.session_state.show_leave_confirmation = False
                st.rerun()
    
    show_question_palette()
    
    # Show question first, then header at the bottom
    if not st.session_state.submitted:
        
        show_enhanced_question_interface()
    else:
        show_results_screen()

# Add this function to handle auto-submits from JavaScript
def handle_auto_submit():
    """Handle auto-submit from JavaScript timer."""
    # Check if this is an auto-submit request
    if st.experimental_get_query_params().get('auto_submit'):
        st.session_state.submitted = True
        st.rerun()        

# =============================
# Enhanced Results Screen
# =============================
def compute_results():
    """Compute results with proper type conversion."""
    df = st.session_state.quiz_questions.copy()
    use_final = st.session_state.use_final_key
    user_ans = st.session_state.answers

    df["Correct Option Used"] = df.apply(lambda r: get_correct_option(r, use_final), axis=1)
    df["Your Answer"] = [user_ans.get(i, None) for i in range(len(df))]
    df["Is Correct"] = df["Your Answer"] == df["Correct Option Used"]

    if "Marks" in df.columns:
        df["Marks"] = pd.to_numeric(df["Marks"], errors="coerce").fillna(0)
        df["Score"] = np.where(df["Is Correct"], df["Marks"], 0)
    else:
        df["Marks"] = 1
        df["Score"] = np.where(df["Is Correct"], 1, 0)

    # Convert to Python native types
    total = int(df["Marks"].sum())
    obtained = int(df["Score"].sum())
    
    attempted = sum(1 for status in st.session_state.question_status.values() 
                   if status['answer'] is not None)
    correct = int(df["Is Correct"].sum())
    
    # Create detailed answers list for retest functionality
    detailed_answers = []
    for i in range(len(df)):
        user_answer = user_ans.get(i, None)
        correct_answer = df.iloc[i]["Correct Option Used"]
        is_correct = df.iloc[i]["Is Correct"]
        
        # Convert numpy bool to Python bool
        if isinstance(is_correct, (np.bool_, np.bool)):
            is_correct = bool(is_correct)
        
        detailed_answers.append({
            "question_index": int(i),  # Ensure integer
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "marked": bool(st.session_state.question_status.get(i, {}).get('marked', False))
        })
    summary = {
        "Exam Name": st.session_state.exam_name,
        "Total Questions": int(len(df)),
        "Attempted": int(attempted),
        "Correct": int(correct),
        "Total Marks": int(total),
        "Marks Obtained": int(obtained),
        "Answer Key Used": "Final" if use_final else "Provisional",
        "Username": st.session_state.username,
        "Percentage": float((obtained / total * 100) if total > 0 else 0),
        "detailed_answers": detailed_answers,
        "is_retest": bool(st.session_state.get('is_retest', False)),
        "original_test_id": st.session_state.get('original_test_id', None),
        "retest_type": st.session_state.get('retest_type', 'full')  # Add this line
    }
    return df, summary
    
def delete_test_entry(username, test_id):
    """Delete a specific test entry from user progress."""
    try:
        if db is None:
            st.error("Firebase not initialized")
            return False
        
        progress = load_user_progress(username)
        if not progress:
            return False
        
        # Convert progress data to ensure proper types
        progress = convert_numpy_to_python(progress)
        
        # Find and remove the test
        test_history = progress.get("test_history", [])
        test_to_delete = None
        updated_history = []
        
        for test in test_history:
            if test.get("test_id") == test_id:
                test_to_delete = test
            else:
                updated_history.append(test)
        
        if test_to_delete:
            # Update progress statistics with proper types
            progress["test_history"] = updated_history
            progress["tests_taken"] = int(len(updated_history))
            
            # Recalculate total score and average
            if updated_history:
                progress["total_score"] = float(sum(float(t["score"]) for t in updated_history))
                progress["average_score"] = float(progress["total_score"]) / float(len(updated_history))
            else:
                progress["total_score"] = 0.0
                progress["average_score"] = 0.0
            
            # Save updated progress
            save_user_progress(username, progress)
            return True
        
        return False
    except Exception as e:
        st.error(f"Error deleting test entry: {e}")
        return False
        
def show_retest_config(original_test):
    """Show configuration for retest based on original test."""
    show_litmusq_header(f"Configure Re-Test: {original_test['exam_name']}")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="retest_home"):
            st.session_state.current_screen = "home"
            st.rerun()
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True, key="retest_back"):
            st.session_state.current_screen = "dashboard"
            st.rerun()
    
    st.markdown(f"**Original Test Date:** {datetime.fromisoformat(original_test['date']).strftime('%Y-%m-%d %H:%M')}")
    st.markdown(f"**Original Score:** {original_test['score']}/{original_test['total_marks']} ({original_test['percentage']:.1f}%)")
    
    # Check if we have stored questions
    if 'questions_used' not in original_test or not original_test['questions_used']:
        st.error("Original questions data not available. Cannot create retest.")
        st.info("Note: This feature requires tests taken after this update.")
        return
    
    # Analyze original test performance
    total_questions = original_test['total_questions']
    incorrect_questions = []
    unanswered_questions = []
    
    if 'detailed_answers' in original_test:
        for answer in original_test['detailed_answers']:
            user_answer = answer.get('user_answer')
            is_correct = answer.get('is_correct', False)
            
            # Check if unanswered (user_answer is None or empty)
            if user_answer is None or (isinstance(user_answer, str) and user_answer.strip() == ""):
                unanswered_questions.append(answer['question_index'])
            # Check if answered but incorrect
            elif not is_correct:
                incorrect_questions.append(answer['question_index'])
    
    st.subheader("📊 Original Test Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Questions", total_questions)
    with col2:
        st.metric("Incorrect Answers", len(incorrect_questions))
    with col3:
        st.metric("Unanswered", len(unanswered_questions))
    with col4:
        correct_questions = total_questions - len(incorrect_questions) - len(unanswered_questions)
        st.metric("Correct Answers", correct_questions)
    
    # Retest options
    retest_option = st.radio(
        "Select Re-Test Type:",
        [
            "Incorrect & Unanswered (Recommended)",
            "All Questions", 
            "Incorrectly Answered Questions Only", 
            "Unanswered Questions Only"
        ],
        index=0,
        key="retest_option"
    )
    
    # Calculate questions based on selection
    if retest_option == "All Questions":
        question_count = total_questions
        question_indices = list(range(total_questions))
    
    elif retest_option == "Incorrectly Answered Questions Only":
        question_count = len(incorrect_questions)
        question_indices = incorrect_questions
    
    elif retest_option == "Unanswered Questions Only":
        question_count = len(unanswered_questions)
        question_indices = unanswered_questions
    
    elif retest_option == "Incorrect & Unanswered (Recommended)":
        # Combine but remove duplicates (though there shouldn't be any now)
        combined = sorted(set(incorrect_questions + unanswered_questions))
        question_count = len(combined)
        question_indices = combined
    
    st.markdown(f"✅ **{question_count} questions** will be included in the re-test.")
    
    # Show breakdown if Incorrect & Unanswered is selected
    if retest_option == "Incorrect & Unanswered (Recommended)":
        st.markdown(f"({len(incorrect_questions)} incorrect questions\n & {len(unanswered_questions)} unanswered questions)")
    
    # Create DataFrame from stored questions
    questions_data = original_test['questions_used']
    
    # Convert to DataFrame format
    questions_list = []
    for q_data in questions_data:
        questions_list.append({
            'Question': q_data.get('question_text', ''),
            'Option A': q_data.get('option_a', ''),
            'Option B': q_data.get('option_b', ''),
            'Option C': q_data.get('option_c', ''),
            'Option D': q_data.get('option_d', ''),
            'Explanation': q_data.get('explanation', ''),
            'Correct Option (Final Answer Key)': q_data.get('correct_option', '')
        })
    
    df_questions = pd.DataFrame(questions_list)
    
    # Store retest configuration in session state
    if st.button("🚀 Start Re-Test", type="primary", use_container_width=True, key="start_retest"):
        if question_count == 0:
            st.error("No questions selected for re-test! Choose a different option.")
            return
            
        # Filter questions based on selection
        if question_indices:
            filtered_df = df_questions.iloc[question_indices].reset_index(drop=True)
        else:
            filtered_df = df_questions
        
        # Set retest flags
        st.session_state.is_retest = True
        st.session_state.original_test_id = original_test.get('test_id')
        st.session_state.retest_type = retest_option
        
        # Get exam name
        exam_name = original_test['exam_name']
        if original_test.get('is_retest', False):
            # This is a retest of a retest, add level indicator
            exam_name = f"{exam_name}📝"
        
        # Start the retest
        start_quiz(
            filtered_df,
            len(filtered_df),
            st.session_state.quiz_duration,
            st.session_state.use_final_key,
            exam_name
        )
        st.session_state.current_screen = "quiz"
        st.rerun()
def show_enhanced_detailed_analysis(res_df):
    """Show detailed analysis with formatted content and question status in headings."""
    for i, row in res_df.iterrows():
        file_path = st.session_state.get('current_qb_path', '')
        sheet_name = st.session_state.get('selected_sheet', '')
        
        # Get formatted content
        formatted_question = get_formatted_content(file_path, sheet_name, i, "question", row['Question'])
        formatted_a = get_formatted_content(file_path, sheet_name, i, "option_a", row.get('Option A', ''))
        formatted_b = get_formatted_content(file_path, sheet_name, i, "option_b", row.get('Option B', ''))
        formatted_c = get_formatted_content(file_path, sheet_name, i, "option_c", row.get('Option C', ''))
        formatted_d = get_formatted_content(file_path, sheet_name, i, "option_d", row.get('Option D', ''))
        formatted_explanation = get_formatted_content(file_path, sheet_name, i, "explanation", row.get('Explanation', ''))
        
        # Determine question status for heading
        correct = row["Correct Option Used"]
        chosen = row["Your Answer"]
        
        # Create status indicator for heading
        if pd.isna(chosen) or chosen is None:
            status_indicator = "🟡 Not Answered"
            status_color = "#94A3B8"  # Gray
        elif correct == chosen:
            status_indicator = "✅ Correct"
            status_color = LITMUSQ_THEME['success']  # Green
        else:
            status_indicator = "❌ Wrong"
            status_color = LITMUSQ_THEME['secondary']  # Red
        
        # Create expander with status in heading
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        with st.expander(
            f"Q{i+1}: {status_indicator}", 
            expanded=False
        ):
            # Add status badge at the top
            st.markdown(f"""
            <div style="
                display: inline-block;
                padding: 4px 12px;
                background-color: {status_color}20;
                color: {status_color};
                border: 1px solid {status_color};
                border-radius: 20px;
                font-weight: 600;
                font-size: 0.9rem;
                margin-bottom: 10px;
            ">
                {status_indicator}
            </div>
            """, unsafe_allow_html=True)
            
            # Question text
            st.markdown("**Question:**")
            render_formatted_content(formatted_question)
            
            # Options with status indicators
            def render_formatted_option(label, text, is_correct, is_chosen):
                option_col1, option_col2 = st.columns([1, 20])
                
                with option_col1:
                    if is_correct and is_chosen:
                        st.markdown(f"✅**{label})** ")
                    elif is_correct:
                        st.markdown(f"✔️**{label})** ")
                    elif is_chosen:
                        st.markdown(f"❌**{label})** ")
                    else:
                        st.markdown(f"⬜**{label})**")
                
                with option_col2:
                    render_formatted_content(text)
            
            render_formatted_option("A", formatted_a, "A" == correct, "A" == chosen)
            render_formatted_option("B", formatted_b, "B" == correct, "B" == chosen)
            render_formatted_option("C", formatted_c, "C" == correct, "C" == chosen)
            render_formatted_option("D", formatted_d, "D" == correct, "D" == chosen)
            
            # Show correct answer summary
            st.markdown(f"**Correct Answer:** **{correct}**")
            
            if chosen and not pd.isna(chosen):
                st.markdown(f"**Your Answer:** **{chosen}**")
            
            # Explanation
            if formatted_explanation and str(formatted_explanation).strip():
                st.markdown("**Explanation:**")
                render_formatted_content(formatted_explanation)
            
            # Add some spacing
            st.markdown("")

def show_results_screen():
    """Display enhanced results after quiz completion."""
    res_df, summary = compute_results()
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("Test Results")
    
    # Add retest type to summary if applicable
    if hasattr(st.session_state, 'retest_type'):
        summary['retest_type'] = st.session_state.retest_type
    
    # Update user progress
    # Save progress only once per test
    if not st.session_state.get("progress_saved", False):
        update_user_progress(summary)
        st.session_state.progress_saved = True

    # Clear retest state after saving results
    clear_retest_state()
    
# Navigation options - Add Home button
    if st.button("🏠 Home", use_container_width=True, key="results_home"):
        st.session_state.current_screen = "home"
        st.rerun()
    if st.button("← Back to Config", use_container_width=True, key="results_back"):
        st.session_state.current_screen = "exam_config"
        st.rerun()
    if st.button("📊 View Analysis", use_container_width=True, key="results_analysis"):
        st.session_state.show_detailed_analysis = not st.session_state.get('show_detailed_analysis', False)
        st.rerun()
    if st.button("🔁 Retake Test", use_container_width=True, key="results_retake"):
        df_exam = st.session_state.quiz_questions
        start_quiz(
            df_exam, 
            len(df_exam),
            st.session_state.quiz_duration,
            st.session_state.use_final_key, 
            st.session_state.exam_name
        )
        st.session_state.current_screen = "quiz"
        st.rerun()
    if st.button("📈 Performance", use_container_width=True, key="results_dashboard"):
        st.session_state.current_screen = "dashboard"
        st.rerun()
    
    # Summary cards with enhanced styling
    st.markdown("---")
    st.subheader("📊 Performance Summary")
    

    st.metric("Total Questions", summary["Total Questions"])
    st.markdown('</div>', unsafe_allow_html=True)
    st.metric("Attempted", summary["Attempted"])
    st.markdown('</div>', unsafe_allow_html=True)
    st.metric("Correct Answers", summary["Correct"])
    st.markdown('</div>', unsafe_allow_html=True)
    st.metric("Final Score", f"{summary['Marks Obtained']}/{summary['Total Marks']}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Score visualization
    percentage = summary['Percentage']
    st.subheader(f"Overall Score: {percentage:.1f}%")
    st.progress(int(percentage))
    
    # Performance gauge
    col1, col2 = st.columns([2, 1])
    with col1:
        if percentage >= 80:
            performance = "Excellent! 🎉"
            color = LITMUSQ_THEME['success']
        elif percentage >= 60:
            performance = "Good! 👍"
            color = LITMUSQ_THEME['warning']
        else:
            performance = "Needs Improvement 📚"
            color = LITMUSQ_THEME['secondary']
        
        st.markdown(f"<h3 style='color: {color};'>{performance}</h3>", unsafe_allow_html=True)
    
    with col2:
        st.download_button(
            label="📥 Download Results",
            data=res_df.to_csv(index=False),
            file_name=f"{summary['Exam Name']}_results_{st.session_state.username}.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_results"
        )
    
    # Detailed analysis
    if st.session_state.get('show_detailed_analysis', False):
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        st.subheader("📋 Question-wise Review")
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        show_enhanced_detailed_analysis(res_df)
        
# =============================
# Session State Optimization
# =============================
def optimize_session_state():
    """Clean up and optimize session state to prevent bloat."""
    essential_keys = {
        'logged_in', 'username', 'user_type', 'current_screen', 'current_path',  # ← Added user_type
        'selected_sheet', 'current_qb_path', 'folder_structure',
        'quiz_started', 'quiz_questions', 'current_idx', 'answers',
        'submitted', 'exam_name', 'question_status', 'quiz_duration',
        'use_final_key', 'started_at', 'end_time', 'last_cleanup'
    }
    
    # Remove non-essential keys
    keys_to_remove = [key for key in st.session_state.keys() if key not in essential_keys]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

def periodic_cleanup():
    """Perform periodic cleanup every 5 minutes."""
    if 'last_cleanup' not in st.session_state:
        st.session_state.last_cleanup = datetime.now()
        return
    
    # Clean up every 5 minutes
    if (datetime.now() - st.session_state.last_cleanup).seconds > 300:
        optimize_session_state()
        st.session_state.last_cleanup = datetime.now()

def check_memory_usage():
    """Check memory usage and trigger cleanup if needed."""
    try:
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        if memory_usage > PerformanceConfig.MAX_MEMORY_MB:
            st.sidebar.warning("High memory usage detected - optimizing...")
            optimize_session_state()
            st.rerun()
        
        return memory_usage
    except:
        return 0  # Return 0 if psutil not available

def safe_execute(func, *args, **kwargs):
    """Execute function with error handling and recovery."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.error(f"An error occurred in {func.__name__}: {str(e)}")
        st.info("🔄 Attempting to recover...")
        
        # Basic recovery - return to home
        if st.session_state.get('logged_in'):
            st.session_state.current_screen = "home"
            optimize_session_state()
            st.rerun()
        return None
        
# =============================
# Helper Functions
# =============================
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {c: str(c).strip() for c in df.columns}
    return df.rename(columns=mapping)

def load_questions(file_path):
    """Load questions from Excel file with memory optimization."""
    try:
        # Define essential columns to load
        essential_columns = [
            'Question', 'Option A', 'Option B', 'Option C', 'Option D',
            'Explanation', 'Correct Option (Final Answer Key)',
            'Correct option (Provisional Answer Key)', 'Marks', 'Subject', 'Exam Year'
        ]
        
        # Read only necessary columns
        df_dict = pd.read_excel(
            file_path, 
            sheet_name=None, 
            engine="openpyxl",
            usecols=lambda x: any(col in x for col in essential_columns)
        )
        
        clean_dict = {}
        for sheet, df in df_dict.items():
            df = _normalize_columns(df)
            
            # Optimize memory usage
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Convert to string type for better memory usage
                    df[col] = df[col].astype('string')
            
            # Fill NA values efficiently
            text_columns = ["Question", "Option A", "Option B", "Option C", "Option D", "Explanation"]
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].fillna("")
            
            clean_dict[sheet] = df
            
        return clean_dict
    except Exception as e:
        st.error(f"Error loading questions from {file_path}: {e}")
        return {}

def get_correct_option(row, use_final_key=True):
    final_col = "Correct Option (Final Answer Key)"
    prov_col = "Correct option (Provisional Answer Key)"
    val = None
    if use_final_key and final_col in row and str(row[final_col]).strip():
        val = str(row[final_col]).strip()
    elif prov_col in row and str(row[prov_col]).strip():
        val = str(row[prov_col]).strip()
    if val is None:
        return None
    v = val.strip().upper()
    mapping = {
        "A": "A", "B": "B", "C": "C", "D": "D",
        "1": "A", "2": "B", "3": "C", "4": "D",
        "OPTION A": "A", "OPTION B": "B", "OPTION C": "C", "OPTION D": "D",
    }
    return mapping.get(v, v[:1] if v[:1] in ["A", "B", "C", "D"] else None)

def start_quiz(df: pd.DataFrame, n_questions: int, duration_minutes: int,
               use_final_key: bool, exam_name: str):
    """Start quiz."""
    n = min(n_questions, len(df))
    
    # Check if shuffle is enabled from session state
    shuffle_enabled = st.session_state.get('shuffle_questions', False)
    
    if shuffle_enabled:
        # Shuffle the questions
        sampled = df.sample(n=n, random_state=np.random.randint(0, 10**9)).reset_index(drop=True)
    else:
        # Take first n questions without shuffling
        sampled = df.head(n).reset_index(drop=True)
    
    st.session_state.quiz_questions = sampled
    st.session_state.order = list(range(len(sampled)))
    st.session_state.answers = {}
    st.session_state.progress_saved = False
    st.session_state.current_idx = 0
    st.session_state.submitted = False
    st.session_state.quiz_started = True
    st.session_state.started_at = datetime.now()
    st.session_state.end_time = (
        st.session_state.started_at + timedelta(minutes=duration_minutes)
        if duration_minutes and duration_minutes > 0
        else None
    )
    st.session_state.use_final_key = use_final_key
    st.session_state.exam_name = exam_name
    st.session_state.quiz_duration = duration_minutes
    
    # Preserve retest information if available
    if hasattr(st.session_state, 'is_retest'):
        st.session_state.is_retest = st.session_state.is_retest
    if hasattr(st.session_state, 'original_test_id'):
        st.session_state.original_test_id = st.session_state.original_test_id
    if hasattr(st.session_state, 'retest_type'):
        st.session_state.retest_type = st.session_state.retest_type
    
    if 'question_status' in st.session_state:
        del st.session_state.question_status
        
def clear_retest_state():
    """Clear retest state after test completion."""
    if hasattr(st.session_state, 'is_retest'):
        del st.session_state.is_retest
    if hasattr(st.session_state, 'original_test_id'):
        del st.session_state.original_test_id
    if hasattr(st.session_state, 'retest_type'):
        del st.session_state.retest_type
        

# =============================
# Enhanced Home Screen
# =============================
def show_home_screen():
    """Display the main folder navigation."""
    st.markdown("<div style='margin-top: 4rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("Online Tests")
    
    # Home and Navigation buttons
    if st.button("🏠 Home", use_container_width=True, key="folder_home"):
        st.session_state.current_screen = "home"
        st.rerun()
    if st.button("← Back", use_container_width=True, key="folder_back"):
        if len(current_path) > 0:
            st.session_state.current_path = current_path[:-1]
        else:
            st.session_state.current_screen = "home"
        st.rerun()

    # Get current path - MUST BE DEFINED BEFORE USING IT
    current_path = st.session_state.get('editor_current_path', [])
    
    # Display current location breadcrumb
    if current_path:
        breadcrumb = "Home > " + " > ".join(current_path)
    else:
        breadcrumb = "Home"
    
    st.write(f"**📍:** `{breadcrumb}`")
    st.markdown("<div style='margin-top: 0.2;'></div>", unsafe_allow_html=True)
    folder_structure = st.session_state.get('folder_structure', {})
    if folder_structure:
        display_folder_navigation(folder_structure)
    else:
        st.info("No folder structure found. Make sure 'Question_Data_Folder' exists with proper structure.")
        
        

def show_platform_guide():
    """Actual platform guide implementation."""
    st.markdown("<div style='margin-top: 3.5rem;'></div>", unsafe_allow_html=True)
    show_litmusq_header("About LitmusQ")

    # Home button
    if st.button("🏠 Home", use_container_width=True, key="guide_home"):
        st.session_state.current_screen = "home"
        st.rerun()

    st.markdown("## 🧪 Welcome to LitmusQ!")
    st.markdown("<br>", unsafe_allow_html=True)

    # Create 4 columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 🚀 Getting Started")
        st.markdown("""
        1. **Navigate** through the folder structure to find question banks  
        2. **Select** a question bank  
        3. **Configure** your test settings  
        4. **Start** the test and track your progress  
        """)

    with col2:
        st.markdown("### 🎯 Key Features")
        st.markdown("""
        - **Professional Testing Interface**  
        - **Advanced Analytics & Dashboard**  
        - **Color-coded Question Palette**  
        - **Detailed Results with Explanations**  
        - **Clear Performance Data Anytime**  
        - **HTML-Rich Question Formatting**  
        """)

    with col3:
        st.markdown("### 🧭 Legends")
        st.markdown("""
        - ✅ **Answered**  
        - ❌ **Not Answered**  
        - 🟨 **Marked for Review**  
        - 🟩 **Answered + Review**  
        - ⛔ **Response Cleared**  
        """)

    with col4:
        st.markdown("### ⚡ Quick Tips")
        st.markdown("""
        - Use the **Question Palette** to navigate  
        - Mark questions if unsure  
        - Watch the **countdown timer**  
        - Review explanations after the test  
        - Clear your performance history anytime  
        """)



# =============================
# Quick Actions Panel
# =============================
def quick_actions_panel():
    """Display quick actions in sidebar."""
    # Don't show quick actions panel during quiz
    if st.session_state.current_screen == "quiz":
        return
    
    st.sidebar.markdown("---")
    
    # Home Button - Always available (except during quiz)
    if st.sidebar.button("🏠 Home", use_container_width=True, key="sidebar_home"):
        st.session_state.current_screen = "home"
        st.rerun()
    
    # Admin-only actions
    if is_admin_user():
        if st.sidebar.button("Admin Panel", use_container_width=True, key="sidebar_admin"):
            st.session_state.current_screen = "admin_panel"
            st.rerun()
    
    # Editor and Admin can edit questions
    if is_admin_or_editor():  # Changed from is_admin_user()
        if st.sidebar.button("📝 Edit Questions", use_container_width=True, key="sidebar_editor"):
            st.session_state.current_screen = "question_editor"
            st.rerun()
    
    # All users can access these
    if st.sidebar.button("📈 Performance", use_container_width=True, key="sidebar_dashboard"):
        st.session_state.current_screen = "dashboard"
        st.rerun()
        
    if st.sidebar.button("ℹ️ About LitmusQ", use_container_width=True, key="home_guide"):
        st.session_state.current_screen = "guide"
        st.rerun()
        
# =============================
# Enhanced Initialization
# =============================
def initialize_state():
    """Initialize session state with stability features."""
    defaults = {
        "quiz_started": False,
        "quiz_questions": pd.DataFrame(),
        "order": [],
        "answers": {},
        "current_idx": 0,
        "submitted": False,
        "started_at": None,
        "end_time": None,
        "use_final_key": True,
        "exam_name": None,
        "logged_in": False,
        "username": None,
        "user_type": "regular",  # Add this
        "current_screen": "home",
        "current_path": [],
        "selected_sheet": None,
        "current_qb_path": None,
        "current_qb_data": {},
        "folder_structure": {},
        "quiz_duration": 0,
        "question_status": {},
        "live_progress_enabled": True,
        "auto_save_enabled": True,
        "show_detailed_analysis": False,
        "calc_display": "0",
        "show_leave_confirmation": False,
        "show_clear_confirmation": False,
        "editor_current_path": [],
        "last_cleanup": datetime.now(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# =============================
# Optimized Screen Handlers
# =============================
def optimized_show_quiz_screen():
    """Optimized quiz screen with reduced reruns."""
    return safe_execute(show_quiz_screen)

def optimized_show_home_screen():
    """Optimized home screen."""
    return safe_execute(show_home_screen)

def optimized_show_folder_view():
    """Optimized folder view."""
    return safe_execute(show_folder_view_screen)
    
# =============================
# Main App
# =============================
def main():
    st.set_page_config(
        page_title="LitmusQ - Professional MCQ Platform",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inject custom CSS
    inject_custom_css()
    
    # Initialize Firebase
    global db
    if 'db' not in globals():
        db = initialize_firebase()
    
    # Initialize session state with stability features
    initialize_state()
    
    # RECOVERY: If user is logged in but user_type is missing, determine it
    if st.session_state.get('logged_in') and 'user_type' not in st.session_state:
        username = st.session_state.get('username')
        if username:
            # First check Excel admin credentials
            admin_credentials = load_admin_credentials()
            if username in admin_credentials:
                st.session_state.user_type = 'admin'
            else:
                # Check Firebase for admin role
                try:
                    if db:
                        user_ref = db.collection('users').document(username)
                        user_doc = user_ref.get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            if user_data.get('role') == 'admin':
                                st.session_state.user_type = 'admin'
                            else:
                                st.session_state.user_type = 'regular'
                        else:
                            st.session_state.user_type = 'regular'
                except Exception as e:
                    st.error(f"Error checking user role: {e}")
                    st.session_state.user_type = 'regular'
    
    # Handle auto-submit if triggered
    handle_auto_submit()
    
    # Perform periodic cleanup
    periodic_cleanup()
    
    # Check memory usage (only if psutil is available)
    if 'psutil' in globals():
        memory_used = check_memory_usage()
        if memory_used > 400:  # Warning at 400MB
            st.sidebar.warning(f"Memory: {memory_used:.1f}MB")
    
    # Check authentication
    if not st.session_state.logged_in:
        safe_execute(show_login_screen)
        st.stop()
    
    # User is logged in - show main app
    if st.session_state.current_screen != "quiz":
        user_type = st.session_state.get('user_type', 'regular')
        username = st.session_state.get('username', 'User')
        
        # Display user info based on role
        if user_type == 'admin':
            st.sidebar.markdown(f"### Welcome, {username}")
            st.sidebar.markdown(
                "<span style='color: #DC2626;'>Admin</span>",
                unsafe_allow_html=True
            )
        elif user_type == 'editor':
            st.sidebar.markdown(f"### Welcome, {username}")
            st.sidebar.markdown(
                "<span style='color: #3B82F6;'>Editor</span>",  # Different color for editor
                unsafe_allow_html=True
            )
        else:  # regular user
            st.sidebar.markdown(f"### 👤 Welcome, {username}")
            st.sidebar.markdown(
                "<span style='color: #059669;'>Student</span>",  # Green for student
                unsafe_allow_html=True
            )
            
        # Show cloud connection status
        if db:
            st.sidebar.markdown(
                "<span style='color: green;'>☁️ Cloud Connected</span>",
                unsafe_allow_html=True
            )
        else:
            st.sidebar.warning("⚠️ Using Local Storage")
            
    # Quick actions panel
    quick_actions_panel()
    
    # Logout button
    if st.session_state.current_screen != "quiz":  
        if st.sidebar.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
            optimize_session_state()  # Clean up before logout
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Scan folder structure on first load with error handling
    if not st.session_state.folder_structure:
        with st.spinner("📁 Scanning question banks..."):
            st.session_state.folder_structure = safe_execute(scan_folder_structure) or {}
    
    # Route to appropriate screen with error handling
    screen_handlers = {
        "home": optimized_show_home_screen,
        "dashboard": lambda: safe_execute(show_student_dashboard),
        "guide": lambda: safe_execute(show_platform_guide),
        "folder_view": optimized_show_folder_view,
        "exam_config": lambda: safe_execute(show_exam_config_screen),
        "quiz": optimized_show_quiz_screen,
        "question_editor": lambda: safe_execute(show_question_editor),
        "retest_config": lambda: safe_execute(show_retest_config, st.session_state.get('retest_config', {})),
        "admin_panel": lambda: safe_execute(show_admin_panel)
    }
    current_screen = st.session_state.current_screen
    handler = screen_handlers.get(current_screen, optimized_show_home_screen)
    
    # Execute the screen handler with error recovery
    try:
        handler()
    except Exception as e:
        st.error("💥 A critical error occurred. Returning to home screen.")
        st.error(f"Error: {str(e)}")
        st.session_state.current_screen = "home"
        optimize_session_state()
        st.rerun()

if __name__ == "__main__":
    main()
