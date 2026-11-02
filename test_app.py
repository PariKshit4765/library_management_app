"""Automated tests. Run with:  python test_app.py
Uses a temporary database, so your real library.db is never touched.
"""
import os
import re
import tempfile
import unittest
from datetime import date, timedelta

import database

_tmp = tempfile.TemporaryDirectory()
database.DB_PATH = os.path.join(_tmp.name, "test_library.db")

import app as lms  # noqa: E402  (must import after DB_PATH override)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        lms.app.config["TESTING"] = True
        self.client = lms.app.test_client()

    # ---- helpers ----
    def token(self, path="/login"):
        html = self.client.get(path).get_data(as_text=True)
        m = re.search(r'name="_csrf" value="([^"]+)"', html)
        self.assertIsNotNone(m, f"no CSRF token on {path}")
        return m.group(1)

    def login(self):
        return self.client.post("/login", data={
            "username": "admin", "password": "admin123", "_csrf": self.token()},
            follow_redirects=True)

    def post(self, path, data, page="/"):
        data = dict(data, _csrf=self.token(page))
        return self.client.post(path, data=data, follow_redirects=True)

    def db_one(self, sql, *args):
        conn = database.get_db()
        try:
            return conn.execute(sql, args).fetchone()
        finally:
            conn.close()

    # ---- tests ----
    def test_01_login_required_and_login(self):
        r = self.client.get("/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        bad = self.client.post("/login", data={"username": "admin", "password": "x",
                                               "_csrf": self.token()}, follow_redirects=True)
        self.assertIn("Invalid username or password", bad.get_data(as_text=True))
        ok = self.login()
        self.assertIn("Dashboard", ok.get_data(as_text=True))

    def test_02_csrf_enforced(self):
        r = self.client.post("/login", data={"username": "admin", "password": "admin123"})
        self.assertEqual(r.status_code, 400)

    def test_03_all_pages_render(self):
        self.login()
        for path in ["/", "/books", "/books?q=python", "/books/add", "/members", "/members/add",
                     "/issue", "/issues", "/issues?status=overdue", "/issues?status=returned",
                     "/issues?status=all", "/reports", "/api/stats", "/api/books?q=clean",
                     "/books/1/edit", "/members/1/edit"]:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
        self.assertEqual(self.client.get("/nope").status_code, 404)
        self.assertEqual(self.client.get("/books/9999/edit").status_code, 404)

    def test_04_book_crud(self):
        self.login()
        r = self.post("/books/add", {"isbn": "TEST-1", "title": "Test Book", "author": "Tester",
                                     "publisher": "P", "year": "2020", "category_id": "1",
                                     "total_copies": "2"}, "/books/add")
        self.assertIn("added", r.get_data(as_text=True))
        book = self.db_one("SELECT * FROM books WHERE isbn='TEST-1'")
        self.assertEqual(book["available_copies"], 2)
        dup = self.post("/books/add", {"isbn": "TEST-1", "title": "Dup", "author": "X",
                                       "total_copies": "1"}, "/books/add")
        self.assertIn("already exists", dup.get_data(as_text=True))
        r = self.post(f"/books/{book['id']}/edit", {"isbn": "TEST-1", "title": "Renamed",
                      "author": "Tester", "total_copies": "3"}, f"/books/{book['id']}/edit")
        self.assertIn("Book updated", r.get_data(as_text=True))
        self.assertEqual(self.db_one("SELECT available_copies a FROM books WHERE id=?", book["id"])["a"], 3)
        r = self.post(f"/books/{book['id']}/delete", {}, "/books")
        self.assertIn("Book deleted", r.get_data(as_text=True))

    def test_05_book_validation(self):
        self.login()
        r = self.post("/books/add", {"isbn": "", "title": "", "author": "", "total_copies": "0"},
                      "/books/add")
        self.assertIn("required", r.get_data(as_text=True))

    def test_06_member_crud(self):
        self.login()
        r = self.post("/members/add", {"name": "Test User", "email": "test.user@example.com",
                                       "phone": "9999999999", "address": "X", "status": "active"},
                      "/members/add")
        self.assertIn("registered", r.get_data(as_text=True))
        m = self.db_one("SELECT * FROM members WHERE email='test.user@example.com'")
        bad = self.post("/members/add", {"name": "A", "email": "not-an-email"}, "/members/add")
        self.assertIn("valid email", bad.get_data(as_text=True))
        dup = self.post("/members/add", {"name": "B", "email": "test.user@example.com"}, "/members/add")
        self.assertIn("already exists", dup.get_data(as_text=True))
        r = self.post(f"/members/{m['id']}/delete", {}, "/members")
        self.assertIn("Member deleted", r.get_data(as_text=True))

    def test_07_issue_and_return_with_fine(self):
        self.login()
        # Fresh book and member so the test is independent of sample data
        self.post("/books/add", {"isbn": "FLOW-1", "title": "Flow Book", "author": "A",
                                 "total_copies": "1"}, "/books/add")
        self.post("/members/add", {"name": "Flow Member", "email": "flow@example.com"}, "/members/add")
        book = self.db_one("SELECT id FROM books WHERE isbn='FLOW-1'")["id"]
        member = self.db_one("SELECT id FROM members WHERE email='flow@example.com'")["id"]

        r = self.post("/issue", {"book_id": book, "member_id": member}, "/issue")
        self.assertIn("issued to Flow Member", r.get_data(as_text=True))
        self.assertEqual(self.db_one("SELECT available_copies a FROM books WHERE id=?", book)["a"], 0)

        # No copies left -> cannot issue to someone else
        other = self.db_one("SELECT id FROM members WHERE email='aarav.sharma@example.com'")["id"]
        r = self.post("/issue", {"book_id": book, "member_id": other}, "/issue")
        self.assertNotIn("issued to Aarav", r.get_data(as_text=True))
        self.assertEqual(self.db_one("SELECT COUNT(*) c FROM issues WHERE book_id=?", book)["c"], 1)

        # Cannot delete a book that is on loan
        r = self.post(f"/books/{book}/delete", {}, "/books")
        self.assertIn("currently issued", r.get_data(as_text=True))

        # Make the loan 5 days overdue, then return -> fine of 5 * FINE_PER_DAY
        issue = self.db_one("SELECT id FROM issues WHERE book_id=? AND status='issued'", book)["id"]
        conn = database.get_db()
        conn.execute("UPDATE issues SET due_date=? WHERE id=?",
                     ((date.today() - timedelta(days=5)).isoformat(), issue))
        conn.commit()
        conn.close()
        r = self.post(f"/return/{issue}", {"next": "/issues"}, "/issues")
        self.assertIn("returned successfully", r.get_data(as_text=True))
        row = self.db_one("SELECT fine, status FROM issues WHERE id=?", issue)
        self.assertEqual(row["fine"], 5 * database.FINE_PER_DAY)
        self.assertEqual(row["status"], "returned")
        self.assertEqual(self.db_one("SELECT available_copies a FROM books WHERE id=?", book)["a"], 1)

    def test_08_inactive_member_cannot_borrow(self):
        self.login()
        self.post("/members/add", {"name": "Sleepy", "email": "sleepy@example.com",
                                   "status": "inactive"}, "/members/add")
        mid = self.db_one("SELECT id FROM members WHERE email='sleepy@example.com'")["id"]
        r = self.post("/issue", {"book_id": 1, "member_id": mid}, "/issue")
        self.assertIn("inactive", r.get_data(as_text=True))

    def test_09_logout(self):
        self.login()
        r = self.post("/logout", {}, "/")
        self.assertIn("logged out", r.get_data(as_text=True))
        self.assertEqual(self.client.get("/books").status_code, 302)

    def test_10_fine_calculation(self):
        today = date.today()
        self.assertEqual(database.calculate_fine(today.isoformat()), 0)
        self.assertEqual(database.calculate_fine((today - timedelta(days=3)).isoformat()),
                         3 * database.FINE_PER_DAY)
        self.assertEqual(database.calculate_fine((today + timedelta(days=3)).isoformat()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
