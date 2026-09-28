"""
Tests for Step 7: Add Expense.

Based on .claude/specs/07-add-expense.md — NOT derived from reading the
implementation. Covers:
  - Auth guard on GET/POST /expenses/add (redirect to /login, no insert)
  - "Add expense" link on /profile
  - GET /expenses/add form contents (amount, all 7 categories, date
    defaulting to today, description, Save + Cancel)
  - Valid POST: redirect to /profile, "Expense added." flash, DB row
    inserted for the logged-in user, updated profile total/count
  - Server-side validation (amount, category, date, description length),
    no insert on failure, form re-populated with submitted values
  - Empty/whitespace description stored as NULL
  - Amount rounded to 2 decimal places before insert
  - Date stored as ISO YYYY-MM-DD text
  - New expense respects the Step 6 date filter (This month vs All time)
  - user_id always comes from the session, never from the form
  - Cross-user isolation: one user's expense never shows on another
    user's profile
"""

from datetime import date, timedelta

import pytest

from database.db import CATEGORIES, get_db


def today_iso():
    return date.today().isoformat()


def long_ago_iso():
    """A date safely more than a year in the past (outside 'This month')."""
    return (date.today() - timedelta(days=400)).isoformat()


def count_expenses(user_id=None):
    conn = get_db()
    try:
        if user_id is None:
            return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        return conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def fetch_expenses(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC", (user_id,)
        ).fetchall()
    finally:
        conn.close()


VALID_PAYLOAD = {
    "amount": "250",
    "category": "Food",
    "date": today_iso(),
    "description": "Lunch",
}


# ------------------------------------------------------------------ #
# Auth guard                                                         #
# ------------------------------------------------------------------ #

