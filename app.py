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
            return clean_text(match.group())

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
                (student_code, password, full_name, role,
                 faculty, major, class_group, year_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (code, pw, name, role,
                 faculty, major, class_group, year_level)
                )

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

    # 🔹 ลบข้อมูลเดิมก่อน (กันบันทึกซ้ำ)
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
        """,
        (student_code, exam_name, q,
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

        # -------------------------------
        # กำหนดตำแหน่งกรอบ (ไม่ซ้ำกัน)
        # -------------------------------
        display_boxes = [
            (625,243,788,311),
            (622,309,785,382),
            (624,384,784,448),
            (622,454,805,529),
            (622,533,785,613),
            (624,619,783,685),
            (622,689,785,754),
            (622,762,783,823),
            (622,830,783,895),
            (621,899,783,965),
        ]

        results = {}
        score = 0

        for i, (x1, y1, x2, y2) in enumerate(display_boxes, 1):

            # 🔹 clamp กันพิกัดหลุดภาพ
            x1 = max(0, min(x1, orig_w-1))
            x2 = max(0, min(x2, orig_w))
            y1 = max(0, min(y1, orig_h-1))
            y2 = max(0, min(y2, orig_h))

            # 🔹 เช็คว่าพิกัดถูกต้อง
            if x2 <= x1 or y2 <= y1:
                st.error(f"ข้อ {i}: พิกัดผิด")
                results[i] = ""
                continue

            roi = img[y1:y2, x1:x2]

            if roi.size == 0:
                st.error(f"ข้อ {i}: crop ไม่สำเร็จ")
                results[i] = ""
                continue

            hand = crop_handwriting_zone(roi)
            st.image(hand, caption=f"Crop ข้อ {i}")

            if hand.size == 0:
                st.error(f"ข้อ {i}: handwriting zone ว่าง")
                results[i] = ""
                continue

            gray = cv2.cvtColor(hand, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray,(5,5),0)
            _, gray = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)

            pred = read_digit_easyocr(gray)
            results[i] = pred

            correct = ANSWER_KEYS[exam][i]

             if is_equal(pred, correct):
                 st.success(f"ข้อ {i}: {pred} ✓")
                 score += 1
            else:
                st.error(f"ข้อ {i}: {pred if pred else '-'} ✗ | ตอบ {correct}")

                st.subheader(f"🎯 คะแนนรวม {score}/10")
        if st.button("บันทึกคะแนน"):
            save_results(st.session_state.user, exam, results)
            st.success("บันทึกคะแนนเรียบร้อยแล้ว")
            
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
