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
