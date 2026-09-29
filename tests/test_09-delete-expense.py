"""
Tests for Step 9: Delete Expense.

Based on .claude/specs/09-delete-expense.md, not on the implementation. Covers:
  - Auth guard on GET/POST /expenses/<id>/delete (redirect to /login, no delete)
  - "Delete" link per row on /profile
  - GET confirmation page (amount, category, date, description, em dash for
    NULL description, Cancel link) and that GET never deletes
  - POST deletes, redirects 302 to /profile, flashes "Expense deleted."
  - Profile total / transaction count update after delete
  - Repeat POST and non-existent id return 404 (GET and POST)
  - Another user's expense returns 404 (GET and POST) and is not deleted
  - Deleting one expense leaves all other expenses untouched
"""

from datetime import date

import pytest

from database.db import create_expense, create_user, get_db

SEED_EXPENSE_ID = 1
SEED_EXPENSE_AMOUNT = "12.50"
SEED_EXPENSE_CATEGORY = "Food"
SEED_EXPENSE_DESCRIPTION = "Groceries"
SEED_TOTAL_BEFORE = "220.74"
SEED_TOTAL_AFTER = "208.24"  # 220.74 - 12.50
MISSING_ID = 99999


def delete_url(expense_id):
    return f"/expenses/{expense_id}/delete"


