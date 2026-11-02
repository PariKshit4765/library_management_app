# Library Management System

A complete web-based library management system built with **Python (Flask)**, **SQLite**, **HTML, CSS and JavaScript**.

## Quick start (Windows)

1. Install **Python 3.9+** from <https://www.python.org/downloads/> (tick **"Add python.exe to PATH"**).
2. Double-click **`run.bat`**.
3. The browser opens at <http://127.0.0.1:5000>. Log in with:

| Username | Password |
|---|---|
| `admin` | `admin123` |

The first run creates a virtual environment, installs Flask, creates `library.db` and loads sample data.
Later runs start in a couple of seconds. Keep the black console window open while you use the app.

### Quick start (macOS / Linux)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Features

* Secure admin login (hashed password, session, CSRF protection on every form)
* **Books** - add, edit, delete, search by title / author / ISBN, filter by category, live search
* **Members** - register, edit, deactivate, delete, search
* **Issue & Return** - 14-day loans, availability tracking, automatic fine of Rs. 2 per late day
* Business rules: no issue when no copies are left, inactive members blocked, max 5 books per member,
  no duplicate active loan of the same title, books/members with history cannot be deleted
* **Dashboard** - live statistics (auto-refresh), recent transactions, books-by-category chart
* **Reports** - overdue list with fines, most borrowed books, most active members, printable
* Responsive layout (works on phones), JSON endpoints `/api/stats` and `/api/books`

## Project structure

```
Library_Management_System/
├── app.py                 Flask routes and business logic
├── database.py            SQLite schema, connection helper, sample data
├── test_app.py            Automated tests (python test_app.py)
├── requirements.txt       Python dependencies
├── run.bat                One-click Windows launcher
├── README.md
├── library.db             Created automatically on first run
├── templates/             HTML (Jinja2) pages
├── static/
│   ├── css/style.css
│   └── js/main.js
└── docs/
    ├── PROJECT_DOCUMENTATION.md
    ├── ER_DIAGRAM.md
    ├── er_diagram.svg
    ├── DATABASE_SCHEMA.md
    └── VIVA_QUESTIONS.md
```

## Sample data

On first run the database is filled with: 1 admin user, 8 categories, 15 books, 6 members and
6 transactions (including two overdue loans so you can see fines straight away).

**Reset to a fresh database:** close the app, delete `library.db`, run `run.bat` again.

## Configuration

Edit the top of `database.py`:

```python
LOAN_DAYS = 14      # loan period
FINE_PER_DAY = 2    # fine in rupees per late day
```

To change the admin password, delete `library.db` after editing the password in `database.py` (`_seed`),
or update the `users` table with a new hash from `werkzeug.security.generate_password_hash`.

## Running the tests

```
venv\Scripts\python.exe test_app.py        (Windows)
python test_app.py                         (macOS / Linux)
```

Tests use a temporary database, so your data is never touched.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Python was not found" | Install Python and tick *Add python.exe to PATH*, then run `run.bat` again. |
| Dependency install fails | Check your internet connection (needed only on the first run). |
| Port 5000 already in use | Close the other program, or change `port=5000` at the bottom of `app.py`. |
| Forgot to keep the console open | The site stops when the console closes; run `run.bat` again. |
