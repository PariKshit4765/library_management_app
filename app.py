"""Library Management System - Flask application.

Run with:  python app.py   (then open http://127.0.0.1:5000)
Default login: admin / admin123
"""
import os
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash

import database as db

app = Flask(__name__)


def _load_secret_key():
    """Persist a random secret key next to the app so sessions survive restarts."""
    path = os.path.join(db.BASE_DIR, "secret.key")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    return key


app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or _load_secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_db()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def get_conn():
    if "conn" not in g:
        g.conn = db.get_db()
    return g.conn


@app.teardown_appcontext
def close_conn(_exc):
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_post():
    if request.method == "POST":
        sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not sent or sent != session.get("_csrf"):
            abort(400, "Invalid or missing CSRF token. Please reload the page and try again.")


@app.context_processor
def inject_globals():
    return {"today": date.today().isoformat(), "loan_days": db.LOAN_DAYS,
            "fine_per_day": db.FINE_PER_DAY}


def to_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_conn().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def dashboard_stats():
    conn = get_conn()
    today_s = date.today().isoformat()
    return {
        "total_books": conn.execute("SELECT COALESCE(SUM(total_copies),0) FROM books").fetchone()[0],
        "titles": conn.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "available": conn.execute("SELECT COALESCE(SUM(available_copies),0) FROM books").fetchone()[0],
        "members": conn.execute("SELECT COUNT(*) FROM members WHERE status='active'").fetchone()[0],
        "issued": conn.execute("SELECT COUNT(*) FROM issues WHERE status='issued'").fetchone()[0],
        "overdue": conn.execute(
            "SELECT COUNT(*) FROM issues WHERE status='issued' AND due_date < ?", (today_s,)
        ).fetchone()[0],
        "fines": conn.execute("SELECT COALESCE(SUM(fine),0) FROM issues").fetchone()[0],
    }


@app.route("/")
@login_required
def dashboard():
    conn = get_conn()
    recent = conn.execute(
        """SELECT i.id, b.title, m.name AS member, i.issue_date, i.due_date, i.status
           FROM issues i JOIN books b ON b.id = i.book_id JOIN members m ON m.id = i.member_id
           ORDER BY i.id DESC LIMIT 8"""
    ).fetchall()
    by_cat = conn.execute(
        """SELECT COALESCE(c.name, 'Uncategorised') AS name, COUNT(b.id) AS n
           FROM books b LEFT JOIN categories c ON c.id = b.category_id
           GROUP BY name ORDER BY n DESC"""
    ).fetchall()
    return render_template("dashboard.html", stats=dashboard_stats(), recent=recent, by_cat=by_cat)


@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(dashboard_stats())


# --------------------------------------------------------------------------- #
# Books
# --------------------------------------------------------------------------- #
def book_query(q="", category=""):
    sql = """SELECT b.*, c.name AS category FROM books b
             LEFT JOIN categories c ON c.id = b.category_id WHERE 1=1"""
    params = []
    if q:
        sql += " AND (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)"
        params += [f"%{q}%"] * 3
    if category:
        sql += " AND b.category_id = ?"
        params.append(category)
    sql += " ORDER BY b.title"
    return get_conn().execute(sql, params).fetchall()


@app.route("/books")
@login_required
def books():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    cats = get_conn().execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("books.html", books=book_query(q, category), categories=cats,
                           q=q, category=category)


@app.route("/api/books")
@login_required
def api_books():
    rows = book_query(request.args.get("q", "").strip(), request.args.get("category", "").strip())
    return jsonify([dict(r) for r in rows])


def read_book_form():
    f = request.form
    data = {
        "isbn": f.get("isbn", "").strip(),
        "title": f.get("title", "").strip(),
        "author": f.get("author", "").strip(),
        "publisher": f.get("publisher", "").strip(),
        "year": to_int(f.get("year")),
        "category_id": to_int(f.get("category_id")),
        "total_copies": to_int(f.get("total_copies"), 1),
    }
    errors = []
    if not data["isbn"] or not data["title"] or not data["author"]:
        errors.append("ISBN, title and author are required.")
    if data["total_copies"] is None or data["total_copies"] < 1:
        errors.append("Total copies must be at least 1.")
    if data["year"] is not None and not (1000 <= data["year"] <= date.today().year + 1):
        errors.append("Please enter a valid publication year.")
    return data, errors


