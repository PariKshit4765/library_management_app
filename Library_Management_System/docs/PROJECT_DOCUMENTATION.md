# Project Documentation - Library Management System

## 1. Introduction
Libraries that track books and borrowers on paper suffer from lost records, slow searches and
manual fine calculation. This project provides a web application that lets a librarian manage
books, members and loans from a browser, with all data stored in a single SQLite database file.

## 2. Objectives
* Maintain a searchable catalogue of books and categories.
* Register and manage library members.
* Issue and return books while keeping stock counts correct.
* Calculate overdue fines automatically.
* Provide statistics and reports for decision making.
* Protect the system with authenticated access.

## 3. Scope
**In scope:** single-library operation, one admin/librarian role, loans with fixed duration, fines.
**Out of scope:** online payment, e-mail/SMS reminders, barcode scanners, multi-branch support,
member self-service portal (possible future work).

## 4. Technology stack
| Layer | Technology | Why |
|---|---|---|
| Backend | Python 3 + Flask | Small, easy to read and explain |
| Database | SQLite | Zero configuration, single file, ships with Python |
| Templates | Jinja2 | Server-side HTML rendering, auto-escaping against XSS |
| Frontend | HTML5, CSS3, vanilla JavaScript | No build step, no external libraries |
| Security | Werkzeug password hashing, session cookies, CSRF tokens | |

## 5. Architecture
The app follows a simple **MVC-style** layout:

* **Model** - `database.py` (schema, connection, fine calculation, sample data)
* **View** - `templates/*.html` with `static/css` and `static/js`
* **Controller** - route functions in `app.py`

```
Browser  --HTTP-->  Flask routes (app.py)  --SQL-->  SQLite (library.db)
   ^                       |
   +------ HTML / JSON ----+
```

## 6. Modules
1. **Authentication** - login/logout, `login_required` decorator, hashed passwords, CSRF protection.
2. **Book management** - CRUD, search, category filter, ISBN uniqueness, stock tracking.
3. **Member management** - CRUD, e-mail validation, active/inactive status.
4. **Circulation** - issue (checks availability, status, limit, duplicates) and return (computes fine).
5. **Dashboard** - aggregate counts via SQL, category chart, auto-refresh through `/api/stats`.
6. **Reports** - overdue list, most borrowed books, most active members, fines collected/pending.

## 7. Business rules
| Rule | Value |
|---|---|
| Loan period | 14 days |
| Fine | Rs. 2 per day after the due date |
| Max books per member | 5 |
| Duplicate loans | A member cannot hold two copies of the same title at once |
| Inactive members | Cannot borrow |
| Deleting | Books/members with loan history cannot be deleted (data integrity) |
| Stock | `available_copies` decreases on issue and increases on return |

## 8. Routes
| URL | Method | Purpose |
|---|---|---|
| `/login`, `/logout` | GET, POST / POST | Authentication |
| `/` | GET | Dashboard |
| `/books`, `/books/add`, `/books/<id>/edit`, `/books/<id>/delete` | GET, POST | Book CRUD |
| `/members`, `/members/add`, `/members/<id>/edit`, `/members/<id>/delete` | GET, POST | Member CRUD |
| `/issue` | GET, POST | Issue a book |
| `/issues?status=issued/overdue/returned/all` | GET | Transaction list |
| `/return/<id>` | POST | Return a book |
| `/reports` | GET | Reports |
| `/api/stats`, `/api/books` | GET | JSON endpoints |

## 9. Security measures
* Passwords stored as salted hashes (`werkzeug.security`).
* All SQL uses **parameterised queries** - prevents SQL injection.
* Jinja2 **auto-escapes** output - prevents XSS.
* **CSRF token** required on every POST request.
* Session cookie flags `HttpOnly` and `SameSite=Lax`; random secret key stored in `secret.key`.
* Open-redirect protection on the login `next` parameter.
* Destructive actions use POST (never GET) and a JavaScript confirmation.

## 10. Testing
`test_app.py` contains 10 automated tests (login, CSRF, every page, book CRUD, member CRUD,
validation, issue/return workflow, fine calculation, stock counts, deletion rules, logout).
Run with `python test_app.py`. A temporary database is used so real data is safe.

### Manual test checklist
- [ ] Log in with wrong password -> error shown
- [ ] Add a book -> appears in list; duplicate ISBN -> rejected
- [ ] Issue a book -> available count drops by one
- [ ] Return an overdue book -> fine shown and stored
- [ ] Try issuing a book with 0 copies -> rejected
- [ ] Reports page lists the overdue sample loans

## 11. Limitations and future enhancements
* Single admin role -> add roles (librarian, student).
* E-mail/SMS reminders for due dates.
* Barcode/QR scanning, book cover images.
* Reservation queue for books that are out.
* Export reports to PDF/Excel.
* Migrate to PostgreSQL/MySQL for large multi-user deployments.

## 12. Conclusion
The system meets the objectives of a small library: it keeps records consistent, automates fines
and gives instant visibility of the library's state, using only a lightweight, easily explained stack.
