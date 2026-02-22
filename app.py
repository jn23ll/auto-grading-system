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

# ================= ANSWER KEYS =================
ANSWER_KEYS = {
    "Exercise 1": {1:"1690",2:"18.42",3:"27820",4:"75",5:"30",6:"16416",7:"2258",8:"3960",9:"1463",10:"5200"},
    "Exercise 2": {1:"12",2:"44",3:"81",4:"9",5:"16",6:"25",7:"36",8:"49",9:"64",10:"100"},
    "Exercise 3": {1:"1690",2:"18.42",3:"27820",4:"75",5:"30",6:"16416",7:"2258",8:"3960",9:"1463",10:"5200"},
    "Exercise 4": {1:"12",2:"44",3:"81",4:"9",5:"16",6:"25",7:"36",8:"49",9:"64",10:"100"},
    "Exercise 5": {1:"1690",2:"18.42",3:"27820",4:"75",5:"30",6:"16416",7:"2258",8:"3960",9:"1463",10:"5200"},
    "Exercise 6": {1:"12",2:"44",3:"81",4:"9",5:"16",6:"25",7:"36",8:"49",9:"64",10:"100"},
    "Exercise 7": {1:"1690",2:"18.42",3:"27820",4:"75",5:"30",6:"16416",7:"2258",8:"3960",9:"1463",10:"5200"},
    "Exercise 8": {1:"12",2:"44",3:"81",4:"9",5:"16",6:"25",7:"36",8:"49",9:"64",10:"100"},
    "Exercise 9": {1:"1690",2:"18.42",3:"27820",4:"75",5:"30",6:"16416",7:"2258",8:"3960",9:"1463",10:"5200"},
    "Exercise 10": {1:"12",2:"44",3:"81",4:"9",5:"16",6:"25",7:"36",8:"49",9:"64",10:"100"},
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
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )

        thresh = cv2.resize(
            thresh, None, fx=2.0, fy=2.0,
            interpolation=cv2.INTER_CUBIC
        )

        result = reader.readtext(
            thresh,
            allowlist='0123456789.',
            detail=1,
            paragraph=False
        )

        if not result:
            return ""

        best = max(result, key=lambda x: x[2])
        text = best[1]

        match = re.search(r"\d+\.?\d*", text)
        if match:
            return match.group()

        return ""

    except Exception:
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

    if role == "student":
        with st.form("student_reg"):
            code = st.text_input("รหัสนักศึกษา")
            pw = st.text_input("Password", type="password")
            name = st.text_input("ชื่อ-สกุล")

            if st.form_submit_button("สมัคร"):
                cur.execute("SELECT * FROM students WHERE student_code=%s",(code,))
                if cur.fetchone():
                    st.error("มีรหัสนี้แล้ว")
                else:
                    cur.execute("""
                    INSERT INTO students
                    (student_code,password,full_name,role)
                    VALUES(%s,%s,%s,'student')
                    """,(code,pw,name))
                    conn.commit()
                    st.success("สมัครสำเร็จ 🎉")

    if role == "teacher":
        with st.form("teacher_reg"):
            code = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            name = st.text_input("ชื่ออาจารย์")

            if st.form_submit_button("สมัคร"):
                cur.execute("SELECT * FROM students WHERE student_code=%s",(code,))
                if cur.fetchone():
                    st.error("Username ซ้ำ")
                else:
                    cur.execute("""
                    INSERT INTO students(student_code,password,full_name,role)
                    VALUES(%s,%s,%s,'teacher')
                    """,(code,pw,name))
                    conn.commit()
                    st.success("สมัครอาจารย์สำเร็จ 🎉")

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
             pred,
             correct,
             pred==correct))

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

        display_boxes = [
            (625,243,788,311),(622,309,785,382),(624,384,784,448),
            (622,454,805,529),(622,533,785,613),(624,619,783,685),
            (622,689,785,754),(622,762,783,823),(622,830,783,895),
            (621,899,783,965),
        ]

        results = {}
        score = 0

        for i,(x1,y1,x2,y2) in enumerate(display_boxes,1):
            roi = img[y1:y2, x1:x2]
            hand = crop_handwriting_zone(roi)
            gray = cv2.cvtColor(hand, cv2.COLOR_BGR2GRAY)

            st.image(gray, caption=f"ROI ข้อ {i}", width=200)

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

    scores = pd.read_sql("""
    SELECT exam_name,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score
    FROM exam_results
    WHERE student_code=%s GROUP BY exam_name
    """, conn, params=(st.session_state.user,))
    st.dataframe(scores)

    conn.close()

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
