# ER Diagram

A picture version is in [`er_diagram.svg`](er_diagram.svg) (open it in any browser).

## Mermaid diagram

```mermaid
erDiagram
    CATEGORIES ||--o{ BOOKS : "has"
    BOOKS      ||--o{ ISSUES : "is borrowed in"
    MEMBERS    ||--o{ ISSUES : "makes"

    CATEGORIES {
        int id PK
        text name "UNIQUE"
    }
    BOOKS {
        int id PK
        text isbn "UNIQUE"
        text title
        text author
        text publisher
        int year
        int category_id FK
        int total_copies
        int available_copies
    }
    MEMBERS {
        int id PK
        text name
        text email "UNIQUE"
        text phone
        text address
        text join_date
        text status "active | inactive"
    }
    ISSUES {
        int id PK
        int book_id FK
        int member_id FK
        text issue_date
        text due_date
        text return_date "NULL until returned"
        int fine
        text status "issued | returned"
    }
    USERS {
        int id PK
        text username "UNIQUE"
        text password_hash
        text full_name
    }
```

## Relationships

| Relationship | Cardinality | Meaning |
|---|---|---|
| categories - books | 1 : N | A category contains many books; a book belongs to at most one category. |
| books - issues | 1 : N | A book can be issued many times over its life. |
| members - issues | 1 : N | A member can borrow many books over time. |
| books - members (via issues) | M : N | `issues` is the junction (associative) table. |

`users` is independent - it stores librarian/admin credentials only.

## Normalisation

* **1NF** - every column holds one atomic value; every table has a primary key.
* **2NF** - all non-key attributes depend on the whole key (all PKs are single columns).
* **3NF** - no transitive dependencies: category names live in `categories`, not repeated in `books`;
  member and book details live in their own tables, not copied into `issues`.
