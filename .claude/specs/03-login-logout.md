# Spec: Login and Logout

## Overview
Implement session-based authentication so registered users can sign in and out of Spendly. This step upgrades the existing stub `GET /login` route into a fully functional form that accepts a POST, verifies credentials against the `users` table, and starts a Flask session. It also replaces the `/logout` placeholder with real session-clearing logic. This is the step that turns Spendly from a collection of static pages into an app with a real notion of "the current user," which every subsequent authenticated feature (profile, expenses) depends on.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user()`, users can already be created with hashed passwords)

## Routes
- `GET /login` — render login form — public (already exists as stub, upgrade it)
- `POST /login` — verify credentials, start session, redirect to a logged-in landing point — public
- `GET /logout` — clear session, redirect to login — logged-in (replaces placeholder)

## Database changes
No new tables or columns. The existing `users` table (id, name, email, password_hash, created_at) covers all requirements.

A new DB helper must be added to `database/db.py`:
- `get_user_by_email(email)` — runs a parameterised `SELECT * FROM users WHERE email = ?`, returns the row (or `None` if not found). Used to look up the user and verify their password hash.

## Templates
- **Modify:** `templates/login.html`
  - Change the form `action` to `{{ url_for('login') }}` (currently hardcoded to `/login`)
  - Confirm `method="POST"` is present (it already is) and add `name` attributes (already present: `email`, `password`)
  - Keep the existing flash-message block (`get_flashed_messages()`), which already renders `.auth-error` — no new block needed
  - Keep all existing visual design

## Files to change
- `app.py` — upgrade `login()` to handle `GET` and `POST`; add session logic; replace `logout()` placeholder with real logic
- `database/db.py` — add `get_user_by_email()` helper
- `templates/login.html` — fix hardcoded form action to use `url_for('login')`

## Files to create
None.

## New dependencies
No new dependencies. Uses `werkzeug.security.check_password_hash` (already available via `werkzeug`, already a dependency) and Flask's built-in `session`, `flash`, `redirect`, `url_for`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Passwords hashed with werkzeug — verify with `werkzeug.security.check_password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use Flask's `session` object to track `session["user_id"]` on successful login; do not invent a custom cookie/token mechanism
- On failed login (unknown email or wrong password), show one generic error (e.g. "Invalid email or password") — do not reveal whether the email exists, to avoid user enumeration
- On any validation failure, re-render the form with a flashed error message — do not redirect
- On success, `flash` a welcome/success message and `redirect` to `url_for('landing')` (no dashboard/profile route is implemented yet, so redirect to the existing landing page)
- `/logout` must call `session.clear()` (or pop `user_id`), flash a message, and redirect to `url_for('login')`
- Use `abort(405)` if an unsupported HTTP method reaches `/login`
- Use `url_for()` for every internal link — never hardcode URLs (this also fixes the existing hardcoded `/login` action in `login.html`)

## Definition of done
- [ ] `GET /login` renders the login form without errors
- [ ] Submitting valid credentials for a registered user (e.g. the seeded `demo@spendly.com` / `demo123`) logs in and redirects to the landing page
- [ ] Submitting an unknown email shows a generic "Invalid email or password" error, no session set
- [ ] Submitting a known email with the wrong password shows the same generic error, no session set
- [ ] Submitting with an empty email or password re-renders the form with a validation error
- [ ] After logging in, visiting `/logout` clears the session and redirects to `/login`
- [ ] After logging out, no session data persists (verifiable by checking that a subsequent request has no `user_id` in session)
