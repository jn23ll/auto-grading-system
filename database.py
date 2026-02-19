import psycopg2
import os

# ================= CONNECT DATABASE =================
def connect_db():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    )

# ================= CREATE TABLES =================
def init_db():
    conn = connect_db()
    cur = conn.cursor()

    # 👨‍🎓 STUDENTS + TEACHERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id SERIAL PRIMARY KEY,
        student_code TEXT UNIQUE,
        password TEXT,
        full_name TEXT,
        faculty TEXT,
        major TEXT,
        class_group TEXT,
        role TEXT
    )
    """)

    # 📄 RESULTS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_results(
        id SERIAL PRIMARY KEY,
        student_code TEXT,
        exam_name TEXT,
        question_no INT,
        predicted_answer TEXT,
        correct_answer TEXT,
        is_correct BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
