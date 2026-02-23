import streamlit as st
import cv2
import numpy as np
import pandas as pd
import easyocr
import re
from PIL import Image
from database import init_db, connect_db

st.set_page_config(
    page_title="Auto Grading System",
    page_icon="📚",
    layout="wide"
)

# ================= UNIVERSITY THEME =================
st.markdown("""
<style>
.stApp { background-color: #f5f7fa; }

.main-header {
    text-align: center;
    padding: 15px 0;
    background: linear-gradient(90deg, #0b3d91, #1f4e79);
    color: white;
    border-radius: 10px;
    margin-bottom: 20px;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b3d91, #163b5c);
}
[data-testid="stSidebar"] * { color: white !important; }

.block-container { padding-top: 2rem; }

div[data-testid="metric-container"] {
    background-color: white;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}

.stButton>button {
    background-color: #0b3d91;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 8px 20px;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #092e6e;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ================= LOAD OCR =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

# ================= INIT DB =================
init_db()

# ================= SESSION =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.user = ""
    st.session_state.student_name = ""

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

# ================= ANSWER KEYS =================
ANSWER_KEYS = {
"Exercise 1": {1:"1690",2:"18.42",3:"27820",4:"75",5:"30",6:"16416",7:"2258",8:"3960",9:"1463",10:"5200"},
"Exercise 2": {1:"12",2:"44",3:"81",4:"9",5:"16",6:"25",7:"36",8:"49",9:"64",10:"100"},
"Exercise 3": {1:"5",2:"10",3:"15",4:"20",5:"25",6:"30",7:"35",8:"40",9:"45",10:"50"},
"Exercise 4": {1:"3",2:"6",3:"9",4:"12",5:"15",6:"18",7:"21",8:"24",9:"27",10:"30"},
"Exercise 5": {1:"1690",2:"18.42",3:"27820",4:"75",5:"30",6:"16416",7:"2258",8:"3960",9:"1463",10:"5200"},
"Exercise 6": {1:"11",2:"22",3:"33",4:"44",5:"55",6:"66",7:"77",8:"88",9:"99",10:"111"},
"Exercise 7": {1:"7",2:"14",3:"21",4:"28",5:"35",6:"42",7:"49",8:"56",9:"63",10:"70"},
"Exercise 8": {1:"8",2:"16",3:"24",4:"32",5:"40",6:"48",7:"56",8:"64",9:"72",10:"80"},
"Exercise 9": {1:"9",2:"18",3:"27",4:"36",5:"45",6:"54",7:"63",8:"72",9:"81",10:"90"},
"Exercise 10": {1:"1",2:"2",3:"3",4:"4",5:"5",6:"6",7:"7",8:"8",9:"9",10:"10"}
}

EXAM_LIST = list(ANSWER_KEYS.keys())

# ================= OCR CLEAN =================
def clean_text(text):
    if not text:
        return ""
    text = text.strip()
    text = text.replace("O","0").replace("o","0")
    text = re.sub(r"[^0-9.,-]", "", text)
    text = text.replace(",", ".")
    return text

def is_equal(a, b):
    try:
        return float(a) == float(b)
    except:
        return False

# ================= SAVE RESULTS =================
def save_results(student_code, exam_name, results):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM exam_results
        WHERE student_code=%s AND exam_name=%s
    """, (student_code, exam_name))

    for q, pred in results.items():
        correct = ANSWER_KEYS[exam_name][q]
        cur.execute("""
        INSERT INTO exam_results
        (student_code, exam_name, question_no,
        predicted_answer, correct_answer, is_correct)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(student_code, exam_name, q,
             pred, correct, is_equal(pred, correct)))

    conn.commit()
    cur.close()
    conn.close()

# ================= DASHBOARD =================
def dashboard():
    st.title("🎓 Academic Dashboard")
    conn = connect_db()

    if st.session_state.role=="student":
        student_code=st.session_state.user

        scores=pd.read_sql("""
            SELECT exam_name,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
            COUNT(question_no) as total
            FROM exam_results
            WHERE student_code=%s
            GROUP BY exam_name
        """,conn,params=(student_code,))
        conn.close()

        total_exams=len(scores)

        if total_exams>0:
            scores["percentage"]=(scores["score"]/scores["total"])*100
            avg_score=round(scores["percentage"].mean(),2)
        else:
            avg_score=0

        grade = calculate_grade(avg_score)
        status = calculate_status(avg_score)
        class_avg = get_class_average()
        diff = avg_score - class_avg

        col1,col2,col3,col4=st.columns(4)
        col1.metric("Exams Taken",total_exams)
        col2.metric("Average (%)",f"{avg_score}%")
        col3.metric("Grade",grade)
        col4.metric("เทียบค่าเฉลี่ยห้อง",f"{diff:+.2f}%")

        if total_exams>0:
            st.line_chart(scores.set_index("exam_name")["percentage"])
            st.dataframe(scores,use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลคะแนน")

    elif st.session_state.role=="teacher":
        df=pd.read_sql("""
            SELECT student_code,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
            COUNT(question_no) as total
            FROM exam_results
            GROUP BY student_code
        """,conn)
        conn.close()

        if df.empty:
            st.info("ยังไม่มีข้อมูลคะแนน")
            return

        df["percentage"]=(df["score"]/df["total"])*100
        df["grade"]=df["percentage"].apply(calculate_grade)
        df["status"]=df["percentage"].apply(calculate_status)

        total_students=df["student_code"].nunique()
        avg_score=round(df["percentage"].mean(),2)

        col1,col2=st.columns(2)
        col1.metric("Total Students",total_students)
        col2.metric("Class Average (%)",f"{avg_score}%")

        st.dataframe(df,use_container_width=True)
        st.bar_chart(df.set_index("student_code")["percentage"])

# ================= MAIN =================
def main():
    st.sidebar.title("📌 เมนู")

    if not st.session_state.logged_in:
        st.info("กรุณา Login")
    else:
        if st.session_state.role=="student":
            menu=st.sidebar.radio("",["📊 Dashboard","🚪 Logout"])
            if menu=="📊 Dashboard": dashboard()
            if menu=="🚪 Logout":
                st.session_state.clear()
                st.rerun()

        if st.session_state.role=="teacher":
            menu=st.sidebar.radio("",["👩‍🏫 Dashboard","🚪 Logout"])
            if menu=="👩‍🏫 Dashboard": dashboard()
            if menu=="🚪 Logout":
                st.session_state.clear()
                st.rerun()

main()
