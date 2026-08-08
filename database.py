import sqlite3

DB_NAME = "ground_truth.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL UNIQUE,
            claim_text TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            confidence REAL,
            summary TEXT,
            sources TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {DB_NAME}")