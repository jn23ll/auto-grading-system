import psycopg2

DB_CONFIG = {
    "host":"localhost",
    "dbname":"grading_db",
    "user":"postgres",
    "password":"saedahlyp23."
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def save_results(student_id, student_name, results, score):
    conn=get_conn()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO students(student_code,student_name)
    VALUES(%s,%s)
    ON CONFLICT(student_code) DO NOTHING
    """,(student_id,student_name))

    cur.execute(
        "SELECT student_id FROM students WHERE student_code=%s",
        (student_id,)
    )
    sid=cur.fetchone()[0]

    cur.execute(
        "INSERT INTO exams(exam_name) VALUES('SmartMath') RETURNING exam_id"
    )
    exam_id=cur.fetchone()[0]

    for q,ans in results.items():
        cur.execute("""
        INSERT INTO exam_results
        (student_id,exam_id,question_no,predicted_answer)
        VALUES(%s,%s,%s,%s)
        """,(sid,exam_id,q,ans))

    conn.commit()
    conn.close()
