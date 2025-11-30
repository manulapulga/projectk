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

# =============================
# Configuration & Theme
# =============================
QUESTION_DATA_FOLDER = "Question_Data_Folder"
LOGIN_FILE_PATH = "data/login_details.xlsx"
USER_PROGRESS_FOLDER = "user_progress"
FORMATTED_QUESTIONS_FILE = "formatted_questions.json"

# =============================
# Add performance config
# =============================
class PerformanceConfig:
    MAX_MEMORY_MB = 500
    CLEANUP_INTERVAL_MINUTES = 5
    MAX_QUESTIONS_PER_LOAD = 200

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
def inject_custom_css():
    st.markdown(f"""
    <style>
    .main .block-container {{
        padding-top: 2rem;
    }}
    
    /* Primary Buttons */
    .stButton>button {{
        background-color: {LITMUSQ_THEME['primary']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        background-color: {LITMUSQ_THEME['accent']};
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    
    /* Enhanced Expander Styling */
    .streamlit-expanderHeader {{
        background-color: {LITMUSQ_THEME['light_bg']};
        border: 1px solid {LITMUSQ_THEME['primary']};
        border-radius: 8px;
        padding: 1rem;
        font-weight: 600;
        color: {LITMUSQ_THEME['primary']};
        margin-bottom: 0.5rem;
    }}
    .streamlit-expanderHeader:hover {{
        background-color: {LITMUSQ_THEME['accent']}15;
        border-color: {LITMUSQ_THEME['accent']};
    }}
    .streamlit-expanderContent {{
        background-color: {LITMUSQ_THEME['background']};
        border: 1px solid #E2E8F0;
        border-top: none;
        border-radius: 0 0 8px 8px;
        padding: 1rem;
    }}
    
    /* Secondary Buttons */
    .secondary-button>button {{
        background-color: {LITMUSQ_THEME['light_bg']};
        color: {LITMUSQ_THEME['primary']};
        border: 2px solid {LITMUSQ_THEME['primary']};
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }}
    
    /* Alerts */
    .stAlert {{
        border-left: 4px solid {LITMUSQ_THEME['secondary']};
        background-color: {LITMUSQ_THEME['light_bg']};
    }}
    
    /* Metrics */
    .metric-container {{
        background-color: {LITMUSQ_THEME['background']};
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid {LITMUSQ_THEME['primary']};
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    
    /* Progress Bar */
    .stProgress > div > div > div > div {{
        background-color: {LITMUSQ_THEME['primary']};
    }}
    
    /* Radio Buttons - Full Width */
    .stRadio > div {{
        background-color: {LITMUSQ_THEME['light_bg']};
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        width: 100% !important;
    }}
    
    /* Make radio button labels full width */
    .stRadio [data-testid="stMarkdownContainer"] {{
        width: 100% !important;
    }}
    
    /* Radio option containers */
    .stRadio > div > label {{
        width: 100% !important;
        padding: 12px 16px !important;
        margin: 4px 0 !important;
        border-radius: 6px !important;
        border: 1px solid #E2E8F0 !important;
        background-color: white !important;
        transition: all 0.2s ease !important;
    }}
    
    .stRadio > div > label:hover {{
        background-color: {LITMUSQ_THEME['light_bg']} !important;
        border-color: {LITMUSQ_THEME['accent']} !important;
    }}
    
    .stRadio > div > label:has(input:checked) {{
        background-color: {LITMUSQ_THEME['light_bg']} !important;
        border-color: {LITMUSQ_THEME['primary']} !important;
        border-width: 2px !important;
    }}
    
    /* Sidebar */
    .css-1d391kg {{
        background-color: {LITMUSQ_THEME['light_bg']};
    }}
    
    /* Custom Header */
    .litmusq-header {{
        background: linear-gradient(135deg, {LITMUSQ_THEME['primary']}, {LITMUSQ_THEME['secondary']});
        border-radius: 10px;
        color: white;
        padding: 0rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    
    /* Badge Styles */
    .badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background-color: {LITMUSQ_THEME['accent']};
        color: white;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 0.1rem;
    }}
    
    /* Question Card */
    .question-card {{
        background-color: {LITMUSQ_THEME['light_bg']};
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid {LITMUSQ_THEME['primary']};
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    
    /* Danger Button */
    .danger-button>button {{
        background-color: {LITMUSQ_THEME['secondary']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }}
    .danger-button>button:hover {{
        background-color: #B91C1C;
        color: white;
    }}

    /* Formatted Content Styles */
    .formatted-content {{
        line-height: 1.6;
        margin: 0.5rem 0;
    }}
    .formatted-content b, .formatted-content strong {{
        color: {LITMUSQ_THEME['primary']};
    }}
    .formatted-content i, .formatted-content em {{
        color: {LITMUSQ_THEME['secondary']};
    }}
    .formatted-content u {{
        text-decoration: underline;
        color: {LITMUSQ_THEME['accent']};
    }}
    
    /* Mobile Responsive */
    @media (max-width: 768px) {{
        .stRadio > div {{
            padding: 0.5rem !important;
        }}
        
        .stRadio > div > label {{
            padding: 10px 12px !important;
            margin: 3px 0 !important;
        }}
        
        .question-card {{
            padding: 1rem !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

# =============================
# Branded Header
# =============================
def show_litmusq_header(subtitle="Professional MCQ Assessment Platform"):
    st.markdown(f"""
    <div class="litmusq-header">
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
    """Enhanced login screen with LitmusQ branding."""
    show_litmusq_header("Assess Better. Learn Faster.")
    
    credentials = load_login_credentials()
    
    if not credentials:
        st.error("No valid login credentials found. Please contact administrator.")
        return False
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown("### 🔐 Please Login")
            
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username", key="login_username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")
                submit_button = st.form_submit_button("🚀 Login to LitmusQ", use_container_width=True)
                
                if submit_button:
                    if not username or not password:
                        st.error("Please enter both username and password")
                        return False
                        
                    if authenticate_user(username, password, credentials):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success(f"🎉 Welcome back, {username}!")
                        # Initialize user progress
                        initialize_user_progress(username)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                        return False
    
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

# =============================
# Rich Text Formatting System
# =============================
def load_formatted_questions():
    """Load formatted questions from JSON file."""
    try:
        if os.path.exists(FORMATTED_QUESTIONS_FILE):
            with open(FORMATTED_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading formatted questions: {e}")
    return {}

def save_formatted_questions(formatted_data):
    """Save formatted questions to JSON file."""
    try:
        with open(FORMATTED_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving formatted questions: {e}")
        return False

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

def is_admin_user():
    """Check if current user is admin."""
    # You can define admin users in your login file or hardcode them
    admin_users = ["admin", "administrator"]  # Add admin usernames here
    return st.session_state.username.lower() in [admin.lower() for admin in admin_users]

def show_question_editor():
    """Admin interface for editing question formatting."""
    show_litmusq_header("📝 Question Formatting Editor")
    
    # Home button
    if st.button("🏠 Home", use_container_width=True, key="editor_home"):
        st.session_state.current_screen = "home"
        st.rerun()
    
    # Check if user is admin
    if not is_admin_user():
        st.error("❌ Access Denied. This section is only available for administrators.")
        st.info("Please contact your system administrator if you need access.")
        return
    
    # Load existing formatted questions
    formatted_questions = load_formatted_questions()
    
    # Folder selection
    st.subheader("Select Question Bank")
    folder_structure = st.session_state.get('folder_structure', {})
    
    if not folder_structure:
        st.error("No question banks found. Please ensure Question_Data_Folder exists.")
        return
    
    # Display current location breadcrumb
    current_path = st.session_state.get('editor_current_path', [])
    if current_path:
        breadcrumb = " > ".join(current_path)
        st.write(f"**Current Location:** `{breadcrumb}`")
        
        # Add back navigation
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ Back", use_container_width=True, key="editor_back"):
                if len(current_path) > 0:
                    st.session_state.editor_current_path = current_path[:-1]
                    st.rerun()
        with col2:
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
            st.markdown("---")
            st.subheader("📝 Question Bank Editor")
            
            qb_path = os.path.join(QUESTION_DATA_FOLDER, *current_path, 'QB.xlsx')
            if os.path.exists(qb_path):
                questions_data = load_questions(qb_path)
                
                if questions_data:
                    # Sheet selection
                    sheet_names = list(questions_data.keys())
                    selected_sheet = st.selectbox("Select Sheet", sheet_names, key="editor_sheet")
                    
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
    st.markdown("---")
    st.subheader(f"✏️ Editing Question {question_index + 1}")
    
    # Display original question for reference
    with st.expander("👀 Original Question (Read-only)", expanded=False):
        st.write(f"**Question:** {question_row['Question']}")
        st.write(f"**Option A:** {question_row.get('Option A', '')}")
        st.write(f"**Option B:** {question_row.get('Option B', '')}")
        st.write(f"**Option C:** {question_row.get('Option C', '')}")
        st.write(f"**Option D:** {question_row.get('Option D', '')}")
        if 'Explanation' in question_row:
            st.write(f"**Explanation:** {question_row.get('Explanation', '')}")
    
    # Generate keys for this question
    question_key = get_question_key(file_path, sheet_name, question_index, "question")
    option_a_key = get_question_key(file_path, sheet_name, question_index, "option_a")
    option_b_key = get_question_key(file_path, sheet_name, question_index, "option_b")
    option_c_key = get_question_key(file_path, sheet_name, question_index, "option_c")
    option_d_key = get_question_key(file_path, sheet_name, question_index, "option_d")
    explanation_key = get_question_key(file_path, sheet_name, question_index, "explanation")
    
    # Load existing formatted content
    default_question = formatted_questions.get(question_key, question_row['Question'])
    default_a = formatted_questions.get(option_a_key, question_row.get('Option A', ''))
    default_b = formatted_questions.get(option_b_key, question_row.get('Option B', ''))
    default_c = formatted_questions.get(option_c_key, question_row.get('Option C', ''))
    default_d = formatted_questions.get(option_d_key, question_row.get('Option D', ''))
    default_explanation = formatted_questions.get(explanation_key, question_row.get('Explanation', ''))
    
    # Formatting guide
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
    
    # Editing form
    with st.form(f"edit_question_{question_index}"):
        st.subheader("Edit Content")
        
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
        st.subheader("👁️ Live Preview")
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
        
        # Form actions
        col1, col2, col3 = st.columns(3)
        with col1:
            save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
        with col2:
            reset_btn = st.form_submit_button("🔄 Reset to Original", use_container_width=True)
        with col3:
            clear_btn = st.form_submit_button("🗑️ Clear Formatting", use_container_width=True)
        
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
            else:
                st.error("❌ Failed to save changes.")
        
        if reset_btn:
            # Reset to original content
            formatted_questions[question_key] = question_row['Question']
            formatted_questions[option_a_key] = question_row.get('Option A', '')
            formatted_questions[option_b_key] = question_row.get('Option B', '')
            formatted_questions[option_c_key] = question_row.get('Option C', '')
            formatted_questions[option_d_key] = question_row.get('Option D', '')
            formatted_questions[explanation_key] = question_row.get('Explanation', '')
            
            if save_formatted_questions(formatted_questions):
                st.success("✅ Reset to original content!")
                st.rerun()
        
        if clear_btn:
            # Remove formatting (use original content)
            for key in [question_key, option_a_key, option_b_key, option_c_key, option_d_key, explanation_key]:
                if key in formatted_questions:
                    del formatted_questions[key]
            
            if save_formatted_questions(formatted_questions):
                st.success("✅ Formatting cleared!")
                st.rerun()

def get_formatted_content(file_path, sheet_name, question_index, field, original_content):
    """Get formatted content if available, otherwise return original."""
    formatted_questions = load_formatted_questions()
    key = get_question_key(file_path, sheet_name, question_index, field)
    return formatted_questions.get(key, original_content)

# =============================
# User Progress & Analytics
# =============================
def ensure_user_progress_folder():
    """Ensure user progress folder exists."""
    os.makedirs(USER_PROGRESS_FOLDER, exist_ok=True)

def get_user_progress_file(username):
    """Get user progress file path."""
    return os.path.join(USER_PROGRESS_FOLDER, f"user_{username}.json")

def initialize_user_progress(username):
    """Initialize user progress data."""
    ensure_user_progress_folder()
    progress_file = get_user_progress_file(username)
    
    if not os.path.exists(progress_file):
        default_progress = {
            "username": username,
            "tests_taken": 0,
            "total_score": 0,
            "average_score": 0,
            "test_history": [],
            "achievements": [],
            "weak_areas": [],
            "strong_areas": [],
            "join_date": datetime.now().isoformat()
        }
        save_user_progress(username, default_progress)

def save_user_progress(username, progress_data):
    """Save user progress to file."""
    try:
        progress_file = get_user_progress_file(username)
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving progress: {e}")

def load_user_progress(username):
    """Load user progress from file."""
    try:
        progress_file = get_user_progress_file(username)
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading progress: {e}")
    return None

def clear_user_progress(username):
    """Clear all performance data for the user."""
    try:
        progress_file = get_user_progress_file(username)
        if os.path.exists(progress_file):
            os.remove(progress_file)
            st.success("✅ All your performance data has been cleared successfully!")
            # Reinitialize with default progress
            initialize_user_progress(username)
            return True
        else:
            st.info("ℹ️ No performance data found to clear.")
            return False
    except Exception as e:
        st.error(f"❌ Error clearing performance data: {e}")
        return False

def update_user_progress(test_results):
    """Update user progress with new test results."""
    username = st.session_state.username
    progress = load_user_progress(username)
    
    if progress:
        # Update basic stats
        progress["tests_taken"] += 1
        progress["total_score"] += test_results["Marks Obtained"]
        progress["average_score"] = progress["total_score"] / progress["tests_taken"]
        
        # Add to test history
        test_history_entry = {
            "exam_name": test_results["Exam Name"],
            "date": datetime.now().isoformat(),
            "score": test_results["Marks Obtained"],
            "total_marks": test_results["Total Marks"],
            "percentage": (test_results["Marks Obtained"] / test_results["Total Marks"]) * 100,
            "correct_answers": test_results["Correct"],
            "total_questions": test_results["Total Questions"]
        }
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
    st.subheader("🗑️ Data Management")
    
    st.warning("⚠️ **Clear Performance Data**")
    st.write("This will permanently delete all your test history, achievements, and performance statistics. This action cannot be undone.")
    
    # Confirmation workflow
    if not st.session_state.get('show_clear_confirmation', False):
        if st.button("🚮 Clear All My Performance Data", type="secondary", key="clear_data_init"):
            st.session_state.show_clear_confirmation = True
            st.rerun()
    else:
        st.error("Are you sure you want to delete ALL your performance data? This action cannot be undone!")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✅ Yes, Delete Everything", type="primary", key="confirm_clear"):
                success = clear_user_progress(st.session_state.username)
                st.session_state.show_clear_confirmation = False
                if success:
                    st.rerun()
        with col2:
            if st.button("❌ Cancel", key="cancel_clear"):
                st.session_state.show_clear_confirmation = False
                st.rerun()
        
        st.info("Note: Your login credentials will remain unchanged. Only your performance data will be deleted.")

def show_student_dashboard():
    """Display student dashboard with progress analytics."""
    show_litmusq_header("Your Learning Dashboard")
    
    # Home button
    if st.button("🏠 Home", use_container_width=False, key="dashboard_home"):
        st.session_state.current_screen = "home"
        st.rerun()
    
    username = st.session_state.username
    progress = load_user_progress(username)
    
    if not progress:
        st.info("📊 Start taking tests to see your progress analytics!")
        # Show clear data section even if no data exists
        show_clear_data_section()
        return
    
    # Key Metrics
    st.subheader("📈 Performance Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Tests Taken", progress["tests_taken"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        avg_score = progress.get("average_score", 0)
        st.metric("Average Score", f"{avg_score:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        total_correct = sum(entry["correct_answers"] for entry in progress["test_history"])
        total_questions = sum(entry["total_questions"] for entry in progress["test_history"])
        accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        st.metric("Overall Accuracy", f"{accuracy:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Achievements", len(progress.get("achievements", [])))
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent Test History
    if progress["test_history"]:
        st.subheader("📋 Recent Tests")
        recent_tests = progress["test_history"][-5:]  # Last 5 tests
        
        for test in reversed(recent_tests):
            test_date = datetime.fromisoformat(test["date"]).strftime("%Y-%m-%d %H:%M")
            percentage = test["percentage"]
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"**{test['exam_name']}**")
            with col2:
                st.write(f"Score: {test['score']}/{test['total_marks']}")
            with col3:
                st.write(f"Accuracy: {percentage:.1f}%")
            with col4:
                st.write(test_date)
            
            st.progress(int(percentage))
            st.markdown("---")
    
    # Achievements
    if progress.get("achievements"):
        st.subheader("🏆 Your Achievements")
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
    """Display folder structure as clickable navigation."""
    if current_path is None:
        current_path = []
    
    for item_name, item_content in folder_structure.items():
        if item_name == '_files':
            continue
            
        folder_key = "->".join(current_path + [item_name])
        has_children = any(k != '_files' for k in item_content.keys())
        has_qb = '_files' in item_content and 'QB.xlsx' in item_content['_files']
        
        # Use columns for better layout
        col1, col2 = st.columns([1, 20])
        with col1:
            if has_qb:
                st.markdown(f"<span style='color: {LITMUSQ_THEME['secondary']}; font-size: 1.2rem;'></span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color: {LITMUSQ_THEME['primary']}; font-size: 1.2rem;'></span>", unsafe_allow_html=True)
        with col2:
            # Use custom button styling
            if st.button(
                item_name, 
                key=f"nav_{folder_key}", 
                use_container_width=True,
                help="Click to explore this folder" + (" (Contains Question Bank)" if has_qb else "")
            ):
                st.session_state.current_path = current_path + [item_name]
                st.session_state.current_screen = "folder_view"
                st.rerun()

def show_folder_view_screen():
    """Show contents of the currently selected folder."""
    current_path = st.session_state.get('current_path', [])
    
    # Home and Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="folder_home"):
            st.session_state.current_screen = "home"
            st.rerun()
    with col2:
        if st.button("← Back", use_container_width=True, key="folder_back"):
            if len(current_path) > 0:
                st.session_state.current_path = current_path[:-1]
            else:
                st.session_state.current_screen = "home"
            st.rerun()
    breadcrumb = " > ".join(current_path) if current_path else ""
    st.write(f"**📍:** `{breadcrumb}`")
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
                    st.markdown(f"""
                    <div style="text-align: center; margin: 2rem 0;">
                        <h2 style="color: {LITMUSQ_THEME['primary']}; 
                                   font-weight: 700; 
                                   margin-bottom: 0.5rem;">
                            🧪 Select Test
                        </h2>
                        <div style="height: 2px; 
                                    background: {LITMUSQ_THEME['primary']}; 
                                    margin: 0 auto; 
                                    width: 50%; 
                                    opacity: 0.7;">
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Mobile-friendly card layout for each test
                    for idx, sheet_name in enumerate(sheet_names):
                        df = questions_data[sheet_name]
                        
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            # Exam name in primary color
                            st.markdown(f"<h4 style='color: {LITMUSQ_THEME['primary']}; margin: 0;'>{sheet_name}</h4>", 
                                       unsafe_allow_html=True)
                            
                            # Compact stats with attractive colors
                            stats_col1, stats_col2 = st.columns(2)
                            with stats_col1:
                                st.markdown(f"<p style='color: {LITMUSQ_THEME['success']}; font-weight: 600; margin: 0.5rem 0;'>❓ {len(df)} Questions</p>", 
                                           unsafe_allow_html=True)
                            with stats_col2:
                                # Create unique key using current path, sheet name, and index
                                current_path_str = '_'.join(current_path) if current_path else 'root'
                                unique_key = f"select_{current_path_str}_{sheet_name}_{idx}"
                                
                                if st.button("**Start Test**", 
                                            key=unique_key,
                                            use_container_width=True,
                                            type="primary"):
                                    st.session_state.selected_sheet = sheet_name
                                    st.session_state.current_screen = "exam_config"
                                    st.rerun()
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                
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
    
    show_litmusq_header(f"Configure Test: {sheet_name}")
    st.write(f"**📍:** `{' > '.join(current_path)}`")
    
    st.metric("Total No. of Questions", len(df_exam))
    # Enhanced metrics with expandable cards
    col1, col2 = st.columns(2)
    with col1:
        
        if "Subject" in df_exam.columns:
            # Get unique subjects (case-insensitive and strip whitespace)
            subjects = df_exam["Subject"].dropna().apply(lambda x: str(x).strip().title()).unique()
            unique_subjects = sorted(subjects)
            
            with st.expander(f"📚 Subjects Covered: **{len(unique_subjects)}**", expanded=False):
                for i, subject in enumerate(unique_subjects, 1):
                    st.write(f"• {subject}")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.metric("No. of Subjects Covered", "N/A")
    
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
    
    st.markdown("---")
    
    # Configuration options
    st.subheader("⚙️ Test Configuration")
    use_final_key = True
    col1, col2 = st.columns(2)
    with col1:
        num_questions = st.number_input(
            "❓ Number of Questions", 
            min_value=1, 
            max_value=len(df_exam),
            value=min(60, len(df_exam)), 
            step=1,
            key="num_questions"
        )
    with col2:
        exam_duration = st.number_input(
            "⏰ Duration (minutes)", 
            min_value=0, 
            max_value=600, 
            value=60, 
            help="Set to 0 for no time limit",
            key="exam_duration_input"
        )
    
    # Advanced options - Use different variable names to avoid session state conflicts
    with st.expander("🎛️ Advanced Options"):
            shuffle_questions = st.checkbox("🔀 Shuffle Questions", value=True, key="shuffle_questions")
            show_live_progress = st.checkbox("📊 Show Live Progress", value=True, key="show_live_progress")
            enable_auto_save = st.checkbox("💾 Auto-save Progress", value=True, key="enable_auto_save")
            full_screen_mode = st.checkbox("🖥️ Full Screen Mode", value=True, key="full_screen_mode")
    
    # Start test button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Test Now", type="primary", use_container_width=True, key="start_test"):
            # Store advanced settings using different variable names
            st.session_state.live_progress_enabled = show_live_progress
            st.session_state.auto_save_enabled = enable_auto_save
            
            start_quiz(df_exam, num_questions, exam_duration, use_final_key, sheet_name)
            st.session_state.current_screen = "quiz"
            st.rerun()

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
    st.markdown(f"""
    <div class="question-card">
        <h3>❓ Question {current_idx + 1}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Render formatted question
    render_formatted_content(formatted_question)
    
    st.markdown("---")
    st.markdown("**Select your answer:**")
    
    current_answer = st.session_state.question_status[current_idx]['answer']
    
    # Use buttons instead of radio for better mobile experience
    col1, col2 = st.columns(2)
    
    with col1:
        # Option A - Add green tick if selected
        option_a_text = f"✅ **A)** {formatted_a}" if current_answer == "A" else f"**A)** {formatted_a}"
        button_style = "primary" if current_answer == "A" else "secondary"
        if st.button(option_a_text, 
                    use_container_width=True, 
                    type=button_style,
                    key=f"option_a_{current_idx}"):
            update_question_status(current_idx, 'answered', "A")
            st.session_state.answers[current_idx] = "A"
            st.rerun()
        
        # Option B - Add green tick if selected
        option_b_text = f"✅ **B)** {formatted_b}" if current_answer == "B" else f"**B)** {formatted_b}"
        button_style = "primary" if current_answer == "B" else "secondary"
        if st.button(option_b_text, 
                    use_container_width=True, 
                    type=button_style,
                    key=f"option_b_{current_idx}"):
            update_question_status(current_idx, 'answered', "B")
            st.session_state.answers[current_idx] = "B"
            st.rerun()
    
    with col2:
        # Option C - Add green tick if selected
        option_c_text = f"✅ **C)** {formatted_c}" if current_answer == "C" else f"**C)** {formatted_c}"
        button_style = "primary" if current_answer == "C" else "secondary"
        if st.button(option_c_text, 
                    use_container_width=True, 
                    type=button_style,
                    key=f"option_c_{current_idx}"):
            update_question_status(current_idx, 'answered', "C")
            st.session_state.answers[current_idx] = "C"
            st.rerun()
        
        # Option D - Add green tick if selected
        option_d_text = f"✅ **D)** {formatted_d}" if current_answer == "D" else f"**D)** {formatted_d}"
        button_style = "primary" if current_answer == "D" else "secondary"
        if st.button(option_d_text, 
                    use_container_width=True, 
                    type=button_style,
                    key=f"option_d_{current_idx}"):
            update_question_status(current_idx, 'answered', "D")
            st.session_state.answers[current_idx] = "D"
            st.rerun()
    
    st.markdown("---")
    
    # Enhanced action buttons
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.button("◀ Previous", use_container_width=True, disabled=current_idx == 0,
                 key=f"prev_{current_idx}",
                 on_click=lambda: setattr(st.session_state, 'current_idx', current_idx - 1))
    
    with col2:
        st.button("Next ▶", use_container_width=True, disabled=current_idx == len(df) - 1,
                 key=f"next_{current_idx}",
                 on_click=lambda: setattr(st.session_state, 'current_idx', current_idx + 1))
    
    with col3:
        button_text = "🟨 Mark Review" if not st.session_state.question_status[current_idx]['marked'] else "↩️ Unmark Review"
        st.button(button_text, use_container_width=True,
                 key=f"mark_{current_idx}",
                 on_click=lambda: toggle_mark_review(current_idx))
    
    with col4:
        if st.button("🗑️ Clear Response", use_container_width=True,
                     key=f"clear_{current_idx}"):
            clear_response(current_idx)
    
    with col5:
        st.button("📤 Submit Test", type="primary", use_container_width=True,
                 key=f"submit_{current_idx}",
                 on_click=lambda: setattr(st.session_state, 'submitted', True))
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
    
    # Handle cleared responses with white square
    if status == 'cleared':
        color = LITMUSQ_THEME['background']  # White background
        text = "⛔"  # White square emoji
        tooltip = "Response cleared"
    elif has_answer and is_marked:
        color = "#FFD700"  # Gold for answered and marked
        text = "🟩"
        tooltip = "Answered & marked for review"
    elif has_answer:
        color = LITMUSQ_THEME['success']  # Green for answered
        text = "✅"
        tooltip = "Answered"
    elif is_marked:
        color = LITMUSQ_THEME['primary']  # Blue for marked
        text = "🟨"
        tooltip = "Marked for Review"
    elif status == 'not_answered':
        color = LITMUSQ_THEME['secondary']  # Red for not answered
        text = "❌"
        tooltip = "Not Answered"
    else:  # not_visited
        color = LITMUSQ_THEME['background']  # White for not visited
        text = str(q_num + 1)  # Show question number
        tooltip = "Not Visited"
    
    return color, text, tooltip

def show_question_palette():
    """Display the question palette with working color coding."""
    st.sidebar.subheader("🎯 Question Palette")
    
    # Enhanced Legend with theme colors
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
    
    st.sidebar.markdown("---")
    
    # Rest of the function remains the same...
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
                    color, text, tooltip = get_question_display_info(q_num)
                    
                    border_color = LITMUSQ_THEME['secondary'] if q_num == st.session_state.current_idx else "#cccccc"
                    
                    button_style = f"""
                    <style>
                    .qbtn-{q_num} {{
                        background-color: {color} !important;
                        border: 2px solid {border_color} !important;
                        border-radius: 5px !important;
                        color: #000000 !important;
                        font-weight: bold !important;
                    }}
                    </style>
                    """
                    st.markdown(button_style, unsafe_allow_html=True)
                    
                    if st.button(
                        text, 
                        key=f"palette_{q_num}", 
                        use_container_width=True,
                        help=f"Q{q_num + 1}: {tooltip}"
                    ):
                        st.session_state.current_idx = q_num
                        if st.session_state.question_status[q_num]['status'] == 'not_visited':
                            update_question_status(q_num, 'not_answered')
                        st.rerun()

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

def show_test_header():
    """Display test header with timer and instructions."""
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 4])
    
    with col1:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.subheader(f"📝 {st.session_state.exam_name}")
        st.write(f"**Question {st.session_state.current_idx + 1} of {len(st.session_state.quiz_questions)}**")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        if st.session_state.end_time and not st.session_state.submitted:
            time_left = st.session_state.end_time - datetime.now()
            seconds_left = time_left.total_seconds()

            if seconds_left <= 0:
                st.session_state.submitted = True
                st.rerun()

            hours, remainder = divmod(int(seconds_left), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_color = get_time_color(seconds_left)

            st.markdown(
                f"<h3 style='color: {time_color}; margin: 0;'>⏰ {hours:02d}:{minutes:02d}</h3>", 
                unsafe_allow_html=True
            )

            st_autorefresh(interval=60000, limit=100, key="timer_refresh")
        else:
            st.metric("⏰ Time Left", "No Limit")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        if 'question_status' in st.session_state:
            total = len(st.session_state.quiz_questions)
            answered = sum(1 for status in st.session_state.question_status.values() 
                           if status['answer'] is not None)
            st.metric("✅ Answered", f"{answered}/{total}") 
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        marked = sum(1 for status in st.session_state.question_status.values() 
                     if status['marked'])
        st.metric("🟨 Marked", marked)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

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

def show_quiz_screen():
    """Main quiz interface with professional layout."""
    if not st.session_state.quiz_started:
        st.error("Quiz not properly initialized. Returning to home.")
        st.session_state.current_screen = "home"
        st.rerun()
        return
    
    if 'question_status' not in st.session_state or not st.session_state.question_status:
        initialize_question_status()
    
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
        show_test_header()  # Moved to bottom
    else:
        show_results_screen()

# =============================
# Enhanced Results Screen
# =============================
def compute_results():
    """Compute results."""
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

    total = int(df["Marks"].sum())
    obtained = int(df["Score"].sum())
    
    attempted = sum(1 for status in st.session_state.question_status.values() 
                   if status['answer'] is not None)
    correct = int(df["Is Correct"].sum())

    summary = {
        "Exam Name": st.session_state.exam_name,
        "Total Questions": len(df),
        "Attempted": attempted,
        "Correct": correct,
        "Total Marks": total,
        "Marks Obtained": obtained,
        "Answer Key Used": "Final" if use_final else "Provisional",
        "Username": st.session_state.username,
        "Percentage": (obtained / total * 100) if total > 0 else 0
    }
    return df, summary

def show_enhanced_detailed_analysis(res_df):
    """Show detailed analysis with formatted content."""
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
        
        with st.expander(f"Question {i+1}", expanded=False):
            st.markdown("**Question:**")
            render_formatted_content(formatted_question)
            
            correct = row["Correct Option Used"]
            chosen = row["Your Answer"]
            
            def render_formatted_option(label, text, is_correct, is_chosen):
                if is_correct and is_chosen:
                    st.markdown(f"**{label})** ✅ Correct - Your Answer")
                    render_formatted_content(text)
                elif is_correct:
                    st.markdown(f"**{label})** ✅ Correct Answer")
                    render_formatted_content(text)
                elif is_chosen:
                    st.markdown(f"**{label})** ❌ Your Answer")
                    render_formatted_content(text)
                else:
                    st.markdown(f"**{label})**")
                    render_formatted_content(text)
            
            render_formatted_option("A", formatted_a, "A" == correct, "A" == chosen)
            render_formatted_option("B", formatted_b, "B" == correct, "B" == chosen)
            render_formatted_option("C", formatted_c, "C" == correct, "C" == chosen)
            render_formatted_option("D", formatted_d, "D" == correct, "D" == chosen)
            
            if formatted_explanation:
                st.markdown("**Explanation:**")
                render_formatted_content(formatted_explanation)

def show_results_screen():
    """Display enhanced results after quiz completion."""
    res_df, summary = compute_results()
    
    show_litmusq_header("Test Results")
    
    # Update user progress
    update_user_progress(summary)
    
    # Navigation options - Add Home button
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="results_home"):
            st.session_state.current_screen = "home"
            st.rerun()
    with col2:
        if st.button("← Back to Config", use_container_width=True, key="results_back"):
            st.session_state.current_screen = "exam_config"
            st.rerun()
    with col3:
        if st.button("📊 View Analysis", use_container_width=True, key="results_analysis"):
            st.session_state.show_detailed_analysis = not st.session_state.get('show_detailed_analysis', False)
            st.rerun()
    with col4:
        if st.button("🔄 Retake Test", use_container_width=True, key="results_retake"):
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
    with col5:
        if st.button("📈 Dashboard", use_container_width=True, key="results_dashboard"):
            st.session_state.current_screen = "dashboard"
            st.rerun()
    
    # Summary cards with enhanced styling
    st.markdown("---")
    st.subheader("📊 Performance Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Total Questions", summary["Total Questions"])
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Attempted", summary["Attempted"])
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Correct Answers", summary["Correct"])
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
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
        st.markdown("---")
        st.subheader("📋 Question-wise Review")
        show_enhanced_detailed_analysis(res_df)
        
# =============================
# Session State Optimization
# =============================
def optimize_session_state():
    """Clean up and optimize session state to prevent bloat."""
    essential_keys = {
        'logged_in', 'username', 'current_screen', 'current_path',
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
    sampled = df.sample(n=n, random_state=np.random.randint(0, 10**9)).reset_index(drop=True)
    st.session_state.quiz_questions = sampled
    st.session_state.order = list(range(len(sampled)))
    st.session_state.answers = {}
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
    
    if 'question_status' in st.session_state:
        del st.session_state.question_status

# =============================
# Enhanced Home Screen
# =============================
def show_home_screen():
    """Display the main folder navigation."""
    show_litmusq_header("Question Bank Navigator")
    
    # Quick actions
    if st.button("🔄 Refresh", use_container_width=True, key="home_refresh"):
        st.session_state.folder_structure = scan_folder_structure()
        st.rerun()

    st.write("Pick Your Test")
    
    folder_structure = st.session_state.get('folder_structure', {})
    if folder_structure:
        display_folder_navigation(folder_structure)
    else:
        st.info("No folder structure found. Make sure 'Question_Data_Folder' exists with proper structure.")

def show_platform_guide():
    """Actual platform guide implementation."""
    show_litmusq_header("About LitmusQ")

    # Home button
    if st.button("🏠 Home", use_container_width=True, key="guide_home"):
        st.session_state.current_screen = "home"
        st.rerun()

    st.markdown("## 🧪 Welcome to LitmusQ!")

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
        if st.sidebar.button("📝 Edit Questions", use_container_width=True, key="sidebar_editor"):
            st.session_state.current_screen = "question_editor"
            st.rerun()
    
    if st.sidebar.button("📊 Performance", use_container_width=True, key="sidebar_dashboard"):
        st.session_state.current_screen = "dashboard"
        st.rerun()
        
    if st.sidebar.button("ℹ️ About LitmusQ", use_container_width=True, key="home_guide"):
        st.session_state.current_screen = "guide"
        st.rerun()
        
    st.sidebar.markdown("---")

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
        "last_cleanup": datetime.now(),  # Add this line
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
    
    # Initialize session state with stability features
    initialize_state()
    
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
        st.sidebar.markdown(f"### 👤 Welcome, **{st.session_state.username}**")
    
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
        "question_editor": lambda: safe_execute(show_question_editor)
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