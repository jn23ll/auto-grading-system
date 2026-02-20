import streamlit as st
import cv2
import numpy as np
import os
import torch
import pandas as pd
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from database import init_db, connect_db

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

# ================= TROCR FUNCTION =================
def trocr_read(roi):

    roi = cv2.GaussianBlur(roi,(3,3),0)

    roi = cv2.adaptiveThreshold(
        roi,255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        35,15)

    roi = cv2.resize(roi,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
    roi = cv2.copyMakeBorder(roi,40,40,40,40,cv2.BORDER_CONSTANT,value=0)

    roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2RGB)
    pil_img = Image.fromarray(roi)

    pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values.to(device)
    ids = model.generate(pixel_values, max_length=8, num_beams=5)
    text = processor.batch_decode(ids, skip_special_tokens=True)[0]

    text = "".join([c for c in text if c.isdigit() or c=="."])
    return text.strip()

# ================= HANDWRITING CROP =================
def crop_handwriting_zone(roi):
    h, w = roi.shape[:2]
    left   = int(w * 0.20)
    right  = int(w * 0.95)
    top    = int(h * 0.15)
    bottom = int(h * 0.85)
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
            faculty = st.text_input("คณะ")
            major = st.text_input("สาขา")
            group = st.text_input("กลุ่มเรียน")

            if st.form_submit_button("สมัคร"):
                cur.execute("SELECT * FROM students WHERE student_code=%s",(code,))
                if cur.fetchone():
                    st.error("มีรหัสนี้แล้ว")
                else:
                    cur.execute("""
                    INSERT INTO students
                    (student_code,password,full_name,faculty,major,class_group,role)
                    VALUES(%s,%s,%s,%s,%s,%s,'student')
                    """,(code,pw,name,faculty,major,group))
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
        FROM students WHERE student_code=%s AND password=%s
        """,(code,pw))
        user = cur.fetchone()
        conn.close()

        if user:
            st.session_state.logged_in=True
            st.session_state.user=user[0]
            st.session_state.student_name=user[1]
            st.session_state.role=user[2]
            st.rerun()
        else:
            st.error("ข้อมูลไม่ถูกต้อง")

# ================= SAVE RESULTS =================
def save_results(student_code, exam_name, results):
    conn=connect_db()
    cur=conn.cursor()

    for q,pred in results.items():
        cur.execute("""
        INSERT INTO exam_results
        (student_code,exam_name,question_no,predicted_answer,correct_answer,is_correct)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(student_code,exam_name,q,pred,
             ANSWER_KEYS[exam_name][q],
             pred==ANSWER_KEYS[exam_name][q]))

    conn.commit()
    conn.close()

# ================= OCR PAGE =================
def ocr_page():
    st.title("📄 ตรวจข้อสอบ")
    exam = st.selectbox("เลือกแบบฝึก",EXAM_LIST)
    file = st.file_uploader("Upload กระดาษคำตอบ")

    if file:
        image = Image.open(file).convert("RGB")
        img = np.array(image)

        orig_h, orig_w = img.shape[:2]

        DISPLAY_WIDTH = 900
        scale = DISPLAY_WIDTH / orig_w

        display_boxes = [
            (625,243,788,311),(622,309,785,382),(624,384,784,448),
            (622,454,805,529),(622,533,785,613),(624,619,783,685),
            (622,689,785,754),(622,762,783,823),(622,830,783,895),
            (621,899,783,965),
        ]

        results = {}
        score = 0

        for i,(x1,y1,x2,y2) in enumerate(display_boxes,1):

            x1 = int(x1 / scale)
            y1 = int(y1 / scale)
            x2 = int(x2 / scale)
            y2 = int(y2 / scale)

            roi = img[y1:y2, x1:x2]
            hand = crop_handwriting_zone(roi)
            gray = cv2.cvtColor(hand, cv2.COLOR_BGR2GRAY)

            st.image(gray, caption=f"ROI ข้อ {i}", width=200)

            pred = trocr_read(gray)
            results[i] = pred

            correct = ANSWER_KEYS[exam][i]

            if pred == correct:
                st.success(f"ข้อ {i}: {pred} ✓")
                score += 1
            else:
                st.error(f"ข้อ {i}: {pred} ✗ | ตอบ {correct}")

        st.subheader(f"คะแนนรวม {score}/10")

        if st.button("บันทึกคะแนน"):
            save_results(st.session_state.user,exam,results)
            st.success("บันทึกแล้ว")

# ================= DASHBOARD STUDENT =================
def dashboard():
    st.title("📊 Dashboard นักศึกษา")
    conn=connect_db()

    profile=pd.read_sql("""
    SELECT student_code,full_name,faculty,major,class_group
    FROM students WHERE student_code=%s
    """,conn,params=(st.session_state.user,))
    st.dataframe(profile)

    scores=pd.read_sql("""
    SELECT exam_name,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score
    FROM exam_results
    WHERE student_code=%s GROUP BY exam_name
    """,conn,params=(st.session_state.user,))
    st.dataframe(scores)

    conn.close()

# ================= DASHBOARD TEACHER =================
def teacher_dashboard():
    st.title("👩‍🏫 Teacher Dashboard")
    conn=connect_db()

    df=pd.read_sql("SELECT * FROM exam_results",conn)
    st.dataframe(df)

    summary=pd.read_sql("""
    SELECT student_code,exam_name,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as score
    FROM exam_results GROUP BY student_code,exam_name
    """,conn)

    st.subheader("คะแนนรวม")
    st.dataframe(summary)
    conn.close()

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
                st.session_state.clear(); st.rerun()

        if st.session_state.role=="teacher":
            menu=st.sidebar.radio("",["👩‍🏫 Teacher Dashboard","🚪 Logout"])
            if menu=="👩‍🏫 Teacher Dashboard": teacher_dashboard()
            if menu=="🚪 Logout":
                st.session_state.clear(); st.rerun()

main()
