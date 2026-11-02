"""SQLite database layer for the Library Management System.

Running this file directly (python database.py) creates library.db and fills it
with sample records. The app also calls init_db() automatically on start-up.
"""
import os
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")

LOAN_DAYS = 14          # how long a book can be kept
FINE_PER_DAY = 2        # rupees per late day

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS books (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn             TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    author           TEXT NOT NULL,
    publisher        TEXT,
    year             INTEGER,
    category_id      INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    total_copies     INTEGER NOT NULL DEFAULT 1 CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL DEFAULT 1 CHECK (available_copies >= 0)
);

CREATE TABLE IF NOT EXISTS members (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    email     TEXT NOT NULL UNIQUE,
    phone     TEXT,
    address   TEXT,
    join_date TEXT NOT NULL,
    status    TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE IF NOT EXISTS issues (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id),
    member_id   INTEGER NOT NULL REFERENCES members(id),
    issue_date  TEXT NOT NULL,
    due_date    TEXT NOT NULL,
    return_date TEXT,
    fine        INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'issued' CHECK (status IN ('issued', 'returned'))
);

CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_member ON issues(member_id);
CREATE INDEX IF NOT EXISTS idx_issues_book   ON issues(book_id);
"""

CATEGORIES = ["Computer Science", "Fiction", "Science", "History",
              "Mathematics", "Biography", "Self Help", "Literature"]

# isbn, title, author, publisher, year, category, copies
BOOKS = [
    ("9780132350884", "Clean Code", "Robert C. Martin", "Prentice Hall", 2008, "Computer Science", 4),
    ("9780262033848", "Introduction to Algorithms", "Thomas H. Cormen", "MIT Press", 2009, "Computer Science", 5),
    ("9781491946008", "Fluent Python", "Luciano Ramalho", "O'Reilly", 2015, "Computer Science", 3),
    ("9780134685991", "Effective Java", "Joshua Bloch", "Addison-Wesley", 2017, "Computer Science", 2),
    ("9780321125217", "Domain-Driven Design", "Eric Evans", "Addison-Wesley", 2003, "Computer Science", 2),
    ("9780061120084", "To Kill a Mockingbird", "Harper Lee", "Harper Perennial", 1960, "Fiction", 3),
    ("9780451524935", "1984", "George Orwell", "Signet Classic", 1949, "Fiction", 4),
    ("9780743273565", "The Great Gatsby", "F. Scott Fitzgerald", "Scribner", 1925, "Fiction", 3),
    ("9780553380163", "A Brief History of Time", "Stephen Hawking", "Bantam", 1998, "Science", 3),
    ("9780140449136", "The Histories", "Herodotus", "Penguin Classics", 2003, "History", 2),
    ("9780393354324", "Guns, Germs, and Steel", "Jared Diamond", "W. W. Norton", 2017, "History", 2),
    ("9780486653631", "Calculus Made Easy", "Silvanus P. Thompson", "Dover", 1998, "Mathematics", 3),
    ("9788129135728", "Wings of Fire", "A. P. J. Abdul Kalam", "Universities Press", 1999, "Biography", 4),
    ("9780743269513", "The 7 Habits of Highly Effective People", "Stephen R. Covey", "Free Press", 2004, "Self Help", 3),
    ("9780140449266", "The Count of Monte Cristo", "Alexandre Dumas", "Penguin Classics", 2003, "Literature", 2),
]

MEMBERS = [
    ("Aarav Sharma", "aarav.sharma@example.com", "9876500001", "Model Town, Ludhiana"),
    ("Priya Verma", "priya.verma@example.com", "9876500002", "Sarabha Nagar, Ludhiana"),
    ("Rohan Gupta", "rohan.gupta@example.com", "9876500003", "Civil Lines, Ludhiana"),
    ("Simran Kaur", "simran.kaur@example.com", "9876500004", "BRS Nagar, Ludhiana"),
    ("Karan Singh", "karan.singh@example.com", "9876500005", "Dugri, Ludhiana"),
    ("Neha Joshi", "neha.joshi@example.com", "9876500006", "Pakhowal Road, Ludhiana"),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def calculate_fine(due_date_str, return_date=None):
    """Fine = FINE_PER_DAY for every day past the due date."""
    return_date = return_date or date.today()
    due = date.fromisoformat(due_date_str)
    late_days = (return_date - due).days
    return max(0, late_days) * FINE_PER_DAY


def init_db(with_sample_data=True):
    """Create tables and (only on a brand-new database) insert sample data."""
    conn = get_db()
    conn.executescript(SCHEMA)

    already_seeded = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0
    if with_sample_data and not already_seeded:
        _seed(conn)
    conn.commit()
    conn.close()


def _seed(conn):
    today = date.today()

    conn.execute(
        "INSERT INTO users (username, password_hash, full_name) VALUES (?, ?, ?)",
        ("admin", generate_password_hash("admin123"), "Library Administrator"),
    )
    conn.executemany("INSERT INTO categories (name) VALUES (?)", [(c,) for c in CATEGORIES])
    cat_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM categories")}

    for isbn, title, author, pub, year, cat, copies in BOOKS:
        conn.execute(
            """INSERT INTO books (isbn, title, author, publisher, year, category_id,
                                  total_copies, available_copies)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (isbn, title, author, pub, year, cat_ids[cat], copies, copies),
        )

    for name, email, phone, address in MEMBERS:
        join = (today - timedelta(days=120)).isoformat()
        conn.execute(
            "INSERT INTO members (name, email, phone, address, join_date) VALUES (?, ?, ?, ?, ?)",
            (name, email, phone, address, join),
        )

    # Sample transactions: (book_id, member_id, days_ago_issued, returned_after_days or None)
    samples = [
        (1, 1, 30, 12),     # returned on time
        (2, 2, 40, 20),     # returned late -> fine
        (7, 3, 5, None),    # currently issued, not overdue
        (9, 4, 25, None),   # currently issued, overdue
        (13, 5, 20, None),  # currently issued, overdue
        (3, 6, 2, None),    # currently issued
    ]
    for book_id, member_id, ago, returned_after in samples:
        issue = today - timedelta(days=ago)
        due = issue + timedelta(days=LOAN_DAYS)
        if returned_after is None:
            conn.execute(
                "INSERT INTO issues (book_id, member_id, issue_date, due_date, status) "
                "VALUES (?, ?, ?, ?, 'issued')",
                (book_id, member_id, issue.isoformat(), due.isoformat()),
            )
            conn.execute(
                "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,)
            )
        else:
            ret = issue + timedelta(days=returned_after)
            conn.execute(
                "INSERT INTO issues (book_id, member_id, issue_date, due_date, return_date, fine, status) "
                "VALUES (?, ?, ?, ?, ?, ?, 'returned')",
                (book_id, member_id, issue.isoformat(), due.isoformat(), ret.isoformat(),
                 calculate_fine(due.isoformat(), ret)),
            )


if __name__ == "__main__":
    init_db()
    print(f"Database ready at: {DB_PATH}")
