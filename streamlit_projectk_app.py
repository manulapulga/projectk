import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path

# =============================
# Configuration
# =============================
QUESTION_DATA_FOLDER = "Question_Data_Folder"
LOGIN_FILE_PATH = "data/login_details.xlsx"

# =============================
# Authentication Helpers (unchanged)
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
    st.title("MCQ Test Platform - Login")
    
    credentials = load_login_credentials()
    
    if not credentials:
        st.error("No valid login credentials found. Please contact administrator.")
        return False
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if not username or not password:
                st.error("Please enter both username and password")
                return False
                
            if authenticate_user(username, password, credentials):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome, {username}!")
                st.rerun()
                return True
            else:
                st.error("Invalid username or password")
                return False
    
    return False

# =============================
# Folder Navigation System (unchanged)
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
        
        col1, col2 = st.columns([1, 20])
        with col1:
            if has_qb:
                st.write("📁")
            else:
                st.write("📂")
        with col2:
            if st.button(item_name, key=f"nav_{folder_key}", use_container_width=True):
                st.session_state.current_path = current_path + [item_name]
                st.session_state.current_screen = "folder_view"
                st.rerun()

def show_folder_view_screen():
    """Show contents of the currently selected folder."""
    current_path = st.session_state.get('current_path', [])
    
    breadcrumb = " > ".join([QUESTION_DATA_FOLDER] + current_path)
    st.write(f"**Location:** {breadcrumb}")
    
    if st.button("← Back"):
        if len(current_path) > 0:
            st.session_state.current_path = current_path[:-1]
        else:
            st.session_state.current_screen = "home"
        st.rerun()
    
    folder_structure = st.session_state.folder_structure
    current_level = folder_structure
    for folder in current_path:
        current_level = current_level.get(folder, {})
    
    has_qb = '_files' in current_level and 'QB.xlsx' in current_level['_files']
    
    if has_qb:
        st.success("🎯 Question bank found! You can start a test from this folder.")
        
        qb_path = os.path.join(QUESTION_DATA_FOLDER, *current_path, 'QB.xlsx')
        try:
            questions_data = load_questions(qb_path)
            if questions_data:
                st.session_state.current_qb_path = qb_path
                st.session_state.current_qb_data = questions_data
                
                sheet_names = list(questions_data.keys())
                if sheet_names:
                    st.subheader("Available Exams in this Question Bank:")
                    for sheet_name in sheet_names:
                        df = questions_data[sheet_name]
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{sheet_name}**")
                        with col2:
                            st.write(f"{len(df)} questions")
                        with col3:
                            if st.button(f"Select", key=f"select_{sheet_name}"):
                                st.session_state.selected_sheet = sheet_name
                                st.session_state.current_screen = "exam_config"
                                st.rerun()
                else:
                    st.error("No sheets found in the question bank file.")
                    
        except Exception as e:
            st.error(f"Error loading question bank: {e}")
    
    subfolders = {k: v for k, v in current_level.items() if k != '_files'}
    if subfolders:
        st.subheader("Subfolders:")
        display_folder_navigation(subfolders, current_path)
    elif not has_qb:
        st.info("This folder is empty. Add subfolders or a QB.xlsx file.")

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
    
    if st.button("← Back to Folder"):
        st.session_state.current_screen = "folder_view"
        st.rerun()
    
    st.title(f"Configure Test: {sheet_name}")
    st.write(f"**Location:** {QUESTION_DATA_FOLDER} > {' > '.join(current_path)}")
    st.write(f"Total questions available: {len(df_exam)}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if "Subject" in df_exam.columns:
            subjects = df_exam["Subject"].dropna().unique()
            st.metric("Subjects", len(subjects))
    with col2:
        if "Difficulty Level" in df_exam.columns:
            difficulties = df_exam["Difficulty Level"].dropna().unique()
            st.metric("Difficulty Levels", len(difficulties))
    with col3:
        if "Exam Year" in df_exam.columns:
            years = df_exam["Exam Year"].dropna().unique()
            st.metric("Years", len(years))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        use_final_key = st.selectbox("Answer key to use", ["Final", "Provisional"], index=0) == "Final"
        num_questions = st.number_input(
            "Number of questions", 
            min_value=1, 
            max_value=len(df_exam),
            value=min(20, len(df_exam)), 
            step=1
        )
    with col2:
        duration_minutes = st.number_input(
            "Duration (minutes)", 
            min_value=0, 
            max_value=600, 
            value=60, 
            help="0 means no timer"
        )
        shuffle_questions = st.checkbox("Shuffle questions", value=True)
    
    if st.button("Start Test", type="primary"):
        start_quiz(df_exam, num_questions, duration_minutes, use_final_key, sheet_name)
        st.session_state.current_screen = "quiz"
        st.rerun()

# =============================
# FIXED: Professional Test Interface with Working Color Coding
# =============================

def initialize_question_status():
    """Initialize question status for all questions."""
    total_questions = len(st.session_state.quiz_questions)
    st.session_state.question_status = {}
    
    for i in range(total_questions):
        st.session_state.question_status[i] = {
            'status': 'not_visited',  # not_visited, not_answered, answered, marked_review, answered_marked
            'marked': False,
            'answer': None,
            'time_spent': 0
        }
    
    st.session_state.current_idx = 0
    st.session_state.start_time = datetime.now()

def update_question_status(question_idx, status, answer=None):
    """Update the status of a question."""
    if question_idx in st.session_state.question_status:
        st.session_state.question_status[question_idx]['status'] = status
        if answer is not None:
            st.session_state.question_status[question_idx]['answer'] = answer

def toggle_mark_review(question_idx):
    """Toggle mark for review status."""
    if question_idx in st.session_state.question_status:
        current_marked = st.session_state.question_status[question_idx]['marked']
        st.session_state.question_status[question_idx]['marked'] = not current_marked
        
        # Update status based on marking and answer
        current_answer = st.session_state.question_status[question_idx]['answer']
        if not current_marked:  # Just marked
            if current_answer is not None:
                st.session_state.question_status[question_idx]['status'] = 'answered_marked'
            else:
                st.session_state.question_status[question_idx]['status'] = 'marked_review'
        else:  # Just unmarked
            if current_answer is not None:
                st.session_state.question_status[question_idx]['status'] = 'answered'
            else:
                st.session_state.question_status[question_idx]['status'] = 'not_answered'

def get_question_display_info(q_num):
    """Get display information for a question in the palette."""
    if q_num not in st.session_state.question_status:
        return "#ffffff", str(q_num + 1), "Not visited"  # White
    
    status_info = st.session_state.question_status[q_num]
    has_answer = status_info['answer'] is not None
    is_marked = status_info['marked']
    
    # Determine color and text based on answer and mark status
    if has_answer and is_marked:
        color = "#ffff44"  # Yellow - Answered and marked
        text = "✓★"
        tooltip = "Answered & Marked"
    elif has_answer:
        color = "#44ff44"  # Green - Answered
        text = "✓"
        tooltip = "Answered"
    elif is_marked:
        color = "#4444ff"  # Blue - Marked for review but not answered
        text = "★"
        tooltip = "Marked for Review"
    elif status_info['status'] == 'not_answered':
        color = "#ff4444"  # Red - Not answered but visited
        text = "✗"
        tooltip = "Not Answered"
    else:  # not_visited
        color = "#ffffff"  # White - Not visited
        text = str(q_num + 1)
        tooltip = "Not Visited"
    
    return color, text, tooltip

def show_question_palette():
    """Display the question palette with working color coding."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Question Palette")
    
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
        <div class="color-box" style="background-color: #ffffff;"></div>
        <span>Not Visited</span>
    </div>
    <div class="legend-item">
        <div class="color-box" style="background-color: #ff4444;"></div>
        <span>Not Answered</span>
    </div>
    <div class="legend-item">
        <div class="color-box" style="background-color: #44ff44;"></div>
        <span>Answered</span>
    </div>
    <div class="legend-item">
        <div class="color-box" style="background-color: #4444ff;"></div>
        <span>Marked for Review</span>
    </div>
    <div class="legend-item">
        <div class="color-box" style="background-color: #ffff44;"></div>
        <span>Answered & Marked</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Question grid
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
                    
                    # Highlight current question with red border
                    border_color = "#ff0000" if q_num == st.session_state.current_idx else "#cccccc"
                    
                    # Create custom CSS for the button
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
                        # Update status to visited if not already
                        if st.session_state.question_status[q_num]['status'] == 'not_visited':
                            update_question_status(q_num, 'not_answered')
                        st.rerun()

def show_test_header():
    """Display test header with timer and instructions."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader(f"📝 Test: {st.session_state.exam_name}")
        st.write(f"**Question {st.session_state.current_idx + 1} of {len(st.session_state.quiz_questions)}**")
    
    with col2:
        # Timer
        if st.session_state.end_time:
            time_left = st.session_state.end_time - datetime.now()
            if time_left.total_seconds() <= 0:
                st.session_state.submitted = True
                st.rerun()
            
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Color code based on time left
            if time_left.total_seconds() < 300:  # Less than 5 minutes
                time_color = "red"
            elif time_left.total_seconds() < 900:  # Less than 15 minutes
                time_color = "orange"
            else:
                time_color = "green"
                
            st.markdown(f"<h3 style='color: {time_color};'>⏰ {hours:02d}:{minutes:02d}:{seconds:02d}</h3>", 
                       unsafe_allow_html=True)
        else:
            st.metric("⏰ Time Left", "No Limit")
    
    with col3:
        # Stats
        if 'question_status' in st.session_state:
            total = len(st.session_state.quiz_questions)
            answered = sum(1 for status in st.session_state.question_status.values() 
                          if status['answer'] is not None)
            marked = sum(1 for status in st.session_state.question_status.values() 
                        if status['marked'])
            
            st.metric("✅ Answered", f"{answered}/{total}")
            st.metric("🔵 Marked", marked)
    
    st.markdown("---")

def show_calculator():
    """Display a simple calculator."""
    if st.sidebar.button("🧮 Calculator"):
        st.session_state.show_calculator = not st.session_state.get('show_calculator', False)
        st.rerun()
    
    if st.session_state.get('show_calculator', False):
        st.sidebar.markdown("---")
        st.sidebar.subheader("Calculator")
        
        # Initialize calculator display
        if 'calc_display' not in st.session_state:
            st.session_state.calc_display = "0"
        
        # Display
        st.sidebar.text_input("Result", st.session_state.calc_display, key="calc_output", disabled=True)
        
        # Calculator buttons
        buttons = [
            ['7', '8', '9', '/'],
            ['4', '5', '6', '*'],
            ['1', '2', '3', '-'],
            ['0', '.', '=', '+'],
            ['C', '(', ')', '⌫']
        ]
        
        for row in buttons:
            cols = st.sidebar.columns(len(row))
            for i, btn in enumerate(row):
                with cols[i]:
                    if st.button(btn, key=f"calc_{btn}", use_container_width=True):
                        handle_calculator_input(btn)

def handle_calculator_input(button):
    """Handle calculator button presses."""
    display = st.session_state.calc_display
    
    if button == 'C':
        st.session_state.calc_display = "0"
    elif button == '⌫':
        st.session_state.calc_display = display[:-1] if len(display) > 1 else "0"
    elif button == '=':
        try:
            # Safety check for evaluation
            if any(word in display.lower() for word in ['import', 'exec', 'eval', 'open', 'file']):
                st.session_state.calc_display = "Error"
            else:
                result = eval(display)
                st.session_state.calc_display = str(result)
        except:
            st.session_state.calc_display = "Error"
    else:
        if display == "0" or display == "Error":
            st.session_state.calc_display = button
        else:
            st.session_state.calc_display += button

def show_question_interface():
    """Display the current question with professional interface."""
    df = st.session_state.quiz_questions
    current_idx = st.session_state.current_idx
    
    if current_idx >= len(df):
        st.error("Invalid question index")
        return
        
    row = df.iloc[current_idx]
    
    # Update status to visited if not already
    if st.session_state.question_status[current_idx]['status'] == 'not_visited':
        update_question_status(current_idx, 'not_answered')
    
    # Display question
    st.markdown(f"### ❓ Question {current_idx + 1}")
    st.markdown(f"**{row['Question']}**")
    
    # Display options (without colors in the options)
    options = {
        "A": row.get("Option A", ""),
        "B": row.get("Option B", ""),
        "C": row.get("Option C", ""),
        "D": row.get("Option D", ""),
    }
    
    current_answer = st.session_state.question_status[current_idx]['answer']
    
    # Create radio buttons for options - NO DEFAULT SELECTION
    choice = st.radio(
        "**Select your answer:**",
        options=[
            f"A) {options['A']}",
            f"B) {options['B']}",
            f"C) {options['C']}",
            f"D) {options['D']}"
        ],
        index=None,  # No default selection
        key=f"question_{current_idx}"
    )
    
    # Extract selected option
    selected_option = None
    if choice and ")" in choice:
        selected_option = choice.split(")", 1)[0].strip()
    
    # Update answer and status
    if selected_option and selected_option != current_answer:
        update_question_status(current_idx, 'answered', selected_option)
        st.session_state.answers[current_idx] = selected_option
        st.rerun()
    
    st.markdown("---")
    
    # Action buttons
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("◀ Previous", use_container_width=True, disabled=current_idx == 0):
            st.session_state.current_idx = current_idx - 1
            st.rerun()
    
    with col2:
        if st.button("Next ▶", use_container_width=True, disabled=current_idx == len(df) - 1):
            st.session_state.current_idx = current_idx + 1
            st.rerun()
    
    with col3:
        button_text = "⭐ Mark Review" if not st.session_state.question_status[current_idx]['marked'] else "❌ Unmark Review"
        if st.button(button_text, use_container_width=True):
            toggle_mark_review(current_idx)
            st.rerun()
    
    with col4:
        if st.button("🗑️ Clear Response", use_container_width=True):
            # Clear the answer from session state
            update_question_status(current_idx, 'not_answered', None)
            if current_idx in st.session_state.answers:
                del st.session_state.answers[current_idx]
            
            # Clear the radio button selection by forcing a rerun with cleared state
            st.session_state[f"question_{current_idx}_cleared"] = True
            st.rerun()
    
    with col5:
        if st.button("📤 Submit Test", type="primary", use_container_width=True):
            st.session_state.submitted = True
            st.rerun()

def show_quiz_screen():
    """Main quiz interface with professional layout."""
    if not st.session_state.quiz_started:
        st.error("Quiz not properly initialized. Returning to home.")
        st.session_state.current_screen = "home"
        st.rerun()
        return
    
    # Initialize question status if not done
    if 'question_status' not in st.session_state or not st.session_state.question_status:
        initialize_question_status()
    
    # Display sidebar components
    show_question_palette()
    show_calculator()
    
    # Display main content
    show_test_header()
    
    if not st.session_state.submitted:
        show_question_interface()
    else:
        show_results_screen()

# =============================
# Existing Helper Functions
# =============================

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {c: str(c).strip() for c in df.columns}
    return df.rename(columns=mapping)

def load_questions(file_path):
    """Load questions from Excel file."""
    try:
        df_dict = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")
        clean_dict = {}
        for sheet, df in df_dict.items():
            df = _normalize_columns(df)
            for col in ["Question", "Option A", "Option B", "Option C", "Option D", "Explanation"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).fillna("").replace("nan", "", regex=False)
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
    
    # Get attempted count from question_status
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
    }
    return df, summary

