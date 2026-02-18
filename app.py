import streamlit as st
import cv2
import numpy as np
import psycopg2
import torch
import pandas as pd
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# ================= SESSION INIT =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.user = ""
    st.session_state.student_name = ""

# ================= CONNECT DB =================
def connect_db():
    return psycopg2.connect(
        host="localhost",
        database="grading_db",
        user="postgres",
        password="saedahlyp23.",
        port="5432"
    )

# ================= ANSWER KEY =================
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

# ================= LOAD MODEL =================
device = "cuda" if torch.cuda.is_available() else "cpu"

@st.cache_resource
def load_model():
    processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained(
        "microsoft/trocr-base-handwritten").to(device)
    model.eval()
    return processor, model

processor, model = load_model()

def trocr_read(roi):

    # 1) เพิ่มความคมชัด
    roi = cv2.GaussianBlur(roi,(5,5),0)

    # 2) Adaptive threshold (สำคัญมาก)
    roi = cv2.adaptiveThreshold(
        roi,255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,31,15
    )

    # 3) ลบ noise
    kernel = np.ones((3,3),np.uint8)
    roi = cv2.morphologyEx(roi, cv2.MORPH_OPEN, kernel)
    roi = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, kernel)

    # 4) ขยายภาพ (สำคัญมากที่สุด)
    roi = cv2.resize(roi,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)

    # 5) เติมขอบขาวรอบภาพ
    roi = cv2.copyMakeBorder(roi,50,50,50,50,cv2.BORDER_CONSTANT,value=0)

    # แปลงเป็น RGB ให้โมเดล
    roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2RGB)
    pil_img = Image.fromarray(roi)

    pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values.to(device)

    ids = model.generate(
        pixel_values,
        max_length=6,
        num_beams=5,
        early_stopping=True
    )

    text = processor.batch_decode(ids, skip_special_tokens=True)[0]

    # filter เฉพาะตัวเลข
    text = "".join([c for c in text if c.isdigit() or c=="."])

    return text

# ================= REGISTER =================
def register_page():
    st.title("📝 สมัครสมาชิก")

    role = st.selectbox("สมัครเป็น", ["student","teacher"])

    conn = connect_db()
    cur = conn.cursor()

    # ==============================
    # 👨‍🎓 REGISTER STUDENT
    # ==============================
    if role == "student":

        st.subheader("สมัครนักศึกษา")

        with st.form("student_reg"):
            code = st.text_input("รหัสนักศึกษา")
            pw = st.text_input("Password", type="password")
            name = st.text_input("ชื่อ-สกุล")
            faculty = st.text_input("คณะ")
            major = st.text_input("สาขา")
            group = st.text_input("กลุ่มเรียน")

            submit = st.form_submit_button("สมัครสมาชิก")

            if submit:
                cur.execute("SELECT * FROM students WHERE student_code=%s",(code,))
                if cur.fetchone():
                    st.error("มีรหัสนี้แล้ว")
                else:
                    cur.execute("""
                        INSERT INTO students
                        (student_code,password,full_name,faculty,major,class_group,role)
                        VALUES (%s,%s,%s,%s,%s,%s,'student')
                    """,(code,pw,name,faculty,major,group))

                    conn.commit()
                    st.success("สมัครนักศึกษาสำเร็จ 🎉")

    # ==============================
    # 👩‍🏫 REGISTER TEACHER
    # ==============================
    if role == "teacher":

        st.subheader("สมัครอาจารย์")

        with st.form("teacher_reg"):
            code = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            name = st.text_input("ชื่ออาจารย์")

            submit = st.form_submit_button("สมัครสมาชิก")

            if submit:
                cur.execute("SELECT * FROM students WHERE student_code=%s",(code,))
                if cur.fetchone():
                    st.error("มี Username นี้แล้ว")
                else:
                    cur.execute("""
                        INSERT INTO students
                        (student_code,password,full_name,role)
                        VALUES (%s,%s,%s,'teacher')
                    """,(code,pw,name))

                    conn.commit()
                    st.success("สมัครอาจารย์สำเร็จ 🎉")

    conn.close()

# ================= LOGIN =================
def login_page():
    st.title("🔐 Login ระบบตรวจแบบฝึก")

    st.info("นักศึกษาและอาจารย์ใช้หน้า Login เดียวกัน")

    code = st.text_input("Username / รหัสนักศึกษา")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        if code == "" or pw == "":
            st.warning("กรอกข้อมูลให้ครบ")
            return

        conn = connect_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT student_code, full_name, role
            FROM students
            WHERE student_code=%s AND password=%s
        """,(code,pw))

        user = cur.fetchone()
        conn.close()

        if user:
            # บันทึก session
            st.session_state.logged_in = True
            st.session_state.user = user[0]
            st.session_state.student_name = user[1]
            st.session_state.role = user[2]

            # แจ้งสถานะการเข้าใช้งาน
            if user[2] == "teacher":
                st.success("เข้าสู่ระบบในโหมดอาจารย์ 👩‍🏫")
            else:
                st.success("เข้าสู่ระบบในโหมดนักศึกษา 🎓")

            st.rerun()

        else:
            st.error("❌ Username หรือ Password ไม่ถูกต้อง")

# ================= SAVE RESULTS =================
def save_results(student_code, exam_name, results):
    conn=connect_db(); cur=conn.cursor()
    for q,pred in results.items():
        cur.execute("""
        INSERT INTO exam_results(student_code,exam_name,question_no,
        predicted_answer,correct_answer,is_correct)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(student_code,exam_name,q,pred,ANSWER_KEYS[exam_name][q],
             pred==ANSWER_KEYS[exam_name][q]))
    conn.commit(); conn.close()

