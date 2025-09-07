import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# =============================
# Configuration
# =============================
DEFAULT_EXCEL_PATH = "questions.xlsx"  # fixed file
REQUIRED_COLUMNS = [
    "Sl No",
    "Medium of Question",
    "Type of Question",
    "Marks",
    "Question",
    "Option A",
    "Option B",
    "Option C",
    "Option D",
    "Correct option (Provisional Answer Key)",
    "Correct Option (Final Answer Key)",
    "Explanation",
    "Difficulty Level",
    "Source of the Question",
    "Subject",
    "Main Topic",
    "Sub Topic",
    "Name of Exam",
    "Category Code",
    "Exam Year",
    "Question Paper Code",
    "Question Booklet alpha code",
    "Question No",
    "Post in which exam is called for",
    "Department",
    "Date of Test",
    "Upload Date of Provisional Answer Key",
    "Upload Date of Final Answer Key",
]


# =============================
# Helpers
# =============================

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {c: str(c).strip() for c in df.columns}
    return df.rename(columns=mapping)


def validate_schema(df: pd.DataFrame) -> list:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def load_questions(path_or_url) -> dict[str, pd.DataFrame]:
    """Load all sheets as {sheet_name: dataframe}."""
    df_dict = pd.read_excel(path_or_url, sheet_name=None, engine="openpyxl")
    clean_dict = {}
    for sheet, df in df_dict.items():
        df = _normalize_columns(df)
        for col in ["Question", "Option A", "Option B", "Option C", "Option D", "Explanation"]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna("").replace("nan", "", regex=False)
        clean_dict[sheet] = df
    return clean_dict


def make_filters(df: pd.DataFrame):
    """Sidebar filter widgets. Returns a filtered df and selection info."""
    st.sidebar.subheader("Filters")

    # Reordered: Exam Year first, Medium last
    cols_to_filter = [
        "Exam Year",
        "Type of Question",
        "Difficulty Level",
        "Subject",
        "Main Topic",
        "Sub Topic",
        "Category Code",
        "Department",
        "Post in which exam is called for",
        "Medium of Question",
    ]

    current = {}
    fdf = df.copy()

    for col in cols_to_filter:
        if col in fdf.columns:
            values = [v for v in sorted(fdf[col].dropna().astype(str).unique()) if v != ""]
            if values:
                sel = st.sidebar.multiselect(col, values, default=[])
                if sel:
                    fdf = fdf[fdf[col].astype(str).isin(sel)]
                current[col] = sel
    return fdf, current


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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def start_quiz(df: pd.DataFrame, n_questions: int, duration_minutes: int,
               use_final_key: bool, exam_name: str):
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


def remaining_time_str():
    if st.session_state.end_time is None:
        return None
    delta = st.session_state.end_time - datetime.now()
    if delta.total_seconds() <= 0:
        return "00:00"
    m, s = divmod(int(delta.total_seconds()), 60)
    return f"{m:02d}:{s:02d}"


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


def show_question(qidx: int):
    df = st.session_state.quiz_questions
    row = df.iloc[qidx]

    st.markdown(f"### Q{qidx + 1}. {row['Question']}")

    options = {
        "A": row.get("Option A", ""),
        "B": row.get("Option B", ""),
        "C": row.get("Option C", ""),
        "D": row.get("Option D", ""),
    }

    prev_answer = st.session_state.answers.get(qidx, None)
    choice = st.radio(
        "Select one:",
        options=[f"A) {options['A']}", f"B) {options['B']}", f"C) {options['C']}", f"D) {options['D']}"],
        index=["A", "B", "C", "D"].index(prev_answer) if prev_answer in ["A", "B", "C", "D"] else 0,
        label_visibility="collapsed",
        key=f"radio_{qidx}",
    )

    chosen = None
    if choice is not None and ")" in choice:
        chosen = choice.split(")", 1)[0]

    if chosen:
        st.session_state.answers[qidx] = chosen

    # Navigation
    cols = st.columns(3)
    with cols[0]:
        if st.button("◀ Previous", disabled=qidx == 0):
            st.session_state.current_idx = max(0, qidx - 1)
            st.rerun()
    with cols[1]:
        if st.button("Next ▶", disabled=qidx == len(df) - 1):
            st.session_state.current_idx = min(len(df) - 1, qidx + 1)
            st.rerun()
    with cols[2]:
        if st.button("Finish & Submit", type="primary"):
            st.session_state.submitted = True
            st.rerun()


