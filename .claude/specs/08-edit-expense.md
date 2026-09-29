# Spec: Edit Expense

## Overview
Step 8 lets a logged-in user correct an expense they have already recorded.
Step 7 made it possible to add expenses, but a typo in the amount, category,
date, or description cannot be fixed yet, and `/expenses/<id>/edit` still
returns a placeholder string. This step replaces that placeholder with a real
edit form, pre-filled with the expense's current values. On a valid submit,
the row in the `expenses` table is updated and the user is redirected to
`/profile`, where the stats, the transaction history, and the category
breakdown reflect the change. Users can only ever view or edit their own
expenses. Each row in the profile's transaction history gets an "Edit" link
so the feature is reachable from the UI. Delete stays a placeholder until
Step 9.

## Depends on
- Step 1: Database setup (`expenses` table, `CATEGORIES` list, `get_db()`)
- Step 3: Login / Logout (`session["user_id"]`, `g.user` loaded before each request)
- Step 5: Backend connection (`/profile` reads expenses via `database/queries.py`)
- Step 6: Date filter (an edited date must move the expense in/out of filtered ranges)
- Step 7: Add expense (form fields, validation rules, and styles are reused)

## Routes
- `GET /expenses/<int:id>/edit` — render the edit form pre-filled with the
  expense's current values — logged-in (owner only)
- `POST /expenses/<int:id>/edit` — validate the form, update the expense, then
  redirect to `/profile` with a flash message — logged-in (owner only)

Both methods are served by the existing `edit_expense` view function (currently
a placeholder), now declared with `methods=["GET", "POST"]`.
- Unauthenticated requests to either method redirect to `/login`.
- If the expense does not exist, **or** belongs to another user, respond with
  `404` (use `abort(404)`). Do not reveal whether the id exists.

## Database changes
No database changes. The existing `expenses` table already has every column
needed.

Add two helpers to `database/db.py`, in the same style as `create_expense()`
(parameterised query, connection closed in a `finally` block):
- `get_expense_by_id(expense_id, user_id)` — returns the row matching **both**
  `id = ?` and `user_id = ?`, or `None`. Scoping by `user_id` in the SQL is the
  ownership check.
- `update_expense(expense_id, user_id, amount, category, date, description)` —
  runs `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ?
  WHERE id = ? AND user_id = ?`, commits, and returns the number of rows
  updated (`cursor.rowcount`).

Modify `database/queries.py`:
- `get_recent_transactions()` — also select `id` so the profile template can
  build the Edit link for each row.

## Templates
- **Create:** `templates/edit_expense.html` — extends `base.html` and mirrors
  `add_expense.html`:
  - A page header with the title "Edit expense"
  - An error message area, shown only when `error` is set
  - A `<form method="post" action="{{ url_for('edit_expense', id=expense_id) }}">` with:
    - `amount` — `<input type="number" step="0.01" min="0.01" required>`
    - `category` — `<select required>` built by looping over `categories`
      passed from the view, with the current category selected
    - `date` — `<input type="date" required>`
    - `description` — `<input type="text" maxlength="200">`, optional
    - A "Save changes" submit button
    - A "Cancel" link to `url_for('profile')`
  - On GET, every field is pre-filled from the stored expense (amount shown
    with 2 decimal places, a `NULL` description shown as an empty field)
  - When re-rendered after a validation error, every field keeps the
    submitted value, not the stored one
- **Modify:** `templates/profile.html` — in the transaction history table, add
  an "Actions" column header and, per row, an "Edit" link to
  `url_for('edit_expense', id=t.id)`. Update the empty-state row's `colspan`
  from 4 to 5.

## Files to change
- `app.py` — replace the `edit_expense` placeholder with the real GET/POST
  logic and remove its "coming in Step 8" comment. Import `get_expense_by_id`
  and `update_expense` from `database.db`. Move the Step 7 validation into a
  shared helper (e.g. `_validate_expense_form(form)` returning
  `(error, cleaned_values)`) used by both `add_expense` and `edit_expense`, so
  the rules and error messages stay identical. `add_expense` behaviour must not
  change.
- `database/db.py` — add `get_expense_by_id()` and `update_expense()`
- `database/queries.py` — include `id` in `get_recent_transactions()`
- `templates/profile.html` — "Actions" column with an Edit link per row
- `static/css/style.css` — styles for the per-row Edit link (reuse the
  add-expense form card styles for the edit page; add new rules only where needed)

## Files to create
- `templates/edit_expense.html`

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
- Authentication guard first: if `g.user` is `None`, `redirect(url_for("login"))`
  before touching the database or form data
- Ownership check second: load the expense with
  `get_expense_by_id(id, g.user["id"])`; if it returns `None`, `abort(404)`.
  This applies to both GET and POST.
- `user_id` always comes from `g.user["id"]`, never from the form or URL
- The `UPDATE` must include `AND user_id = ?` even though ownership was
  already checked
- Validation is exactly the same as Step 7 (same order, same messages). On
  failure, re-render `edit_expense.html` with status 200, the error message,
  and the submitted values. Nothing is updated.
  - `amount` — required, must parse as a finite number, `> 0`.
    Error: "Amount must be a positive number."
  - `category` — must be one of `CATEGORIES`. Error: "Please choose a valid category."
  - `date` — required, must parse with `date.fromisoformat()`.
    Error: "Please enter a valid date."
  - `description` — optional. Strip whitespace. Store `NULL` when empty.
    Longer than 200 characters → "Description must be 200 characters or fewer."
- Round `amount` to 2 decimal places before updating
- Store `date` as ISO `YYYY-MM-DD` text
- On success, `flash("Expense updated.")` and `redirect(url_for("profile"))` (302)
- `created_at` must not change on update
- A validation error or unknown id must never cause a 500 error
- Do not implement delete — `/expenses/<id>/delete` stays a Step 9 placeholder

## Definition of done
- [ ] Logged out, visiting `/expenses/1/edit` redirects to `/login`
- [ ] Logged out, POSTing to `/expenses/1/edit` redirects to `/login` and changes nothing
- [ ] Logged in, every row in the profile's transaction history has an "Edit" link to `/expenses/<id>/edit`
- [ ] Opening the Edit link shows the form pre-filled with that expense's amount, category, date, and description
- [ ] Changing the amount to `99.50` and saving redirects to `/profile`, shows "Expense updated.", and the row now shows ₹99.50
- [ ] After editing, the profile total and category breakdown reflect the new amount/category; the transaction count is unchanged
- [ ] Changing an expense's category from Food to Transport moves its amount between those categories in the breakdown
- [ ] Changing an expense's date to last year removes it from the "This month" preset but it still appears under "All time"
- [ ] Visiting `/expenses/99999/edit` (non-existent id) returns 404
- [ ] Visiting or POSTing to another user's expense edit URL returns 404 and leaves that expense unchanged
- [ ] Submitting an empty, zero, negative, or non-numeric amount re-shows the form with "Amount must be a positive number." and the stored expense is unchanged
- [ ] Submitting an invalid category shows "Please choose a valid category." and changes nothing
- [ ] Submitting an invalid date shows "Please enter a valid date." and changes nothing
- [ ] After a validation error, the form keeps the values that were entered
- [ ] Clearing the description and saving stores it as `NULL`
- [ ] Clicking "Cancel" returns to `/profile` without changing anything
- [ ] Adding an expense via `/expenses/add` still works exactly as in Step 7
- [ ] `/expenses/<id>/delete` still returns the Step 9 placeholder
- [ ] No hex colour values appear in `edit_expense.html` or the new CSS rules