@app.route("/books/add", methods=["GET", "POST"])
@login_required
def add_book():
    conn = get_conn()
    cats = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        data, errors = read_book_form()
        if not errors:
            try:
                conn.execute(
                    """INSERT INTO books (isbn, title, author, publisher, year, category_id,
                                          total_copies, available_copies)
                       VALUES (:isbn, :title, :author, :publisher, :year, :category_id,
                               :total_copies, :total_copies)""", data)
                conn.commit()
                flash(f"Book '{data['title']}' added.", "success")
                return redirect(url_for("books"))
            except sqlite3.IntegrityError:
                errors.append("A book with this ISBN already exists.")
        for e in errors:
            flash(e, "danger")
        return render_template("book_form.html", book=data, categories=cats, mode="add")
    return render_template("book_form.html", book={}, categories=cats, mode="add")


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    conn = get_conn()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        abort(404)
    cats = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        data, errors = read_book_form()
        on_loan = book["total_copies"] - book["available_copies"]
        if data["total_copies"] is not None and data["total_copies"] < on_loan:
            errors.append(f"Total copies cannot be less than the {on_loan} copies currently on loan.")
        if not errors:
            data["id"] = book_id
            data["available"] = data["total_copies"] - on_loan
            try:
                conn.execute(
                    """UPDATE books SET isbn=:isbn, title=:title, author=:author, publisher=:publisher,
                              year=:year, category_id=:category_id, total_copies=:total_copies,
                              available_copies=:available WHERE id=:id""", data)
                conn.commit()
                flash("Book updated.", "success")
                return redirect(url_for("books"))
            except sqlite3.IntegrityError:
                errors.append("Another book already uses this ISBN.")
        for e in errors:
            flash(e, "danger")
        data["id"] = book_id
        return render_template("book_form.html", book=data, categories=cats, mode="edit")
    return render_template("book_form.html", book=book, categories=cats, mode="edit")


@app.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    conn = get_conn()
    active = conn.execute(
        "SELECT COUNT(*) FROM issues WHERE book_id = ? AND status = 'issued'", (book_id,)
    ).fetchone()[0]
    if active:
        flash("Cannot delete a book that is currently issued.", "danger")
    else:
        history = conn.execute("SELECT COUNT(*) FROM issues WHERE book_id = ?", (book_id,)).fetchone()[0]
        if history:
            flash("Cannot delete a book that has issue history (keeps records consistent). "
                  "Set its copies to match instead.", "danger")
        else:
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            flash("Book deleted.", "success")
    return redirect(url_for("books"))


# --------------------------------------------------------------------------- #
# Members
# --------------------------------------------------------------------------- #
@app.route("/members")
@login_required
def members():
    q = request.args.get("q", "").strip()
    sql = """SELECT m.*, (SELECT COUNT(*) FROM issues i
                          WHERE i.member_id = m.id AND i.status='issued') AS borrowed
             FROM members m WHERE 1=1"""
    params = []
    if q:
        sql += " AND (m.name LIKE ? OR m.email LIKE ? OR m.phone LIKE ?)"
        params += [f"%{q}%"] * 3
    sql += " ORDER BY m.name"
    return render_template("members.html", members=get_conn().execute(sql, params).fetchall(), q=q)


def read_member_form():
    f = request.form
    data = {
        "name": f.get("name", "").strip(),
        "email": f.get("email", "").strip().lower(),
        "phone": f.get("phone", "").strip(),
        "address": f.get("address", "").strip(),
        "status": f.get("status", "active"),
    }
    errors = []
    if not data["name"]:
        errors.append("Name is required.")
    if "@" not in data["email"] or "." not in data["email"].split("@")[-1]:
        errors.append("A valid email address is required.")
    if data["phone"] and not data["phone"].replace("+", "").replace(" ", "").isdigit():
        errors.append("Phone may contain digits only.")
    if data["status"] not in ("active", "inactive"):
        data["status"] = "active"
    return data, errors


@app.route("/members/add", methods=["GET", "POST"])
@login_required
def add_member():
    if request.method == "POST":
        data, errors = read_member_form()
        if not errors:
            try:
                data["join_date"] = date.today().isoformat()
                get_conn().execute(
                    """INSERT INTO members (name, email, phone, address, join_date, status)
                       VALUES (:name, :email, :phone, :address, :join_date, :status)""", data)
                get_conn().commit()
                flash(f"Member '{data['name']}' registered.", "success")
                return redirect(url_for("members"))
            except sqlite3.IntegrityError:
                errors.append("A member with this email already exists.")
        for e in errors:
            flash(e, "danger")
        return render_template("member_form.html", member=data, mode="add")
    return render_template("member_form.html", member={}, mode="add")


@app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
def edit_member(member_id):
    conn = get_conn()
    member = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not member:
        abort(404)
    if request.method == "POST":
        data, errors = read_member_form()
        if not errors:
            data["id"] = member_id
            try:
                conn.execute(
                    """UPDATE members SET name=:name, email=:email, phone=:phone,
                              address=:address, status=:status WHERE id=:id""", data)
                conn.commit()
                flash("Member updated.", "success")
                return redirect(url_for("members"))
            except sqlite3.IntegrityError:
                errors.append("Another member already uses this email.")
        for e in errors:
            flash(e, "danger")
        data["id"] = member_id
        return render_template("member_form.html", member=data, mode="edit")
    return render_template("member_form.html", member=member, mode="edit")


@app.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def delete_member(member_id):
    conn = get_conn()
    history = conn.execute("SELECT COUNT(*) FROM issues WHERE member_id = ?", (member_id,)).fetchone()[0]
    if history:
        flash("This member has borrowing history and cannot be deleted. "
              "Mark the member as inactive instead.", "danger")
    else:
        conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        conn.commit()
        flash("Member deleted.", "success")
    return redirect(url_for("members"))


