
# Spec: Date Filter for Profile Page

## Overview
Step 6 lets a logged-in user narrow the profile page to a chosen date range.
Step 5 connected the profile page to the database, but it always shows every
expense the user has ever recorded. This step adds a small filter form (start
date, end date, and quick presets) at the top of the profile page. The summary
stats, transaction history, and category breakdown then show only expenses
whose `date` falls inside the selected range. The filter is carried in the
query string (`GET /profile?start_date=...&end_date=...`), so a filtered view
can be bookmarked or reloaded. With no filter, the page behaves exactly as it
did in Step 5.

## Depends on
- Step 1: Database setup (`expenses.date` stored as ISO `YYYY-MM-DD` text)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page static UI
- Step 5: Backend connection (`database/queries.py` helpers feed `/profile`)

## Routes
No new routes. The existing `GET /profile` route (logged-in) is modified to
read two optional query parameters:
- `start_date` — ISO date `YYYY-MM-DD`, inclusive lower bound
- `end_date` — ISO date `YYYY-MM-DD`, inclusive upper bound

Either, both, or neither may be supplied.

## Database changes
No database changes. `expenses.date` is already stored as `YYYY-MM-DD` text,
which sorts and compares correctly with SQL string comparison
(`date >= ?`, `date <= ?`).

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter form (`method="get"`, `action="{{ url_for('profile') }}"`)
    between the profile header / user card and the summary stats. It contains:
    - `<input type="date" name="start_date">` pre-filled with the active start date
    - `<input type="date" name="end_date">` pre-filled with the active end date
    - An "Apply" submit button
    - A "Clear" link to `url_for('profile')` (no query string), shown only
      when a filter is active
  - Add preset links that fill in the query string: **This month**,
    **Last 30 days**, **This year**, and **All time** (which links to no filter).
    Each is built with `url_for('profile', start_date=..., end_date=...)`.
    The preset matching the active range gets an "active" CSS class.
  - When a filter is active, show a short label above the stats, e.g.
    "Showing 01 Sep 2026 – 30 Sep 2026".
  - Show the filter error message (see rules) when one is present.
  - Change the empty-state text in the transaction table and category
    breakdown to "No expenses in this period" when a filter is active. Keep
    "No expenses yet" when no filter is active.

## Files to change
- `app.py` — `profile()` reads, validates, and passes `start_date` / `end_date`
  to the query helpers, and passes the active filter, the presets, and any error
  to the template
- `database/queries.py` — `get_recent_transactions`, `get_summary_stats`, and
  `get_category_breakdown` take optional `start_date=None, end_date=None`
  keyword arguments and apply them in the `WHERE` clause
- `templates/profile.html` — filter form, presets, active-range label, and
  empty-state text as described above
- `static/css/style.css` — styles for the filter bar, preset pills, and range label

## Files to create
No new files.

## New dependencies
No new dependencies. Use `datetime.date` from the standard library for parsing
and for computing presets.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format dates into SQL. Build the
  `WHERE` clause from fixed fragments (`AND date >= ?`, `AND date <= ?`) and
  append the values to the params tuple.
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹
- Both bounds are **inclusive**.
- Parse dates with `date.fromisoformat()`. If a value is missing, blank, or
  invalid, treat that bound as "not set". Never raise a 500 error.
- If both dates are valid but `start_date > end_date`, ignore both. Render the
  unfiltered page with the error message
  "Start date must be on or before end date."
- The query helpers keep their Step 5 signatures working: calling them with
  only `user_id` must return exactly the same results as before.
- The same date range must be applied to all three sections (stats,
  transactions, and breakdown) so the numbers always agree with each other.
- Category breakdown `pct` values must still sum to 100 for any non-empty range.
- An empty range returns the Step 5 zero/empty values
  (`{"total_spent": 0, "transaction_count": 0, "top_category": "—"}`, `[]`, `[]`).
- Compute presets from `date.today()` in `app.py` (or in a small helper there),
  not in the template:
  - This month: first day of the current month → today
  - Last 30 days: today − 29 days → today
  - This year: 1 January of the current year → today
- The user card (name, email, member since) is **not** filtered.
- The unauthenticated redirect to `/login` must still happen before any filter
  parsing.

## Tests to write

### Unit tests
File: `tests/test_date_filter.py`

| Function | Input | Expected output |
|---|---|---|
| `get_summary_stats` | seed user, no dates | same as Step 5 (total 220.74, count 8, top "Bills") |
| `get_summary_stats` | seed user, day 1 – day 5 of current month | total 107.50, count 3, top "Bills" |
| `get_summary_stats` | seed user, range with no expenses | zeros / "—" |
| `get_recent_transactions` | seed user, only `start_date` = day 10 | 4 rows (days 10, 12, 14, 16), newest first |
| `get_recent_transactions` | seed user, only `end_date` = day 4 | 2 rows (days 4, 2) |
| `get_category_breakdown` | seed user, day 1 – day 5 | 3 categories (Bills, Transport, Food); `pct` sums to 100 |
| `get_category_breakdown` | seed user, range with no expenses | `[]` |
| any helper | `start_date == end_date` == day 8 | only the day-8 expense (Health, 20.00) |

### Route tests
`GET /profile?start_date=...` — unauthenticated:
- Redirects to `/login` (302)

`GET /profile` — authenticated as seed user:
- No params → 200, total ₹220.74, 8 transactions (unchanged from Step 5)
- `start_date=<day 1>&end_date=<day 5>` → 200, shows ₹107.50 and 3 transactions
- Filter inputs are pre-filled with the submitted dates
- `start_date=not-a-date` → 200, unfiltered results, no crash
- `start_date` after `end_date` → 200, unfiltered results, error message shown
- A range with no expenses → 200, "No expenses in this period" shown, ₹0.00 total
- A "Clear" link to `/profile` is shown only when a filter is active

## Definition of done
- [ ] Visiting `/profile` with no query string shows exactly the Step 5 numbers (₹220.74, 8 transactions, top category "Bills")
- [ ] The profile page shows a filter form with start date, end date, Apply, and preset links (This month / Last 30 days / This year / All time)
- [ ] Choosing day 1 to day 5 of the current month and clicking Apply updates the URL to `/profile?start_date=...&end_date=...` and shows ₹107.50 total, 3 transactions, and a 3-category breakdown whose percentages sum to 100 %
- [ ] After applying a filter, the date inputs stay filled with the chosen dates and an "active range" label is visible
- [ ] Clicking "This month" shows all 8 seed expenses (they are all in the current month) and highlights that preset
- [ ] Choosing a range with no expenses shows ₹0.00, 0 transactions, "—" as top category, and "No expenses in this period" in both lists
- [ ] Setting start date after end date shows "Start date must be on or before end date." and the unfiltered data, with no error page
- [ ] Manually editing the URL to `?start_date=abc` shows the unfiltered page, with no error page
- [ ] Clicking "Clear" (or "All time") returns to `/profile` with the full, unfiltered data
- [ ] Logging out and visiting `/profile?start_date=2026-01-01` redirects to `/login`
