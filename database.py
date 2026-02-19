import psycopg2
import os
from psycopg2.extras import RealDictCursor

# =====================================================
# CONNECT DATABASE (Streamlit Cloud)
# =====================================================
def connect_db():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        sslmode="require",
        cursor_factory=RealDictCursor
    )

# =====================================================
# INIT DATABASE (Run ตอนเปิดแอปทุกครั้ง)
# =====================================================
def init_db():
    conn = connect_db()
    cur = conn.cursor()

    # 👤 USERS TABLE (Student + Teacher)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        role TEXT,
        student_id TEXT,
        fullname TEXT,
        faculty TEXT,
        major TEXT,
        section TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    # 📝 SCORES TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scores(
        id SERIAL PRIMARY KEY,
        student_email TEXT,
        exercise TEXT,
        q1 INT, q2 INT, q3 INT, q4 INT, q5 INT,
        total INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

# =====================================================
# USER FUNCTIONS
# =====================================================

# สมัครสมาชิก
def register_user(role, student_id, fullname, faculty, major, section, email, password):
    conn = connect_db()
    cur = conn.cursor()

    # 🔎 เช็คซ้ำก่อน
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        conn.close()
        return False

    cur.execute("""
        INSERT INTO users
        (role, student_id, fullname, faculty, major, section, email, password)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """,(role, student_id, fullname, faculty, major, section, email, password))

    conn.commit()
    conn.close()
    return True


# login
def get_user_by_email(email):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=%s",(email,))
    user = cur.fetchone()

    conn.close()
    return user


# ดึงรายชื่อนักศึกษาทั้งหมด (ใช้หน้า Teacher)
def get_all_students():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT student_id, fullname, faculty, major, section, email FROM users WHERE role='student'")
    data = cur.fetchall()

    conn.close()
    return data


# =====================================================
# SCORE FUNCTIONS
# =====================================================

# บันทึกคะแนน
def save_score(email, exercise, scores, total):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scores(student_email, exercise, q1,q2,q3,q4,q5,total)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """,(email, exercise,
         scores[0],scores[1],scores[2],scores[3],scores[4], total))

    conn.commit()
    conn.close()


# คะแนนนักศึกษาคนเดียว
def get_student_scores(email):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT exercise, q1,q2,q3,q4,q5,total,created_at
        FROM scores
        WHERE student_email=%s
        ORDER BY created_at DESC
    """,(email,))
    data = cur.fetchall()

    conn.close()
    return data


# คะแนนทั้งหมด (Teacher dashboard)
def get_all_scores():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM scores
        ORDER BY created_at DESC
    """)
    data = cur.fetchall()

    conn.close()
    return data
