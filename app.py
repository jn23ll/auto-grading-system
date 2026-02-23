import streamlit as st
import cv2
import numpy as np
import pandas as pd
import easyocr
import re
from PIL import Image
from database import init_db, connect_db

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="University Auto Grading System",
    page_icon="🎓",
    layout="wide"
)

# ================= UNIVERSITY THEME =================
st.markdown("""
<style>
.stApp { background-color: #f4f6fb; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b3d91, #163b5c);
}
[data-testid="stSidebar"] * { color: white !important; }

div[data-testid="metric-container"] {
    background-color: white;
    border-radius: 15px;
    padding: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.stButton>button {
    background-color: #0b3d91;
    color: white;
    border-radius: 8px;
    border: none;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #082c6a;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ================= INIT =================
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.user = ""

# ================= GRADE SYSTEM =================
def calculate_grade(percent):
    if percent >= 80:
        return "A"
    elif percent >= 70:
        return "B"
    elif percent >= 60:
        return "C"
    elif percent >= 50:
        return "D"
    return "F"

def calculate_status(percent):
    return "ผ่าน" if percent >= 50 else "ไม่ผ่าน"

# ================= CLASS AVERAGE =================
def get_class_average():
    conn = connect_db()
    df = pd.read_sql("""
        SELECT student_code,
        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
        COUNT(question_no) as total
        FROM exam_results
        GROUP BY student_code
    """, conn)
    conn.close()

    if df.empty:
        return 0

    df["percent"] = (df["score"] / df["total"]) * 100
    return round(df["percent"].mean(), 2)

# ================= STUDENT DASHBOARD =================
def student_dashboard():
    st.title("🎓 Student Academic Dashboard")

    conn = connect_db()

    student_code = st.session_state.user

    info = pd.read_sql(
        "SELECT full_name FROM students WHERE student_code=%s",
        conn, params=(student_code,)
    )

    scores = pd.read_sql("""
        SELECT exam_name,
        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
        COUNT(question_no) as total
        FROM exam_results
        WHERE student_code=%s
        GROUP BY exam_name
        ORDER BY exam_name
    """, conn, params=(student_code,))

    conn.close()

    if info.empty:
        st.error("ไม่พบข้อมูล")
        return

    st.subheader(f"👤 {info['full_name'].iloc[0]}")

    if scores.empty:
        st.info("ยังไม่มีข้อมูลคะแนน")
        return

    scores["percent"] = (scores["score"] / scores["total"]) * 100
    avg_score = round(scores["percent"].mean(), 2)
    grade = calculate_grade(avg_score)
    status = calculate_status(avg_score)
    class_avg = get_class_average()
    diff = avg_score - class_avg

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("คะแนนเฉลี่ย", f"{avg_score}%")
    col2.metric("เกรด", grade)
    col3.metric("สถานะ", status)
    col4.metric("เทียบค่าเฉลี่ยห้อง", f"{diff:+.2f}%")

    st.divider()

    st.subheader("📊 กราฟผลการเรียน")
    st.line_chart(scores.set_index("exam_name")["percent"])

    st.subheader("📋 ประวัติการสอบ")
    st.dataframe(scores[["exam_name","score","total","percent"]], use_container_width=True)

# ================= TEACHER DASHBOARD =================
def teacher_dashboard():
    st.title("👩‍🏫 Teacher Dashboard")

    conn = connect_db()

    df = pd.read_sql("""
        SELECT student_code,
        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
        COUNT(question_no) as total
        FROM exam_results
        GROUP BY student_code
    """, conn)

    conn.close()

    if df.empty:
        st.info("ยังไม่มีข้อมูลคะแนน")
        return

    df["percent"] = (df["score"] / df["total"]) * 100

    total_students = df["student_code"].nunique()
    class_avg = round(df["percent"].mean(), 2)

    col1, col2 = st.columns(2)
    col1.metric("จำนวนนักศึกษา", total_students)
    col2.metric("ค่าเฉลี่ยทั้งห้อง", f"{class_avg}%")

    st.divider()

    df["grade"] = df["percent"].apply(calculate_grade)
    df["status"] = df["percent"].apply(calculate_status)

    st.subheader("📋 ตารางคะแนนนักศึกษา")
    st.dataframe(df, use_container_width=True)

    st.subheader("📊 Distribution")
    st.bar_chart(df.set_index("student_code")["percent"])

# ================= LOGIN =================
def login_page():
    st.title("🔐 Login")
    code = st.text_input("Username")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("""
        SELECT student_code, role
        FROM students
        WHERE student_code=%s AND password=%s
        """,(code,pw))
        user = cur.fetchone()
        conn.close()

        if user:
            st.session_state.logged_in = True
            st.session_state.user = user[0]
            st.session_state.role = user[1]
            st.rerun()
        else:
            st.error("ข้อมูลไม่ถูกต้อง")

# ================= MAIN =================
def main():
    st.sidebar.title("🏛 Prince of Songkla University")

    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.role == "student":
            menu = st.sidebar.radio("เมนู",["📊 Dashboard","🚪 Logout"])
            if menu == "📊 Dashboard":
                student_dashboard()
            if menu == "🚪 Logout":
                st.session_state.clear()
                st.rerun()

        elif st.session_state.role == "teacher":
            menu = st.sidebar.radio("เมนู",["👩‍🏫 Dashboard","🚪 Logout"])
            if menu == "👩‍🏫 Dashboard":
                teacher_dashboard()
            if menu == "🚪 Logout":
                st.session_state.clear()
                st.rerun()

main()
