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

# ================= LOAD EASY OCR =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

# ================= INIT DATABASE =================
init_db()

# ================= SESSION =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.user = ""
    st.session_state.student_name = ""

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

# ================= CLEAN TEXT =================
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

# ================= OCR =================
def read_digit_easyocr(gray):
    if gray is None or gray.size == 0:
        return ""
    try:
        gray = cv2.equalizeHist(gray)
        blur = cv2.GaussianBlur(gray, (3,3), 0)
        thresh = cv2.adaptiveThreshold(
            blur,255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11,2
        )
        thresh = cv2.resize(thresh,None,fx=2.0,fy=2.0)

        result = reader.readtext(
            thresh,
            allowlist='0123456789.',
            detail=1,
            paragraph=False
        )
        if not result:
            return ""

        best = max(result,key=lambda x:x[2])
        match = re.search(r"\d+\.?\d*", best[1])
        if match:
            return clean_text(match.group())
        return ""
    except:
        return ""

def crop_handwriting_zone(roi):
    h, w = roi.shape[:2]
    return roi[int(h*0.10):int(h*0.90), int(w*0.15):int(w*0.95)]

# ================= REGISTER =================
def register_page():
    st.title("📝 สมัครสมาชิก")
    role = st.selectbox("สมัครเป็น", ["student","teacher"])
    conn = connect_db()
    cur = conn.cursor()

    with st.form("register"):
        code = st.text_input("Username / รหัส")
        pw = st.text_input("Password", type="password")
        name = st.text_input("ชื่อ-สกุล")
        faculty = st.text_input("คณะ")
        major = st.text_input("สาขา")
        class_group = st.text_input("กลุ่มเรียน")
        year_level = st.selectbox("ชั้นปี", ["1","2","3","4"])

        if st.form_submit_button("สมัคร"):
            cur.execute("SELECT * FROM students WHERE student_code=%s",(code,))
            if cur.fetchone():
                st.error("Username ซ้ำ")
            else:
                cur.execute("""
                INSERT INTO students
                (student_code, password, full_name, role,
                 faculty, major, class_group, year_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,(code, pw, name, role,
                     faculty, major, class_group, year_level))
                conn.commit()
                st.success("สมัครสำเร็จ 🎉")

    cur.close()
    conn.close()

# ================= LOGIN =================
def login_page():
    st.title("🔐 Login")
    code = st.text_input("Username / รหัสนักศึกษา")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("""
        SELECT student_code, full_name, role
        FROM students
        WHERE student_code=%s AND password=%s
        """,(code,pw))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            st.session_state.logged_in = True
            st.session_state.user = user[0]
            st.session_state.student_name = user[1]
            st.session_state.role = user[2]
            st.rerun()
        else:
            st.error("ข้อมูลไม่ถูกต้อง")

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

# ================= OCR PAGE =================
def ocr_page():
    st.title("📄 ตรวจข้อสอบ")

    exam = st.selectbox("เลือกแบบฝึก", EXAM_LIST)
    file = st.file_uploader("Upload กระดาษคำตอบ")

    if file:
        image = Image.open(file).convert("RGB")
        img = np.array(image)
        orig_h, orig_w = img.shape[:2]

        display_boxes = [
            (625,243,788,311),(622,309,785,382),(624,384,784,448),
            (622,454,805,529),(622,533,785,613),(624,619,783,685),
            (622,689,785,754),(622,762,783,823),(622,830,783,895),
            (621,899,783,965),
        ]

        results = {}
        score = 0

        for i,(x1,y1,x2,y2) in enumerate(display_boxes,1):
            x1 = max(0,min(x1,orig_w-1))
            x2 = max(0,min(x2,orig_w))
            y1 = max(0,min(y1,orig_h-1))
            y2 = max(0,min(y2,orig_h))

            if x2<=x1 or y2<=y1:
                results[i]=""
                continue

            roi = img[y1:y2,x1:x2]
            if roi.size==0:
                results[i]=""
                continue

            hand = crop_handwriting_zone(roi)
            if hand.size==0:
                results[i]=""
                continue

            gray=cv2.cvtColor(hand,cv2.COLOR_BGR2GRAY)
            gray=cv2.GaussianBlur(gray,(5,5),0)
            _,gray=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)

            pred=read_digit_easyocr(gray)
            results[i]=pred
            correct=ANSWER_KEYS[exam][i]

            if is_equal(pred,correct):
                st.success(f"ข้อ {i}: {pred} ✓")
                score+=1
            else:
                st.error(f"ข้อ {i}: {pred if pred else '-'} ✗ | ตอบ {correct}")

        st.subheader(f"🎯 คะแนนรวม {score}/10")

        if st.button("บันทึกคะแนน"):
            save_results(st.session_state.user, exam, results)
            st.success("บันทึกคะแนนเรียบร้อยแล้ว")

# ================= DASHBOARD =================
def dashboard():
    st.title("🎓 Academic Dashboard")
    conn = connect_db()

    if st.session_state.role=="student":
        student_code=st.session_state.user

        info=pd.read_sql(
            "SELECT * FROM students WHERE student_code=%s",
            conn,params=(student_code,)
        )

        scores=pd.read_sql("""
            SELECT exam_name,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
            COUNT(question_no) as total
            FROM exam_results
            WHERE student_code=%s
            GROUP BY exam_name
            ORDER BY exam_name
        """,conn,params=(student_code,))

        try:
            attendance=pd.read_sql("""
                SELECT COUNT(*) as total_days,
                SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) as present_days
                FROM attendance
                WHERE student_code=%s
            """,conn,params=(student_code,))
        except:
            attendance=None

        conn.close()

        if info.empty:
            st.error("ไม่พบข้อมูลนักศึกษา")
            return

        st.subheader("👤 Student Profile")
        col1,col2=st.columns(2)
        col1.metric("Student Code",student_code)
        col2.metric("Full Name",info["full_name"].iloc[0])

        st.subheader("📊 Academic Summary")
        total_exams=len(scores)

        if total_exams>0:
            scores["percentage"]=scores.apply(
                lambda r:(r["score"]/r["total"])*100 if r["total"]>0 else 0,
                axis=1)
            avg_score=round(scores["percentage"].mean(),2)
        else:
            avg_score=0

        col1,col2,col3=st.columns(3)
        col1.metric("Exams Taken",total_exams)
        col2.metric("Average Score (%)",f"{avg_score}%")

        if attendance is not None and not attendance.empty:
            td=attendance["total_days"].iloc[0]
            pdays=attendance["present_days"].iloc[0]
            percent_att=round((pdays/td)*100,2) if td and td>0 else 0
            col3.metric("Attendance (%)",f"{percent_att}%")
        else:
            col3.metric("Attendance (%)","-")

        st.subheader("📈 Performance Trend")
        if total_exams>0:
            st.line_chart(scores.set_index("exam_name")["percentage"])
        else:
            st.info("ยังไม่มีข้อมูลคะแนน")

        st.subheader("📋 Exam History")
        if total_exams>0:
            st.dataframe(scores,use_container_width=True)
        else:
            st.info("ยังไม่มีประวัติการสอบ")

    elif st.session_state.role=="teacher":
        st.subheader("👩‍🏫 Teacher Overview")

        df=pd.read_sql("""
            SELECT student_code,
            exam_name,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
            COUNT(question_no) as total
            FROM exam_results
            GROUP BY student_code, exam_name
        """,conn)
        conn.close()

        if df.empty:
            st.info("ยังไม่มีข้อมูลคะแนน")
            return

        df["percentage"]=df.apply(
            lambda r:(r["score"]/r["total"])*100 if r["total"]>0 else 0,
            axis=1)

        st.subheader("📊 Class Summary")
        total_students=df["student_code"].nunique()
        avg_score=round(df["percentage"].mean(),2)

        col1,col2=st.columns(2)
        col1.metric("Total Students",total_students)
        col2.metric("Class Average (%)",f"{avg_score}%")

        st.subheader("🏆 Top 5 Students")
        ranking=df.groupby("student_code")["percentage"].mean().reset_index()
        ranking=ranking.sort_values(by="percentage",ascending=False).head(5)
        st.dataframe(ranking,use_container_width=True)

        st.subheader("📈 Score Distribution")
        st.bar_chart(df.groupby("student_code")["percentage"].mean())

# ================= MAIN =================
def main():
    st.sidebar.title("📌 เมนู")

    if not st.session_state.logged_in:
        menu=st.sidebar.radio("",["🔐 Login","📝 Register"])
        if menu=="🔐 Login": login_page()
        if menu=="📝 Register": register_page()
    else:
        if st.session_state.role=="student":
            menu=st.sidebar.radio("",["📊 Dashboard","📄 ตรวจข้อสอบ","🚪 Logout"])
            if menu=="📊 Dashboard": dashboard()
            if menu=="📄 ตรวจข้อสอบ": ocr_page()
            if menu=="🚪 Logout":
                st.session_state.clear()
                st.rerun()

        if st.session_state.role=="teacher":
            menu=st.sidebar.radio("",["👩‍🏫 Teacher Overview","🚪 Logout"])
            if menu=="👩‍🏫 Teacher Overview": dashboard()
            if menu=="🚪 Logout":
                st.session_state.clear()
                st.rerun()

main()
