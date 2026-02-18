import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost",
    "database": "smartmath",
    "user": "postgres",
    "password": "saedahlyp23."
}

def connect_db():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def init_db():
    conn = connect_db()
    cur = conn.cursor()

    # 👨‍🎓 USERS (นักศึกษา + อาจารย์)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        role TEXT,
        student_id TEXT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    # 📝 SCORES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scores(
        id SERIAL PRIMARY KEY,
        student_email TEXT,
        exercise TEXT,
        q1 INT, q2 INT, q3 INT, q4 INT, q5 INT,
        total INT
    )
    """)

    conn.commit()
    conn.close()