def fetch_expense(expense_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()


def all_expense_rows():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM expenses ORDER BY id").fetchall()
        return [tuple(r) for r in rows]
    finally:
        conn.close()


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


@pytest.fixture
def other_user_expense_id(app):
    """An expense owned by a second user (not the seeded demo user)."""
    other_id = create_user("Other Person", "other@example.com", "otherpass123")
    return create_expense(
        other_id, 77.00, "Shopping", date.today().isoformat(), "Other's secret"
    )


# ------------------------------------------------------------------ #
# Auth guard                                                         #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_get_logged_out_redirects_to_login(self, client):
        response = client.get(delete_url(SEED_EXPENSE_ID))
        assert response.status_code == 302, "Expected redirect when logged out"
        assert "/login" in response.headers["Location"]

    def test_post_logged_out_redirects_to_login(self, client):
        response = client.post(delete_url(SEED_EXPENSE_ID))
        assert response.status_code == 302, "Expected redirect when logged out"
        assert "/login" in response.headers["Location"]

    def test_post_logged_out_deletes_nothing(self, client):
        before = all_expense_rows()
        client.post(delete_url(SEED_EXPENSE_ID))
        assert fetch_expense(SEED_EXPENSE_ID) is not None, (
            "Logged-out POST must not delete the expense"
        )
        assert all_expense_rows() == before

    def test_get_logged_out_deletes_nothing(self, client):
        before = all_expense_rows()
        client.get(delete_url(SEED_EXPENSE_ID))
        assert all_expense_rows() == before

    def test_logged_out_missing_id_redirects_not_404(self, client):
        """Auth guard comes before the existence check."""
        response = client.get(delete_url(MISSING_ID))
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ------------------------------------------------------------------ #
# Profile Delete links                                               #
# ------------------------------------------------------------------ #

class TestProfileDeleteLinks:
    def test_profile_has_delete_link_for_each_seed_row(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert body.count("/delete") >= 8, (
            "Expected one Delete link per transaction row (8 seeded)"
        )

    def test_profile_delete_link_targets_expense_id(self, auth_client):
        body = auth_client.get("/profile").data.decode("utf-8")
        assert delete_url(SEED_EXPENSE_ID) in body, (
            "Expected a Delete link to /expenses/1/delete"
        )

    def test_profile_shows_delete_text(self, auth_client):
        response = auth_client.get("/profile")
        assert b"Delete" in response.data

    def test_profile_keeps_edit_links_alongside_delete(self, auth_client):
        body = auth_client.get("/profile").data.decode("utf-8")
        assert f"/expenses/{SEED_EXPENSE_ID}/edit" in body
        assert delete_url(SEED_EXPENSE_ID) in body


# ------------------------------------------------------------------ #
# GET confirmation page                                              #
# ------------------------------------------------------------------ #

class TestConfirmationPage:
    def test_get_returns_200(self, auth_client):
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert response.status_code == 200

    def test_get_shows_delete_expense_title(self, auth_client):
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert b"Delete expense" in response.data

    def test_get_shows_amount_with_rupee_and_two_decimals(self, auth_client):
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert f"₹{SEED_EXPENSE_AMOUNT}".encode("utf-8") in response.data, (
            "Expected amount formatted as ₹12.50"
        )

    def test_get_shows_category(self, auth_client):
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert SEED_EXPENSE_CATEGORY.encode() in response.data

    def test_get_shows_date(self, auth_client):
        expense_date = fetch_expense(SEED_EXPENSE_ID)["date"]
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert str(expense_date).encode() in response.data, (
            "Expected the expense date on the confirmation page"
        )

    def test_get_shows_description(self, auth_client):
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert SEED_EXPENSE_DESCRIPTION.encode() in response.data

    def test_get_null_description_shows_em_dash(self, auth_client, seed_user_id):
        null_id = create_expense(
            seed_user_id, 5.00, "Other", date.today().isoformat(), None
        )
        null_page = auth_client.get(delete_url(null_id))
        assert null_page.status_code == 200
        described_page = auth_client.get(delete_url(SEED_EXPENSE_ID))
        dash = "—".encode("utf-8")
        assert dash in null_page.data, "Expected em dash for NULL description"
        assert null_page.data.count(dash) > described_page.data.count(dash), (
            "NULL-description page should show an extra em dash placeholder"
        )

    def test_get_has_post_form_to_same_url(self, auth_client):
        body = auth_client.get(delete_url(SEED_EXPENSE_ID)).data.decode("utf-8")
        assert 'method="post"' in body.lower()
        assert delete_url(SEED_EXPENSE_ID) in body

    def test_get_has_cancel_link_to_profile(self, auth_client):
        body = auth_client.get(delete_url(SEED_EXPENSE_ID)).data.decode("utf-8")
        assert "Cancel" in body
        assert 'href="/profile"' in body

    def test_get_does_not_delete(self, auth_client):
        before = all_expense_rows()
        auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert fetch_expense(SEED_EXPENSE_ID) is not None, "GET must not delete"
        assert all_expense_rows() == before

    def test_get_twice_still_200(self, auth_client):
        auth_client.get(delete_url(SEED_EXPENSE_ID))
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert response.status_code == 200


# ------------------------------------------------------------------ #
# POST delete                                                        #
# ------------------------------------------------------------------ #

class TestDeletePost:
    def test_post_redirects_302_to_profile(self, auth_client):
        response = auth_client.post(delete_url(SEED_EXPENSE_ID))
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile"), (
            f"Expected redirect to /profile, got {response.headers['Location']}"
        )

    def test_post_removes_row_from_db(self, auth_client, seed_user_id):
        assert count_expenses(seed_user_id) == 8
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        assert fetch_expense(SEED_EXPENSE_ID) is None, "Row should be deleted"
        assert count_expenses(seed_user_id) == 7

    def test_post_flashes_expense_deleted(self, auth_client):
        response = auth_client.post(
            delete_url(SEED_EXPENSE_ID), follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Expense deleted." in response.data

    def test_flash_not_shown_on_get_confirmation(self, auth_client):
        response = auth_client.get(delete_url(SEED_EXPENSE_ID))
        assert b"Expense deleted." not in response.data

    def test_post_ignores_form_user_id(self, auth_client, other_user_expense_id):
        """user_id comes from the session; a spoofed form field is ignored."""
        other = fetch_expense(other_user_expense_id)
        response = auth_client.post(
            delete_url(other_user_expense_id),
            data={"user_id": other["user_id"]},
        )
        assert response.status_code == 404
        assert fetch_expense(other_user_expense_id) is not None


# ------------------------------------------------------------------ #
# Profile reflects the delete                                        #
# ------------------------------------------------------------------ #

class TestProfileAfterDelete:
    def test_total_before_delete_baseline(self, auth_client):
        response = auth_client.get("/profile")
        assert f"₹{SEED_TOTAL_BEFORE}".encode("utf-8") in response.data

    def test_total_drops_after_delete(self, auth_client):
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        response = auth_client.get("/profile")
        assert f"₹{SEED_TOTAL_AFTER}".encode("utf-8") in response.data, (
            "Expected total to drop by the deleted amount"
        )
        assert f"₹{SEED_TOTAL_BEFORE}".encode("utf-8") not in response.data

    def test_delete_link_removed_and_others_remain(self, auth_client):
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        body = auth_client.get("/profile").data.decode("utf-8")
        assert delete_url(SEED_EXPENSE_ID) not in body, (
            "Deleted row should no longer appear in transaction history"
        )
        assert body.count("/delete") == 7, "Expected 7 remaining Delete links"

    def test_transaction_row_count_after_delete(self, auth_client):
        before = auth_client.get("/profile").data.decode("utf-8")
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        after = auth_client.get("/profile").data.decode("utf-8")
        assert before.count("/delete") - after.count("/delete") == 1

    def test_category_breakdown_no_longer_includes_amount(self, auth_client):
        """Food had 12.50 + 22.30 = 34.80; after delete only 22.30 remains."""
        before = auth_client.get("/profile").data
        assert "₹34.80".encode("utf-8") in before, "Baseline Food total"
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        after = auth_client.get("/profile").data
        assert "₹34.80".encode("utf-8") not in after, (
            "Food category total should drop by the deleted expense"
        )


# ------------------------------------------------------------------ #
# 404 handling                                                       #
# ------------------------------------------------------------------ #

class TestNotFound:
    def test_repeat_post_returns_404(self, auth_client):
        first = auth_client.post(delete_url(SEED_EXPENSE_ID))
        assert first.status_code == 302
        second = auth_client.post(delete_url(SEED_EXPENSE_ID))
        assert second.status_code == 404, "Second delete must 404"

    def test_get_after_delete_returns_404(self, auth_client):
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        assert auth_client.get(delete_url(SEED_EXPENSE_ID)).status_code == 404

    def test_get_nonexistent_id_returns_404(self, auth_client):
        assert auth_client.get(delete_url(MISSING_ID)).status_code == 404

    def test_post_nonexistent_id_returns_404(self, auth_client):
        before = all_expense_rows()
        response = auth_client.post(delete_url(MISSING_ID))
        assert response.status_code == 404
        assert all_expense_rows() == before, "Nothing should be deleted"

    def test_get_other_users_expense_returns_404(
        self, auth_client, other_user_expense_id
    ):
        assert auth_client.get(delete_url(other_user_expense_id)).status_code == 404

    def test_post_other_users_expense_returns_404(
        self, auth_client, other_user_expense_id
    ):
        response = auth_client.post(delete_url(other_user_expense_id))
        assert response.status_code == 404

    def test_post_other_users_expense_is_not_deleted(
        self, auth_client, other_user_expense_id
    ):
        auth_client.post(delete_url(other_user_expense_id))
        assert fetch_expense(other_user_expense_id) is not None, (
            "Another user's expense must survive a foreign delete attempt"
        )

    def test_get_other_users_expense_does_not_leak_details(
        self, auth_client, other_user_expense_id
    ):
        response = auth_client.get(delete_url(other_user_expense_id))
        assert b"Other's secret" not in response.data
        assert "₹77.00".encode("utf-8") not in response.data

    def test_other_user_cannot_delete_demo_expense(self, client, app):
        """Reverse direction: second user cannot delete the seeded expense."""
        create_user("Mallory", "mallory@example.com", "mallorypass1")
        client.post(
            "/login",
            data={"email": "mallory@example.com", "password": "mallorypass1"},
        )
        response = client.post(delete_url(SEED_EXPENSE_ID))
        assert response.status_code == 404
        assert fetch_expense(SEED_EXPENSE_ID) is not None


# ------------------------------------------------------------------ #
# Isolation from other expenses                                      #
# ------------------------------------------------------------------ #

class TestIsolation:
    def test_delete_leaves_other_expenses_untouched(self, auth_client):
        before = [r for r in all_expense_rows() if r[0] != SEED_EXPENSE_ID]
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        after = all_expense_rows()
        assert after == before, "Only the targeted expense may be removed"

    def test_delete_does_not_affect_other_users_expenses(
        self, auth_client, other_user_expense_id
    ):
        before = fetch_expense(other_user_expense_id)
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        after = fetch_expense(other_user_expense_id)
        assert after is not None
        assert tuple(after) == tuple(before)

    def test_delete_does_not_remove_user(self, auth_client, seed_user_id):
        auth_client.post(delete_url(SEED_EXPENSE_ID))
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id FROM expenses WHERE user_id = ?", (seed_user_id,)
            ).fetchone()
            user = conn.execute(
                "SELECT id FROM users WHERE id = ?", (seed_user_id,)
            ).fetchone()
        finally:
            conn.close()
        assert user is not None, "User row must remain"
        assert row is not None, "Remaining expenses must remain"

    @pytest.mark.parametrize("expense_id", [2, 5, 8])
    def test_delete_other_seed_expense_leaves_expense_one(
        self, auth_client, expense_id
    ):
        response = auth_client.post(delete_url(expense_id))
        assert response.status_code == 302
        assert fetch_expense(expense_id) is None
        assert fetch_expense(SEED_EXPENSE_ID) is not None
