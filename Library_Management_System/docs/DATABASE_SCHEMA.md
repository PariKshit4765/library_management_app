# Database Schema (SQLite)

Database file: `library.db` (created automatically by `database.py`).
Foreign keys are enabled on every connection with `PRAGMA foreign_keys = ON`.

## users
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| username | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL (salted hash, never plain text) |
| full_name | TEXT | NOT NULL |

## categories
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | NOT NULL, UNIQUE |

## books
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| isbn | TEXT | NOT NULL, UNIQUE |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| publisher | TEXT | |
| year | INTEGER | |
| category_id | INTEGER | FOREIGN KEY -> categories(id) ON DELETE SET NULL |
| total_copies | INTEGER | NOT NULL, CHECK >= 0 |
| available_copies | INTEGER | NOT NULL, CHECK >= 0 |

## members
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | NOT NULL |
| email | TEXT | NOT NULL, UNIQUE |
| phone | TEXT | |
| address | TEXT | |
| join_date | TEXT | NOT NULL (ISO date) |
| status | TEXT | NOT NULL, CHECK IN ('active','inactive') |

## issues
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| book_id | INTEGER | NOT NULL, FOREIGN KEY -> books(id) |
| member_id | INTEGER | NOT NULL, FOREIGN KEY -> members(id) |
| issue_date | TEXT | NOT NULL (ISO date) |
| due_date | TEXT | NOT NULL (issue date + 14 days) |
| return_date | TEXT | NULL until the book is returned |
| fine | INTEGER | NOT NULL DEFAULT 0 |
| status | TEXT | NOT NULL, CHECK IN ('issued','returned') |

Indexes: `idx_issues_status`, `idx_issues_member`, `idx_issues_book` speed up the most common queries.

## Useful queries

```sql
-- Currently overdue loans
SELECT b.title, m.name, i.due_date
FROM issues i JOIN books b ON b.id = i.book_id JOIN members m ON m.id = i.member_id
WHERE i.status = 'issued' AND i.due_date < date('now');

-- Most borrowed books
SELECT b.title, COUNT(*) AS times
FROM issues i JOIN books b ON b.id = i.book_id
GROUP BY b.id ORDER BY times DESC;

-- Total fines collected
SELECT SUM(fine) FROM issues WHERE status = 'returned';
```