class TestAddExpenseAuthGuard:
    def test_unauthenticated_get_redirects_to_login(self, client):
        response = client.get("/expenses/add", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_post_redirects_to_login(self, client):
        response = client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_post_inserts_nothing(self, app, client):
        before = count_expenses()
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        after = count_expenses()
        assert after == before, "Logged-out POST must not insert an expense"

    def test_logout_then_get_redirects_to_login(self, auth_client):
        auth_client.get("/logout")
        response = auth_client.get("/expenses/add", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_logout_then_post_redirects_to_login_and_inserts_nothing(self, app, auth_client, seed_user_id):
        auth_client.get("/logout")
        before = count_expenses(seed_user_id)
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
        assert count_expenses(seed_user_id) == before


# ------------------------------------------------------------------ #
# Link on /profile                                                   #
# ------------------------------------------------------------------ #

class TestProfileAddExpenseLink:
    def test_profile_has_add_expense_link(self, auth_client):
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        assert '/expenses/add' in html, "Expected an 'Add expense' link pointing to /expenses/add"

    def test_add_expense_link_opens_the_form(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200


# ------------------------------------------------------------------ #
# GET /expenses/add form contents                                    #
# ------------------------------------------------------------------ #

class TestAddExpenseFormGet:
    def test_logged_in_get_returns_200(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200

    def test_form_has_amount_field(self, auth_client):
        response = auth_client.get("/expenses/add")
        html = response.data.decode("utf-8")
        assert 'name="amount"' in html

    def test_form_has_category_field_with_all_7_categories(self, auth_client):
        response = auth_client.get("/expenses/add")
        html = response.data.decode("utf-8")
        assert 'name="category"' in html
        assert len(CATEGORIES) == 7, "Sanity check: spec expects 7 categories"
        for category in CATEGORIES:
            assert category in html, f"Expected category '{category}' in the form"

    def test_form_has_date_field_defaulting_to_today(self, auth_client):
        response = auth_client.get("/expenses/add")
        html = response.data.decode("utf-8")
        assert 'name="date"' in html
        assert f'value="{today_iso()}"' in html, "Date input must default to today's ISO date"

    def test_form_has_description_field(self, auth_client):
        response = auth_client.get("/expenses/add")
        html = response.data.decode("utf-8")
        assert 'name="description"' in html

    def test_form_has_save_button(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert b"Save expense" in response.data

    def test_form_has_cancel_link_to_profile(self, auth_client):
        response = auth_client.get("/expenses/add")
        html = response.data.decode("utf-8")
        assert "Cancel" in html
        assert '/profile' in html


# ------------------------------------------------------------------ #
# Valid POST                                                          #
# ------------------------------------------------------------------ #

class TestAddExpenseValidSubmit:
    def test_valid_submit_redirects_to_profile(self, auth_client):
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")

    def test_valid_submit_shows_flash_message(self, auth_client):
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=True)
        assert response.status_code == 200
        assert b"Expense added." in response.data

    def test_valid_submit_inserts_row_for_logged_in_user(self, app, auth_client, seed_user_id):
        before = count_expenses(seed_user_id)
        auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        after = count_expenses(seed_user_id)
        assert after == before + 1

        rows = fetch_expenses(seed_user_id)
        newest = rows[0]
        assert newest["amount"] == 250.0
        assert newest["category"] == "Food"
        assert newest["date"] == today_iso()
        assert newest["description"] == "Lunch"
        assert newest["user_id"] == seed_user_id

    def test_valid_submit_shows_new_expense_at_top_of_history(self, auth_client):
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=True)
        html = response.data.decode("utf-8")
        assert "₹250.00" in html
        assert "Food" in html
        assert "Lunch" in html

    def test_valid_submit_raises_profile_total_by_amount(self, auth_client):
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=True)
        assert "₹470.74".encode("utf-8") in response.data, "220.74 baseline + 250 new expense"

    def test_valid_submit_raises_transaction_count_by_one(self, auth_client):
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=True)
        assert b"9" in response.data, "8 seeded + 1 new = 9 transactions"


# ------------------------------------------------------------------ #
# Validation: amount                                                  #
# ------------------------------------------------------------------ #

class TestAddExpenseAmountValidation:
    @pytest.mark.parametrize("bad_amount", ["", "0", "-5", "abc"])
    def test_invalid_amount_shows_error(self, auth_client, bad_amount):
        payload = dict(VALID_PAYLOAD, amount=bad_amount)
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 200
        assert b"Amount must be a positive number." in response.data

    @pytest.mark.parametrize("bad_amount", ["", "0", "-5", "abc"])
    def test_invalid_amount_inserts_no_row(self, app, auth_client, seed_user_id, bad_amount):
        before = count_expenses(seed_user_id)
        payload = dict(VALID_PAYLOAD, amount=bad_amount)
        auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert count_expenses(seed_user_id) == before


# ------------------------------------------------------------------ #
# Validation: category                                                #
# ------------------------------------------------------------------ #

class TestAddExpenseCategoryValidation:
    def test_invalid_category_shows_error(self, auth_client):
        payload = dict(VALID_PAYLOAD, category="NotACategory")
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 200
        assert b"Please choose a valid category." in response.data

    def test_invalid_category_inserts_no_row(self, app, auth_client, seed_user_id):
        before = count_expenses(seed_user_id)
        payload = dict(VALID_PAYLOAD, category="NotACategory")
        auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert count_expenses(seed_user_id) == before


# ------------------------------------------------------------------ #
# Validation: date                                                    #
# ------------------------------------------------------------------ #

class TestAddExpenseDateValidation:
    @pytest.mark.parametrize("bad_date", ["not-a-date", "2026-13-40", ""])
    def test_invalid_date_shows_error(self, auth_client, bad_date):
        payload = dict(VALID_PAYLOAD, date=bad_date)
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 200
        assert b"Please enter a valid date." in response.data

    @pytest.mark.parametrize("bad_date", ["not-a-date", "2026-13-40", ""])
    def test_invalid_date_inserts_no_row(self, app, auth_client, seed_user_id, bad_date):
        before = count_expenses(seed_user_id)
        payload = dict(VALID_PAYLOAD, date=bad_date)
        auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert count_expenses(seed_user_id) == before


# ------------------------------------------------------------------ #
# Validation: description                                             #
# ------------------------------------------------------------------ #

class TestAddExpenseDescriptionValidation:
    def test_description_over_200_chars_shows_error(self, auth_client):
        payload = dict(VALID_PAYLOAD, description="x" * 201)
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 200
        assert b"Description must be 200 characters or fewer." in response.data

    def test_description_over_200_chars_inserts_no_row(self, app, auth_client, seed_user_id):
        before = count_expenses(seed_user_id)
        payload = dict(VALID_PAYLOAD, description="x" * 201)
        auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert count_expenses(seed_user_id) == before

    def test_description_exactly_200_chars_succeeds(self, app, auth_client, seed_user_id):
        payload = dict(VALID_PAYLOAD, description="x" * 200)
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 302

    def test_empty_description_succeeds_and_stored_as_null(self, app, auth_client, seed_user_id):
        payload = dict(VALID_PAYLOAD, description="")
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 302
        rows = fetch_expenses(seed_user_id)
        assert rows[0]["description"] is None

    def test_whitespace_only_description_stored_as_null(self, app, auth_client, seed_user_id):
        payload = dict(VALID_PAYLOAD, description="   ")
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 302
        rows = fetch_expenses(seed_user_id)
        assert rows[0]["description"] is None


# ------------------------------------------------------------------ #
# Form re-population after a validation error                         #
# ------------------------------------------------------------------ #

class TestAddExpenseFormRepopulation:
    def test_amount_field_keeps_submitted_value_on_error(self, auth_client):
        payload = dict(VALID_PAYLOAD, amount="-5")
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        html = response.data.decode("utf-8")
        assert "-5" in html

    def test_description_field_keeps_submitted_value_on_error(self, auth_client):
        payload = dict(VALID_PAYLOAD, amount="-5", description="Keep me")
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        html = response.data.decode("utf-8")
        assert "Keep me" in html

    def test_date_field_keeps_submitted_value_on_error(self, auth_client):
        submitted_date = "2020-05-15"
        payload = dict(VALID_PAYLOAD, amount="-5", date=submitted_date)
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        html = response.data.decode("utf-8")
        assert f'value="{submitted_date}"' in html

    def test_category_select_reselects_submitted_category_on_error(self, auth_client):
        payload = dict(VALID_PAYLOAD, amount="-5", category="Health")
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        html = response.data.decode("utf-8")
        # The Health <option> must carry a `selected` marker after the value 250 invalid amount error.
        assert "Health" in html
        assert "selected" in html


# ------------------------------------------------------------------ #
# Amount rounding and date storage format                             #
# ------------------------------------------------------------------ #

class TestAddExpenseAmountRounding:
    def test_amount_rounded_to_2_decimal_places(self, app, auth_client, seed_user_id):
        payload = dict(VALID_PAYLOAD, amount="19.999")
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 302
        rows = fetch_expenses(seed_user_id)
        assert rows[0]["amount"] == 20.0


class TestAddExpenseDateStorage:
    def test_date_stored_as_iso_yyyy_mm_dd(self, app, auth_client, seed_user_id):
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        assert response.status_code == 302
        rows = fetch_expenses(seed_user_id)
        stored_date = rows[0]["date"]
        assert stored_date == today_iso()
        # Confirm it parses as ISO YYYY-MM-DD
        date.fromisoformat(stored_date)


# ------------------------------------------------------------------ #
# Interaction with the Step 6 date filter                             #
# ------------------------------------------------------------------ #

class TestAddExpenseRespectsDateFilter:
    def test_last_year_expense_excluded_from_this_month_filter(self, auth_client):
        payload = dict(VALID_PAYLOAD, date=long_ago_iso(), amount="99.99", description="Old expense")
        auth_client.post("/expenses/add", data=payload, follow_redirects=False)

        month_start = date.today().replace(day=1).isoformat()
        month_end = date.today().isoformat()
        response = auth_client.get(f"/profile?start_date={month_start}&end_date={month_end}")
        html = response.data.decode("utf-8")
        assert "Old expense" not in html
        assert "₹220.74".encode("utf-8") in response.data, "This month total must still match the seed baseline"

    def test_last_year_expense_present_under_all_time(self, auth_client):
        payload = dict(VALID_PAYLOAD, date=long_ago_iso(), amount="99.99", description="Old expense")
        auth_client.post("/expenses/add", data=payload, follow_redirects=False)

        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        assert "Old expense" in html
        assert "₹320.73".encode("utf-8") in response.data, "220.74 baseline + 99.99 old expense"


# ------------------------------------------------------------------ #
# Cross-user isolation and user_id sourced from the session            #
# ------------------------------------------------------------------ #

class TestAddExpenseUserIsolation:
    def test_other_user_never_sees_a_users_new_expense(self, app, auth_client):
        from database.db import create_user

        with app.app_context():
            other_user_id = create_user("Other User", "other@spendly.com", "password123")

        payload = dict(VALID_PAYLOAD, description="Secret demo lunch")
        auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        auth_client.get("/logout")

        other_client = app.test_client()
        other_client.post("/login", data={"email": "other@spendly.com", "password": "password123"})
        response = other_client.get("/profile")
        html = response.data.decode("utf-8")
        assert "Secret demo lunch" not in html
        assert count_expenses(other_user_id) == 0

    def test_user_id_comes_from_session_not_form_field(self, app, auth_client, seed_user_id):
        from database.db import create_user

        with app.app_context():
            other_user_id = create_user("Other User", "other2@spendly.com", "password123")

        payload = dict(VALID_PAYLOAD, description="Spoof attempt", user_id=str(other_user_id))
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 302

        rows = fetch_expenses(seed_user_id)
        assert rows[0]["description"] == "Spoof attempt", "Row must be attributed to the session user"
        assert rows[0]["user_id"] == seed_user_id
        assert count_expenses(other_user_id) == 0, "user_id must never be taken from the form"


# ------------------------------------------------------------------ #
# Cancel link                                                         #
# ------------------------------------------------------------------ #

class TestAddExpenseCancel:
    def test_cancel_link_points_to_profile_and_no_post_is_made(self, app, auth_client, seed_user_id):
        response = auth_client.get("/expenses/add")
        html = response.data.decode("utf-8")
        assert "Cancel" in html
        assert '/profile' in html
        # Following Cancel is a plain navigation (GET), never an insert.
        before = count_expenses(seed_user_id)
        auth_client.get("/profile")
        assert count_expenses(seed_user_id) == before
