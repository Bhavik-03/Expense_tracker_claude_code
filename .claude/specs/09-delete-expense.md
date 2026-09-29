# Spec: Delete Expense

## Overview
Step 9 lets a logged-in user permanently remove an expense they recorded by
mistake. Steps 7 and 8 made it possible to add and edit expenses, but
`/expenses/<id>/delete` still returns a placeholder string. This step replaces
that placeholder with a two-stage flow: a `GET` shows a confirmation page
summarising the expense (amount, category, date, description), and a `POST`
from that page deletes the row from the `expenses` table and redirects to
`/profile`, where the stats, transaction history, and category breakdown no
longer include it. Deletion never happens on a `GET`, so a link preview,
prefetch, or accidental click cannot destroy data. Users can only ever view or
delete their own expenses. Each row in the profile's transaction history gets
a "Delete" link next to the existing "Edit" link so the feature is reachable
from the UI. This completes the add / edit / delete cycle for expenses.

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`)
- Step 3: Login / Logout (`session["user_id"]`, `g.user` loaded before each request)
- Step 5: Backend connection (`/profile` reads expenses via `database/queries.py`)
- Step 7: Add expense (form card styles reused for the confirmation page)
- Step 8: Edit expense (`get_expense_by_id()`, `t.id` in transactions, the
  "Actions" column in the profile table)

## Routes
- `GET /expenses/<int:id>/delete` — render a confirmation page showing the
  expense's details — logged-in (owner only)
- `POST /expenses/<int:id>/delete` — delete the expense, then redirect to
  `/profile` with a flash message — logged-in (owner only)

Both methods are served by the existing `delete_expense` view function
(currently a placeholder), now declared with `methods=["GET", "POST"]`.
- Unauthenticated requests to either method redirect to `/login`.
- If the expense does not exist, **or** belongs to another user, respond with
  `404` (use `abort(404)`). Do not reveal whether the id exists.

## Database changes
No database changes. No schema changes are needed and no other table
references `expenses`, so no cascading is required.

Add one helper to `database/db.py`, in the same style as `update_expense()`
(parameterised query, connection closed in a `finally` block):
- `delete_expense(expense_id, user_id)` — runs
  `DELETE FROM expenses WHERE id = ? AND user_id = ?`, commits, and returns
  the number of rows deleted (`cursor.rowcount`).

Reuse the existing `get_expense_by_id(expense_id, user_id)` for the ownership
check and for the confirmation page's details.

## Templates
- **Create:** `templates/delete_expense.html` — extends `base.html` and uses
  the same form card layout as `edit_expense.html`:
  - A page header with the title "Delete expense"
  - A short warning that the action cannot be undone
  - A summary of the expense: amount formatted as `₹` with 2 decimal places,
    category, date, and description (show "—" when description is `NULL`)
  - A `<form method="post" action="{{ url_for('delete_expense', id=expense.id) }}">`
    containing only a "Delete expense" submit button, styled as a
    danger button using `var(--danger)` / `var(--danger-light)`
  - A "Cancel" link to `url_for('profile')`
- **Modify:** `templates/profile.html` — in the "Actions" cell of each
  transaction row, add a "Delete" link to `url_for('delete_expense', id=t.id)`
  alongside the existing "Edit" link. The column count stays at 5 (the
  empty-state `colspan` is unchanged).

## Files to change
- `app.py` — replace the `delete_expense` placeholder with the real GET/POST
  logic and remove its "coming in Step 9" comment. Import the new
  `delete_expense` helper from `database.db` under an alias (e.g.
  `delete_expense as db_delete_expense`) so it does not clash with the view
  function name.
- `database/db.py` — add `delete_expense()`
- `templates/profile.html` — add a "Delete" link per row in the Actions cell
- `static/css/style.css` — styles for the per-row Delete link, the
  confirmation summary, and the danger submit button (reuse existing form
  card styles; add new rules only where needed)

## Files to create
- `templates/delete_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- All internal links and form actions use `url_for(...)`
- Currency must always display as ₹
- Authentication guard first: if `g.user` is `None`,
  `redirect(url_for("login"))` before touching the database
- Ownership check second: load the expense with
  `get_expense_by_id(id, g.user["id"])`; if it returns `None`, `abort(404)`.
  This applies to both GET and POST.
- `user_id` always comes from `g.user["id"]`, never from the form or URL
- The `DELETE` must include `AND user_id = ?` even though ownership was
  already checked
- `GET` must never delete anything — only `POST` deletes
- No JavaScript `confirm()` dialogs — confirmation is the server-rendered page
- On success, `flash("Expense deleted.")` and `redirect(url_for("profile"))` (302)
- An unknown id or another user's id must never cause a 500 error
- Deleting an expense must not affect any other expense or user

## Definition of done
- [ ] Logged out, visiting `/expenses/1/delete` redirects to `/login`
- [ ] Logged out, POSTing to `/expenses/1/delete` redirects to `/login` and deletes nothing
- [ ] Logged in, every row in the profile's transaction history has a "Delete" link to `/expenses/<id>/delete` next to its "Edit" link
- [ ] Opening the Delete link shows a confirmation page with that expense's amount (₹, 2 decimals), category, date, and description
- [ ] Visiting the confirmation page (GET) does not remove the expense
- [ ] Clicking "Delete expense" redirects to `/profile`, shows "Expense deleted.", and the row is gone
- [ ] After deleting, the profile total, transaction count, and category breakdown all drop by that expense
- [ ] Clicking "Cancel" returns to `/profile` and the expense is still there
- [ ] Visiting or POSTing to `/expenses/99999/delete` (non-existent id) returns 404
- [ ] Visiting or POSTing to another user's expense delete URL returns 404 and that expense still exists
- [ ] POSTing to the same delete URL a second time returns 404
- [ ] Adding and editing expenses still work exactly as in Steps 7 and 8
- [ ] No hex colour values appear in `delete_expense.html` or the new CSS rules