# --------------------------------------------------------------------------- #
# Issue / Return
# --------------------------------------------------------------------------- #
@app.route("/issue", methods=["GET", "POST"])
@login_required
def issue_book():
    conn = get_conn()
    if request.method == "POST":
        book_id = to_int(request.form.get("book_id"))
        member_id = to_int(request.form.get("member_id"))
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        member = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        error = None
        if not book or not member:
            error = "Please select a valid book and member."
        elif member["status"] != "active":
            error = "This member is inactive and cannot borrow books."
        elif book["available_copies"] < 1:
            error = "No copies of this book are currently available."
        elif conn.execute("SELECT 1 FROM issues WHERE book_id=? AND member_id=? AND status='issued'",
                          (book_id, member_id)).fetchone():
            error = "This member already has a copy of this book."
        elif conn.execute("SELECT COUNT(*) FROM issues WHERE member_id=? AND status='issued'",
                          (member_id,)).fetchone()[0] >= 5:
            error = "Borrowing limit reached (maximum 5 books per member)."
        if error:
            flash(error, "danger")
        else:
            issue_d = date.today()
            due = issue_d + timedelta(days=db.LOAN_DAYS)
            conn.execute(
                "INSERT INTO issues (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
                (book_id, member_id, issue_d.isoformat(), due.isoformat()))
            conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
            conn.commit()
            flash(f"'{book['title']}' issued to {member['name']}. Due on {due.strftime('%d %b %Y')}.", "success")
            return redirect(url_for("issues"))
    books_avail = conn.execute(
        "SELECT id, title, author, available_copies FROM books WHERE available_copies > 0 ORDER BY title"
    ).fetchall()
    members_active = conn.execute(
        "SELECT id, name, email FROM members WHERE status='active' ORDER BY name").fetchall()
    return render_template("issue.html", books=books_avail, members=members_active)


@app.route("/issues")
@login_required
def issues():
    flt = request.args.get("status", "issued")
    if flt not in ("issued", "returned", "overdue", "all"):
        flt = "issued"
    sql = """SELECT i.*, b.title, m.name AS member FROM issues i
             JOIN books b ON b.id = i.book_id JOIN members m ON m.id = i.member_id WHERE 1=1"""
    params = []
    if flt == "issued":
        sql += " AND i.status = 'issued'"
    elif flt == "returned":
        sql += " AND i.status = 'returned'"
    elif flt == "overdue":
        sql += " AND i.status = 'issued' AND i.due_date < ?"
        params.append(date.today().isoformat())
    sql += " ORDER BY i.id DESC"
    rows = []
    for r in get_conn().execute(sql, params).fetchall():
        row = dict(r)
        if r["status"] == "issued":
            row["fine"] = db.calculate_fine(r["due_date"])
            row["overdue"] = r["due_date"] < date.today().isoformat()
        else:
            row["overdue"] = False
        rows.append(row)
    return render_template("issues.html", issues=rows, flt=flt)


@app.route("/return/<int:issue_id>", methods=["POST"])
@login_required
def return_book(issue_id):
    conn = get_conn()
    issue = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    if not issue:
        abort(404)
    if issue["status"] == "returned":
        flash("This book was already returned.", "info")
    else:
        fine = db.calculate_fine(issue["due_date"])
        conn.execute("UPDATE issues SET status='returned', return_date=?, fine=? WHERE id=?",
                     (date.today().isoformat(), fine, issue_id))
        conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
                     (issue["book_id"],))
        conn.commit()
        flash("Book returned successfully." + (f" Fine collected: Rs. {fine}." if fine else ""),
              "success")
    return redirect(request.form.get("next") or url_for("issues"))


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
@app.route("/reports")
@login_required
def reports():
    conn = get_conn()
    today_s = date.today().isoformat()
    overdue = []
    for r in conn.execute(
        """SELECT i.id, b.title, m.name AS member, m.phone, i.issue_date, i.due_date
           FROM issues i JOIN books b ON b.id=i.book_id JOIN members m ON m.id=i.member_id
           WHERE i.status='issued' AND i.due_date < ? ORDER BY i.due_date""", (today_s,)):
        row = dict(r)
        row["days_late"] = (date.today() - date.fromisoformat(r["due_date"])).days
        row["fine"] = db.calculate_fine(r["due_date"])
        overdue.append(row)
    popular = conn.execute(
        """SELECT b.title, b.author, COUNT(i.id) AS times FROM issues i
           JOIN books b ON b.id = i.book_id GROUP BY b.id ORDER BY times DESC, b.title LIMIT 5""").fetchall()
    active_members = conn.execute(
        """SELECT m.name, COUNT(i.id) AS times FROM issues i
           JOIN members m ON m.id = i.member_id GROUP BY m.id ORDER BY times DESC, m.name LIMIT 5""").fetchall()
    collected = conn.execute("SELECT COALESCE(SUM(fine),0) FROM issues WHERE status='returned'").fetchone()[0]
    pending = sum(o["fine"] for o in overdue)
    return render_template("reports.html", overdue=overdue, popular=popular,
                           active_members=active_members, collected=collected, pending=pending)


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="The page you are looking for does not exist."), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message=getattr(e, "description", "Bad request.")), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