# ================= OCR PAGE =================
def ocr_page():
    st.title("📄 ตรวจข้อสอบ")
    exam = st.selectbox("เลือกแบบฝึก",EXAM_LIST)
    file = st.file_uploader("Upload")

    if file:
        image = Image.open(file).convert("RGB")
        img = cv2.resize(np.array(image),(2480,3508))
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # เพิ่มความคมทั้งแผ่น
        kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
        gray = cv2.filter2D(gray,-1,kernel)

        results={}; score=0
        for i in range(1,11):
            roi = gray[600+i*200:750+i*200,1600:2200]
            pred = trocr_read(roi)
            results[i]=pred

            correct = ANSWER_KEYS[exam][i]
            if pred==correct:
                st.success(f"ข้อ {i}: {pred} ✓")
                score+=1
            else:
                st.error(f"ข้อ {i}: {pred} ✗ | ตอบ {correct}")

        st.subheader(f"🎯 คะแนนรวม {score}/10")

        if st.button("บันทึกคะแนน"):
            save_results(st.session_state.user,exam,results)
            st.success("บันทึกแล้ว")

# ================= STUDENT DASHBOARD =================
def dashboard():
    st.title("📊 Dashboard นักศึกษา")

    conn=connect_db()

    # โปรไฟล์
    profile=pd.read_sql("""
    SELECT student_code,full_name,faculty,major,class_group
    FROM students WHERE student_code=%s
    """,conn,params=(st.session_state.user,))
    st.subheader("👤 ข้อมูลนักศึกษา")
    st.dataframe(profile,use_container_width=True)

    # คะแนนแต่ละแบบฝึก
    scores=pd.read_sql("""
    SELECT exam_name,
           SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score
    FROM exam_results
    WHERE student_code=%s
    GROUP BY exam_name
    ORDER BY exam_name
    """,conn,params=(st.session_state.user,))
    conn.close()

    st.subheader("📚 คะแนนแต่ละแบบฝึก")
    st.dataframe(scores,use_container_width=True)

# ================= TEACHER DASHBOARD =================
def teacher_dashboard():
    st.title("👩‍🏫 Teacher Dashboard")

    conn = connect_db()

    # ==============================
    # 1) ข้อมูลผลสอบทั้งหมด
    # ==============================
    df = pd.read_sql("""
        SELECT student_code, exam_name, question_no,
               predicted_answer, correct_answer, is_correct
        FROM exam_results
        ORDER BY student_code, exam_name
    """, conn)

    st.subheader("📋 ผลการตรวจทั้งหมด")
    st.dataframe(df, use_container_width=True)

    st.divider()

    # ==============================
    # 2) ค้นหานักศึกษา
    # ==============================
    st.subheader("🔍 ค้นหานักศึกษา")
    search_id = st.text_input("ใส่รหัสนักศึกษา")

    if search_id:
        student_df = df[df["student_code"]==search_id]
        st.dataframe(student_df)

    st.divider()

    # ==============================
    # 3) ตารางคะแนนรวมรายคน
    # ==============================
    st.subheader("🏆 ตารางคะแนนรวมรายคน")

    score_summary = pd.read_sql("""
        SELECT student_code,
               exam_name,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score
        FROM exam_results
        GROUP BY student_code, exam_name
        ORDER BY student_code
    """, conn)

    st.dataframe(score_summary, use_container_width=True)

    st.divider()

    # ==============================
    # 4) สถิติห้องเรียน
    # ==============================
    st.subheader("📊 สถิติภาพรวม")

    stats = pd.read_sql("""
        SELECT exam_name,
               AVG(CASE WHEN is_correct THEN 1 ELSE 0 END)*10 as avg_score
        FROM exam_results
        GROUP BY exam_name
        ORDER BY exam_name
    """, conn)

    st.dataframe(stats)

    conn.close()

    # ==============================
    # 5) Export Excel
    # ==============================
    st.download_button(
        "📥 Export Excel",
        df.to_excel(index=False, engine="openpyxl"),
        "all_scores.xlsx"
    )

# ================= MAIN =================
def main():
    st.sidebar.title("📌 เมนูระบบ")

    if not st.session_state.logged_in:
        choice=st.sidebar.radio("",["🔐 Login","📝 Register"])
        if choice=="🔐 Login": login_page()
        if choice=="📝 Register": register_page()

    else:
        if st.session_state.role == "teacher":
            st.sidebar.success(f"👩‍🏫 {st.session_state.student_name}")
        else:
            st.sidebar.success(f"🎓 {st.session_state.student_name}")

        if st.session_state.role=="student":
            choice=st.sidebar.radio("",["📊 Dashboard","📄 ตรวจข้อสอบ","🚪 Logout"])
            if choice=="📊 Dashboard": dashboard()
            if choice=="📄 ตรวจข้อสอบ": ocr_page()
            if choice=="🚪 Logout":
                st.session_state.clear(); st.rerun()

        if st.session_state.role=="teacher":
            choice=st.sidebar.radio("",["👩‍🏫 Teacher Dashboard","🚪 Logout"])
            if choice=="👩‍🏫 Teacher Dashboard": teacher_dashboard()
            if choice=="🚪 Logout":
                st.session_state.clear(); st.rerun()

main()
