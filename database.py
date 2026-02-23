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
        password VARCHAR(100) NOT NULL,
        full_name VARCHAR(200) NOT NULL,
        role VARCHAR(20) DEFAULT 'student',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    ALTER TABLE students
    ADD COLUMN IF NOT EXISTS faculty VARCHAR(200),
    ADD COLUMN IF NOT EXISTS major VARCHAR(200),
    ADD COLUMN IF NOT EXISTS class_group VARCHAR(50),
    ADD COLUMN IF NOT EXISTS year_level VARCHAR(20);
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS answer_keys(
        id SERIAL PRIMARY KEY,
        exam_name VARCHAR(100),
        question_no INT,
        correct_answer VARCHAR(50)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_results(
        id SERIAL PRIMARY KEY,
        student_code VARCHAR(50) REFERENCES students(student_code),
        exam_name VARCHAR(100),
        question_no INT,
        predicted_answer VARCHAR(50),
        correct_answer VARCHAR(50),
        is_correct BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id SERIAL PRIMARY KEY,
        student_code VARCHAR(50) REFERENCES students(student_code),
        date DATE DEFAULT CURRENT_DATE,
        status VARCHAR(10) CHECK (status IN ('present','absent')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