def show_results_screen():
    """Display results after quiz completion."""
    res_df, summary = compute_results()
    
    st.title("🎯 Test Results")
    
    # Navigation options
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back to Configuration"):
            st.session_state.current_screen = "exam_config"
            st.rerun()
    with col2:
        if st.button("📊 View Detailed Analysis"):
            st.session_state.show_detailed_analysis = not st.session_state.get('show_detailed_analysis', False)
            st.rerun()
    with col3:
        if st.button("🔄 Retake Same Test"):
            df_exam = st.session_state.quiz_questions
            start_quiz(
                df_exam, 
                len(df_exam),
                st.session_state.duration_minutes,
                st.session_state.use_final_key, 
                st.session_state.exam_name
            )
            st.session_state.current_screen = "quiz"
            st.rerun()
    
    # Summary cards
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Questions", summary["Total Questions"])
    with col2:
        st.metric("✅ Attempted", summary["Attempted"])
    with col3:
        st.metric("🎯 Correct", summary["Correct"])
    with col4:
        st.metric("📈 Score", f"{summary['Marks Obtained']}/{summary['Total Marks']}")
    
    # Score percentage
    if summary['Total Marks'] > 0:
        percentage = (summary['Marks Obtained'] / summary['Total Marks']) * 100
        st.progress(int(percentage))
        st.write(f"**Overall Score: {percentage:.1f}%**")
    
    # Download button
    st.download_button(
        label="📥 Download Detailed Results (CSV)",
        data=res_df.to_csv(index=False),
        file_name=f"{summary['Exam Name']}_results_{st.session_state.username}.csv",
        mime="text/csv",
    )
    
    # Detailed analysis
    if st.session_state.get('show_detailed_analysis', False):
        st.markdown("---")
        st.subheader("📋 Question-wise Review")
        
        for i, row in res_df.iterrows():
            with st.expander(f"Question {i+1}: {row['Question'][:100]}..."):
                correct = row["Correct Option Used"]
                chosen = row["Your Answer"]
                
                st.markdown(f"**Question:** {row['Question']}")
                
                def fmt_option(label, text):
                    if label == correct and label == chosen:
                        return f"✅ **{label}) {text}** (Correct - Your Answer)"
                    elif label == correct:
                        return f"✅ **{label}) {text}** (Correct Answer)"
                    elif label == chosen:
                        return f"❌ **{label}) {text}** (Your Answer)"
                    else:
                        return f"{label}) {text}"
                
                st.write(fmt_option("A", row.get("Option A", "")))
                st.write(fmt_option("B", row.get("Option B", "")))
                st.write(fmt_option("C", row.get("Option C", "")))
                st.write(fmt_option("D", row.get("Option D", "")))
                
                if str(row.get("Explanation", "")).strip():
                    st.info(f"**Explanation:** {row['Explanation']}")
                
                if i in st.session_state.question_status:
                    status_info = st.session_state.question_status[i]
                    status_text = status_info['status'].replace('_', ' ').title()
                    if status_info['marked']:
                        status_text += " ⭐"
                    st.write(f"**Status:** {status_text}")

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
    st.session_state.duration_minutes = duration_minutes
    
    # Clear previous question status
    if 'question_status' in st.session_state:
        del st.session_state.question_status

