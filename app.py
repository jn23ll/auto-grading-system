import streamlit as st
import cv2
import numpy as np
import pandas as pd
import easyocr
import re
from PIL import Image
from database import init_db, connect_db

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

def init_db():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        student_code VARCHAR(50) PRIMARY KEY,
        password VARCHAR(100),
        full_name VARCHAR(200),
        role VARCHAR(20),
        faculty VARCHAR(200),
        major VARCHAR(200),
        class_group VARCHAR(50),
        year_level VARCHAR(20)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_results(
        id SERIAL PRIMARY KEY,
        student_code VARCHAR(50),
        exam_name VARCHAR(100),
        question_no INT,
        predicted_answer VARCHAR(50),
        correct_answer VARCHAR(50),
        is_correct BOOLEAN
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ================= ANSWER KEYS =================
ANSWER_KEYS = {
    f"Exercise {i}": {j: str(j*j) for j in range(1,11)}
    for i in range(1,11)
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

# ================= EASY OCR FUNCTION =================
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
            return match.group()

        return ""

    except:
        return ""

# ================= CROP HANDWRITING =================
def crop_handwriting_zone(roi):
    h, w = roi.shape[:2]
    left   = int(w * 0.15)
    right  = int(w * 0.95)
    top    = int(h * 0.10)
    bottom = int(h * 0.90)
    return roi[top:bottom, left:right]

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
                (student_code,password,full_name,role,
                 faculty,major,class_group,year_level)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (code,pw,name,role,
                 faculty,major,class_group,year_level))

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

    for q,pred in results.items():
        correct = ANSWER_KEYS[exam_name][q]
        cur.execute("""
        INSERT INTO exam_results
        (student_code,exam_name,question_no,
        predicted_answer,correct_answer,is_correct)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(student_code,exam_name,q,
             pred,correct,pred==correct))

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

        display_boxes = [(625,243,788,311)]*10

        results = {}
        score = 0

        for i,(x1,y1,x2,y2) in enumerate(display_boxes,1):
            roi = img[y1:y2, x1:x2]
            hand = crop_handwriting_zone(roi)
            gray = cv2.cvtColor(hand, cv2.COLOR_BGR2GRAY)

            pred = read_digit_easyocr(gray)
            results[i] = pred

            correct = ANSWER_KEYS[exam][i]

            if pred == correct:
                st.success(f"ข้อ {i}: {pred} ✓")
                score += 1
            else:
                st.error(f"ข้อ {i}: {pred} ✗ | ตอบ {correct}")

        st.subheader(f"🎯 คะแนนรวม {score}/10")

        if st.button("บันทึกคะแนน"):
            save_results(st.session_state.user, exam, results)
            st.success("บันทึกแล้ว")

# ================= DASHBOARD STUDENT =================
def dashboard():
    st.title("📊 Dashboard นักศึกษา")

    conn = connect_db()
    cur = conn.cursor()

    # -------------------------------
    # ตรวจสอบว่า column ไหนมีอยู่จริง
    # -------------------------------
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'students'
    """)
    existing_columns = [row[0] for row in cur.fetchall()]

    fields = ["full_name"]
    optional_fields = ["faculty","major","class_group","year_level"]

    for col in optional_fields:
        if col in existing_columns:
            fields.append(col)

    query = f"""
        SELECT {', '.join(fields)}
        FROM students
        WHERE student_code=%s
    """

    student_info = pd.read_sql(query, conn,
                               params=(st.session_state.user,))

    # -------------------------------
    # โหลดคะแนน
    # -------------------------------
    df = pd.read_sql("""
        SELECT exam_name,
        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score,
        COUNT(question_no) as total_questions
        FROM exam_results
        WHERE student_code=%s
        GROUP BY exam_name
        ORDER BY exam_name
    """, conn, params=(st.session_state.user,))

    conn.close()

    # -------------------------------
    # แสดงข้อมูลนักศึกษา
    # -------------------------------
    st.subheader("👤 ข้อมูลนักศึกษา")

    if not student_info.empty:
        info = student_info.iloc[0]

        col1, col2 = st.columns(2)
        col1.metric("รหัสนักศึกษา", st.session_state.user)
        col2.metric("ชื่อ-สกุล", info.get("full_name","-"))

        if "faculty" in info:
            col3, col4 = st.columns(2)
            col3.metric("คณะ", info.get("faculty","-"))
            col4.metric("สาขา", info.get("major","-"))

        if "class_group" in info:
            col5, col6 = st.columns(2)
            col5.metric("กลุ่มเรียน", info.get("class_group","-"))
            col6.metric("ชั้นปี", info.get("year_level","-"))

    st.divider()

    # -------------------------------
    # แสดงคะแนน
    # -------------------------------
    if not df.empty:
        df["เปอร์เซ็นต์"] = (df["score"]/df["total_questions"])*100

        c1,c2,c3 = st.columns(3)
        c1.metric("จำนวนแบบฝึก", len(df))
        c2.metric("คะแนนเฉลี่ย", f"{df['เปอร์เซ็นต์'].mean():.2f}%")
        c3.metric("คะแนนสูงสุด", f"{df['เปอร์เซ็นต์'].max():.2f}%")

        st.divider()
        st.dataframe(df,use_container_width=True)
        st.line_chart(df.set_index("exam_name")["เปอร์เซ็นต์"])

    else:
        st.info("ยังไม่มีประวัติการสอบ")
        
# ================= DASHBOARD TEACHER =================
def teacher_dashboard():
    st.title("👩‍🏫 Teacher Dashboard")
    conn = connect_db()
    df = pd.read_sql("SELECT * FROM exam_results", conn)
    st.dataframe(df)
    conn.close()

# ================= MAIN =================
def main():
    st.sidebar.title("📌 เมนู")

    if not st.session_state.logged_in:
        menu = st.sidebar.radio("",["🔐 Login","📝 Register"])
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
            menu=st.sidebar.radio("",["👩‍🏫 Teacher Dashboard","🚪 Logout"])
            if menu=="👩‍🏫 Teacher Dashboard": teacher_dashboard()
            if menu=="🚪 Logout":
                st.session_state.clear()
                st.rerun()

main()
