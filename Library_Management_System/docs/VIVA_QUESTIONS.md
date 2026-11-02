# Viva Questions and Answers

## A. Project overview

**1. What is your project about?**
A web-based Library Management System that manages books, members, issuing/returning of books,
fines and reports, built with Flask, SQLite, HTML, CSS and JavaScript.

**2. Why did you choose Flask?**
It is lightweight, easy to learn, needs little configuration and lets me understand every part of the
request-response cycle. Django would add features (admin, ORM) this project does not need.

**3. Why SQLite instead of MySQL?**
SQLite needs no server or installation, stores everything in one file and is bundled with Python, so the
project runs on any PC. For many simultaneous users I would migrate to MySQL/PostgreSQL.

**4. Who are the users of the system?**
The librarian/administrator. (Future work: student/member login.)

**5. What are the main modules?**
Authentication, books, members, circulation (issue/return), dashboard and reports.

## B. Database

**6. What is a primary key? Give an example.**
A column that uniquely identifies each row, e.g. `books.id`.

**7. What is a foreign key? Give an example.**
A column that references the primary key of another table, e.g. `issues.book_id -> books.id`.

**8. Explain the relationships in your ER diagram.**
categories 1:N books, books 1:N issues, members 1:N issues. Hence books and members have a many-to-many
relationship resolved by the `issues` table.

**9. What is a junction (associative) table?**
A table that implements an M:N relationship using two foreign keys. `issues` is one, and it also stores
extra data (dates, fine, status).

**10. What normal form is your database in?**
Third Normal Form: atomic values, full dependency on the key, no transitive dependency.

**11. What are constraints? Which did you use?**
Rules enforced by the DB: PRIMARY KEY, UNIQUE (isbn, email, username), NOT NULL, CHECK (status values,
copies >= 0), FOREIGN KEY.

**12. What does `PRAGMA foreign_keys = ON` do?**
SQLite does not enforce foreign keys by default; this enables enforcement for the connection.

**13. Why are there indexes on the `issues` table?**
Queries filter by status, member and book frequently; indexes avoid full table scans.

**14. Write a query to list overdue books.**
```sql
SELECT b.title, m.name, i.due_date
FROM issues i JOIN books b ON b.id=i.book_id JOIN members m ON m.id=i.member_id
WHERE i.status='issued' AND i.due_date < date('now');
```

**15. Difference between DELETE and DROP?**
DELETE removes rows (table stays); DROP removes the entire table structure.

**16. What is a JOIN? Which types did you use?**
Combining rows from tables by a related column. I used INNER JOIN and LEFT JOIN (books with no category).

**17. What is ACID?**
Atomicity, Consistency, Isolation, Durability - transaction guarantees. SQLite is ACID-compliant; in
"issue book" I insert the loan and decrement stock then `commit()` together.

## C. Python / Flask

**18. What is a route?**
A URL pattern mapped to a Python function using `@app.route`.

**19. Difference between GET and POST?**
GET requests data and appears in the URL; POST sends data in the body and is used to change data.

**20. What is Jinja2?**
Flask's template engine: `{{ }}` prints values, `{% %}` runs logic, and `{% extends %}` gives template inheritance.

**21. What is `session`?**
Per-user data stored in a signed cookie; I keep `user_id` there after login.

**22. What does `@login_required` do?**
It is a decorator that redirects to `/login` if no user is in the session.

**23. What is a decorator?**
A function that wraps another function to add behaviour without changing its code.

**24. What is `g` in Flask?**
An object that lives for one request; I store the DB connection there and close it in `teardown_appcontext`.

**25. Why `url_for` instead of hard-coded URLs?**
URLs stay correct if routes change and static paths are handled automatically.

**26. What is `jsonify`?**
Converts Python data to a JSON HTTP response (used in `/api/stats`).

**27. What is a virtual environment?**
An isolated Python installation so project dependencies do not clash with other projects. `run.bat` creates one.

## D. Security

**28. How do you protect against SQL injection?**
Parameterised queries (`?` placeholders) - user input is never concatenated into SQL.

**29. How are passwords stored?**
As salted hashes via `generate_password_hash`; verified with `check_password_hash`. Plain text is never stored.

**30. What is CSRF and how do you prevent it?**
Cross-Site Request Forgery tricks a logged-in user's browser into sending unwanted requests. Every POST
form includes a random token that must match the one in the session.

**31. What is XSS?**
Injecting malicious scripts through input. Jinja2 auto-escapes output so scripts are displayed as text.

**32. Why are delete actions POST rather than links?**
GET links can be triggered by crawlers or prefetching; POST + CSRF token + confirmation is safer.

## E. Business logic

**33. How is the fine calculated?**
`max(0, return_date - due_date in days) * Rs. 2`.

**34. How do you stop issuing a book with no copies?**
The issue route checks `available_copies >= 1` before inserting the loan.

**35. What happens to stock on return?**
`available_copies` is incremented and the issue row becomes `returned` with the return date and fine.

**36. Why can't a member with history be deleted?**
It would orphan loan records and break reports; the member is marked inactive instead.

**37. How does the dashboard update itself?**
JavaScript calls `/api/stats` with `fetch()` every 30 seconds and updates the numbers.

## F. Frontend

**38. What does `main.js` do?**
Mobile menu, dismissible alerts, delete/return confirmation dialogs, live table search and select filtering.

**39. How is the layout responsive?**
CSS grid with `auto-fit`, flexible containers and a `@media (max-width: 800px)` rule for the menu.

**40. What is AJAX/fetch?**
Requesting data from the server without reloading the page. `fetch('/api/stats')` is an example.

## G. Testing and improvement

**41. How did you test the application?**
Automated unit/integration tests with Flask's test client (`test_app.py`) plus a manual checklist.

**42. What improvements would you make?**
Roles, e-mail reminders, barcode scanning, reservations, PDF/Excel export, and a production database.

**43. How would you deploy it?**
Use a production WSGI server (e.g. Gunicorn/Waitress), set `SECRET_KEY` as an environment variable, use HTTPS.

**44. What are the limitations of SQLite?**
Limited concurrent writes and no network access, so it suits small and medium single-server apps.

**45. What would you change to support multiple branches?**
Add a `branches` table and a `branch_id` foreign key on books and issues.