def show_home_screen():
    """Display the main folder navigation."""
    st.title("📚 Professional MCQ Test Platform")
    st.write("Navigate through the folder structure to find question banks:")
    
    if st.button("🔄 Refresh Folder Structure"):
        st.session_state.folder_structure = scan_folder_structure()
        st.rerun()
    
    folder_structure = st.session_state.get('folder_structure', {})
    if folder_structure:
        display_folder_navigation(folder_structure)
    else:
        st.info("No folder structure found. Make sure 'Question_Data_Folder' exists with proper structure.")

# =============================
# Modified Initialization and Main App
# =============================

def initialize_state():
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
        "duration_minutes": 0,
        "question_status": {},
        "show_calculator": False,
        "show_detailed_analysis": False,
        "calc_display": "0",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# =============================
# Main App
# =============================

st.set_page_config(page_title="Professional MCQ Test Platform", layout="wide")

# Initialize session state
initialize_state()

# Check authentication
if not st.session_state.logged_in:
    show_login_screen()
    st.stop()

# User is logged in - show main app
st.sidebar.write(f"Logged in as: **{st.session_state.username}**")

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Scan folder structure on first load
if not st.session_state.folder_structure:
    st.session_state.folder_structure = scan_folder_structure()

# Route to appropriate screen
if st.session_state.current_screen == "home":
    show_home_screen()
elif st.session_state.current_screen == "folder_view":
    show_folder_view_screen()
elif st.session_state.current_screen == "exam_config":
    show_exam_config_screen()
elif st.session_state.current_screen == "quiz":
    show_quiz_screen()