def compute_results():
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
    attempted = int(df["Your Answer"].notna().sum())
    correct = int(df["Is Correct"].sum())

    summary = {
        "Exam Name": st.session_state.exam_name,
        "Total Questions": len(df),
        "Attempted": attempted,
        "Correct": correct,
        "Total Marks": total,
        "Marks Obtained": obtained,
        "Answer Key Used": "Final" if use_final else "Provisional",
    }
    return df, summary


# =============================
# UI
# =============================

st.set_page_config(page_title="MCQ Test Platform", layout="wide")
st.title("Online Test Platform")

initialize_state()

# Load Excel once
if "loaded_sheets" not in st.session_state:
    try:
        st.session_state.loaded_sheets = load_questions(DEFAULT_EXCEL_PATH)
    except Exception as e:
        st.error("Failed to load questions. Please check the Excel file.")
        st.stop()

# Sidebar exam selection
st.sidebar.subheader("Exam Selection")
exam_names = list(st.session_state.loaded_sheets.keys())
selected_exam = st.sidebar.selectbox("Exam Name", exam_names)

df_exam = st.session_state.loaded_sheets[selected_exam]

# Filters
filtered_df, selections = make_filters(df_exam)

# Quiz settings
st.sidebar.markdown("---")
st.sidebar.subheader("Quiz Settings")
use_final_key = st.sidebar.selectbox("Answer key to use", ["Final", "Provisional"], index=0) == "Final"
num_questions = st.sidebar.number_input(
    "Number of questions", min_value=1, max_value=max(1, len(filtered_df)),
    value=min(20, max(1, len(filtered_df))), step=1
)
duration_minutes = st.sidebar.number_input(
    "Duration (minutes)", min_value=0, max_value=600, value=0, help="0 means no timer"
)

if st.sidebar.button("Start Quiz", type="primary", disabled=len(filtered_df) == 0):
    start_quiz(filtered_df, num_questions, duration_minutes, use_final_key, selected_exam)
    st.rerun()

# Main display
if not st.session_state.quiz_started:
    st.info("Choose Exam, apply filters, select settings, then click **Start Quiz**.")
    st.write(f"Total number of questions in the selected exam: {len(df_exam)}")
    if len(filtered_df) != len(df_exam):
        st.write(f"Filtered subset size: **{len(filtered_df)}**")

else:
    if st.session_state.end_time:
        left = remaining_time_str()
        if left == "00:00":
            st.warning("Time is over. Auto-submitting…")
            st.session_state.submitted = True
        else:
            st.metric("Time Left", left)

    st.metric("Attempted", value=sum(1 for v in st.session_state.answers.values() if v))

    st.progress(int(100 * (st.session_state.current_idx + 1) / len(st.session_state.quiz_questions)))

    if not st.session_state.submitted:
        show_question(st.session_state.current_idx)
    else:
        res_df, summary = compute_results()
        left, right = st.columns([1, 2])
        with left:
            st.subheader("Summary")
            st.write(pd.DataFrame([summary]).T.rename(columns={0: "Value"}))
            st.download_button(
                label="Download Detailed Results (CSV)",
                data=res_df.to_csv(index=False),
                file_name=f"{summary['Exam Name']}_results.csv",
                mime="text/csv",
            )
        with right:
            st.subheader("Question-wise Review")
            for i, row in res_df.iterrows():
                st.markdown(f"**Q{i+1}. {row['Question']}**")
                correct = row["Correct Option Used"]
                chosen = row["Your Answer"]

                def fmt(label, text):
                    prefix = f"{label}) "
                    if label == correct:
                        return f"✅ **{prefix}{text}**"
                    elif label == chosen:
                        return f"❌ {prefix}{text}"
                    else:
                        return f"{prefix}{text}"

                st.write(fmt("A", row.get("Option A", "")))
                st.write(fmt("B", row.get("Option B", "")))
                st.write(fmt("C", row.get("Option C", "")))
                st.write(fmt("D", row.get("Option D", "")))
                if str(row.get("Explanation", "")).strip():
                    st.info(f"Explanation: {row['Explanation']}")
                st.markdown("---")

        if st.button("Retake with same filters"):
            start_quiz(filtered_df, num_questions, duration_minutes,
                       st.session_state.use_final_key, selected_exam)
            st.rerun()
