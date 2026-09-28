# Spec: Add Expense

## Overview
Step 7 lets a logged-in user record a new expense. Until now every expense in
Spendly came from `seed_db()`, and `/expenses/add` returns a placeholder
string. This step replaces that placeholder with a real form (amount,
category, date, description). On a valid submit, the expense is saved to the
`expenses` table for the current user. The user is then redirected to
`/profile`, where the new expense appears in the stats, the transaction
history, and the category breakdown. This is the first time users can put
their own data into the app, and it comes before Edit (Step 8) and Delete
(Step 9).

## Depends on
- Step 1: Database setup (`expenses` table, `CATEGORIES` list, `get_db()`)
- Step 3: Login / Logout (`session["user_id"]`, `g.user` loaded before each request)
- Step 5: Backend connection (`/profile` reads expenses via `database/queries.py`)
- Step 6: Date filter (the new expense must respect the profile date filter)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in
- `POST /expenses/add` — validate the form, insert the expense, then redirect
  to `/profile` with a flash message — logged-in

Both methods are served by the existing `add_expense` view function (currently
a placeholder), now declared with `methods=["GET", "POST"]`. Unauthenticated
requests to either method redirect to `/login`.

## Database changes
No database changes. The existing `expenses` table already has every column
needed (`user_id`, `amount`, `category`, `date`, `description`, `created_at`).

Add one helper to `database/db.py`:
- `create_expense(user_id, amount, category, date, description)` — inserts
  one row using a parameterised query, commits, closes the connection in a
  `finally` block, and returns the new row's `id`. It matches the style of
  `create_user()`.

## Templates
- **Create:** `templates/add_expense.html` — extends `base.html` and contains:
  - A page header with the title "Add expense"
  - An error message area, shown only when `error` is set
  - A `<form method="post" action="{{ url_for('add_expense') }}">` with:
    - `amount` — `<input type="number" step="0.01" min="0.01" required>`
    - `category` — `<select required>` built by looping over `categories`
      passed from the view (never a hardcoded list in the template)
    - `date` — `<input type="date" required>`, defaulting to today
    - `description` — `<input type="text" maxlength="200">`, optional
    - A "Save expense" submit button
    - A "Cancel" link to `url_for('profile')`
  - When re-rendered after a validation error, every field keeps the
    submitted value (the category `<select>` re-selects the chosen option)
- **Modify:** `templates/profile.html` — add an "Add expense" button/link to
  `url_for('add_expense')` in the profile header area, visible above the
  filter bar

## Files to change
- `app.py` — replace the `add_expense` placeholder with the real GET/POST
  logic and remove its "coming in Step 7" comment. Import `CATEGORIES` and
  `create_expense` from `database.db`.
- `database/db.py` — add `create_expense()`
- `templates/profile.html` — "Add expense" link in the header
- `static/css/style.css` — styles for the add-expense form card, form fields,
  error message, and the header "Add expense" button

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies. Use `datetime.date` for date parsing and the default value.

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
  before reading any form data
- `user_id` always comes from `g.user["id"]`, never from the form
- Validation (all server-side, in this order). On failure, re-render
  `add_expense.html` with status 200, the error message, and the submitted
  values. Nothing is inserted.
  - `amount` — required, must parse as a number, and must be `> 0`.
    Error: "Amount must be a positive number."
  - `category` — must be one of `CATEGORIES`. Error: "Please choose a valid category."
  - `date` — required, must parse with `date.fromisoformat()`.
    Error: "Please enter a valid date."
  - `description` — optional. Strip whitespace. Store `NULL` when empty.
    Anything longer than 200 characters is rejected with
    "Description must be 200 characters or fewer."
- Round `amount` to 2 decimal places before inserting
- Store `date` as ISO `YYYY-MM-DD` text (the same format as the seed data, so
  the Step 6 date filter keeps working)
- On success, `flash("Expense added.")` and `redirect(url_for("profile"))` (302).
  Do not render the profile directly.
- The GET form defaults the date to `date.today().isoformat()`
- A validation error must never cause a 500 error

## Definition of done
- [ ] Logged out, visiting `/expenses/add` redirects to `/login`
- [ ] Logged out, POSTing to `/expenses/add` redirects to `/login` and inserts nothing
- [ ] Logged in, `/profile` shows an "Add expense" link that opens `/expenses/add`
- [ ] `/expenses/add` shows a form with amount, category (all 7 categories), date (pre-filled with today), and description, plus Save and Cancel
- [ ] Submitting amount `250`, category `Food`, today's date, and description `Lunch` redirects to `/profile`, shows the "Expense added." message, and lists the new expense (₹250.00, Food, Lunch) at the top of the transaction history
- [ ] After adding that expense, the profile total rises by ₹250.00 and the transaction count rises by 1
- [ ] Submitting an empty, zero, negative, or non-numeric amount re-shows the form with "Amount must be a positive number." and adds no row
- [ ] Submitting a category that is not in the list (e.g. by editing the HTML) shows "Please choose a valid category." and adds no row
- [ ] Submitting an invalid date shows "Please enter a valid date." and adds no row
- [ ] After a validation error, the form keeps the values that were entered
- [ ] Submitting with an empty description succeeds, and the description is stored as `NULL`
- [ ] An expense added with a date last year does not appear under the "This month" preset, but does appear under "All time"
- [ ] An expense added by one user never appears on another user's profile
- [ ] Clicking "Cancel" returns to `/profile` without adding anything
- [ ] No hex colour values appear in `add_expense.html` or the new CSS rules
