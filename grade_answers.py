import os
import re
import easyocr
import psycopg2

# =========================
# CONFIG
# =========================
IMAGE_DIR = "cropped_answers"
EXAM_ID = 1
STUDENT_ID = 1

DB_CONFIG = {
    "dbname": "grading_db",
    "user": "postgres",
    "password": "saedahlyp23.",
    "host": "localhost",
    "port": 5432
}

# =========================
# OCR READER
# =========================
reader = easyocr.Reader(['en'], gpu=False)

# =========================
# NORMALIZE FUNCTION
# =========================
def normalize_number(text: str) -> str:
    if not text:
        return ""
    text = text.replace(" ", "")
    text = text.replace(",", "")
    text = text.replace(".", "")
    text = re.sub(r"[^\d]", "", text)
    return text

# =========================
# CONNECT DATABASE
# =========================
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# =========================
# LOAD ANSWER KEYS
# =========================
cur.execute("""
    SELECT question_no, correct_answer
    FROM answer_keys
    WHERE exam_id = %s
    ORDER BY question_no
""", (EXAM_ID,))

answer_keys = dict(cur.fetchall())

# =========================
# LOAD IMAGES
# =========================
files = sorted(
    [f for f in os.listdir(IMAGE_DIR)
     if f.lower().endswith((".png", ".jpg", ".jpeg"))],
    key=lambda x: int("".join(filter(str.isdigit, x)))
)

print("\n📥 อ่านคำตอบจากภาพ\n")

# =========================
# OCR + GRADING + SAVE
# =========================
score = 0

for i, fname in enumerate(files, start=1):
    img_path = os.path.join(IMAGE_DIR, fname)

    # OCR
    ocr = reader.readtext(img_path, detail=0)
    raw = " ".join(ocr)
    pred = normalize_number(raw)

    # Correct answer
    gt = answer_keys.get(i, "")
    is_correct = pred == gt
    score += is_correct

    # INSERT RESULT
    cur.execute("""
        INSERT INTO exam_results
        (student_id, exam_id, question_no,
         predicted_answer, correct_answer, is_correct)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        STUDENT_ID,
        EXAM_ID,
        i,
        pred,
        gt,
        is_correct
    ))

    print(
        f"ข้อ {i}: อ่านได้ = {pred} | เฉลย = {gt} | "
        f"{'✓ ถูก' if is_correct else '✗ ผิด'}"
    )

# =========================
# COMMIT & CLOSE
# =========================
conn.commit()
cur.close()
conn.close()

print(f"\n🎯 คะแนนรวม: {score} / {len(answer_keys)}")
print("💾 บันทึกผลลง PostgreSQL เรียบร้อยแล้ว")