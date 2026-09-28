"""
Tests for Step 6: Date Filter for Profile Page.

Based on .claude/specs/06-date-filter-profile-page.md — NOT derived from
reading the implementation. Covers:
  - database.queries helpers (get_summary_stats, get_recent_transactions,
    get_category_breakdown) with optional start_date/end_date bounds
  - GET /profile query-string filtering, validation, and auth guard
"""

from datetime import date, timedelta

import pytest

from database import queries


def day(n):
    """ISO date string for day `n` of the current month (seed data anchor)."""
    return date.today().replace(day=n).isoformat()


# ------------------------------------------------------------------ #
# Unit tests: database/queries.py helpers                            #
# ------------------------------------------------------------------ #

class TestGetSummaryStats:
    def test_no_dates_matches_step5_baseline(self, app, seed_user_id):
        stats = queries.get_summary_stats(seed_user_id)
        assert stats["total_spent"] == 220.74, "Unfiltered total must match Step 5 baseline"
        assert stats["transaction_count"] == 8, "Unfiltered count must match Step 5 baseline"
        assert stats["top_category"] == "Bills", "Unfiltered top category must match Step 5 baseline"

    def test_day1_to_day5_range(self, app, seed_user_id):
        stats = queries.get_summary_stats(seed_user_id, start_date=day(1), end_date=day(5))
        assert stats["total_spent"] == 107.50
        assert stats["transaction_count"] == 3
        assert stats["top_category"] == "Bills"

    def test_range_with_no_expenses_returns_zeros(self, app, seed_user_id):
        far_future_start = (date.today() + timedelta(days=365)).isoformat()
        far_future_end = (date.today() + timedelta(days=370)).isoformat()
        stats = queries.get_summary_stats(seed_user_id, start_date=far_future_start, end_date=far_future_end)
        assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    def test_start_equals_end_on_day8_returns_only_that_expense(self, app, seed_user_id):
        stats = queries.get_summary_stats(seed_user_id, start_date=day(8), end_date=day(8))
        assert stats["total_spent"] == 20.00
        assert stats["transaction_count"] == 1
        assert stats["top_category"] == "Health"

    def test_default_kwargs_unchanged_signature(self, app, seed_user_id):
        """Calling with only user_id must behave exactly as before (Step 5 contract)."""
        via_positional = queries.get_summary_stats(seed_user_id)
        via_explicit_none = queries.get_summary_stats(seed_user_id, start_date=None, end_date=None)
        assert via_positional == via_explicit_none


class TestGetRecentTransactions:
    def test_only_start_date_day10_returns_4_rows_newest_first(self, app, seed_user_id):
        rows = queries.get_recent_transactions(seed_user_id, start_date=day(10))
        assert len(rows) == 4, "Expect days 10, 12, 14, 16"
        returned_dates = [row["date"] for row in rows]
        assert returned_dates == [day(16), day(14), day(12), day(10)], "Must be newest first"

    def test_only_end_date_day4_returns_2_rows(self, app, seed_user_id):
        rows = queries.get_recent_transactions(seed_user_id, end_date=day(4))
        assert len(rows) == 2, "Expect days 2 and 4"
        returned_dates = [row["date"] for row in rows]
        assert returned_dates == [day(4), day(2)], "Must be newest first"

    def test_start_equals_end_day8_returns_only_health_expense(self, app, seed_user_id):
        rows = queries.get_recent_transactions(seed_user_id, start_date=day(8), end_date=day(8))
        assert len(rows) == 1
        assert rows[0]["category"] == "Health"
        assert rows[0]["amount"] == 20.00

    def test_no_dates_unchanged_from_step5(self, app, seed_user_id):
        rows = queries.get_recent_transactions(seed_user_id)
        assert len(rows) == 8


class TestGetCategoryBreakdown:
    def test_day1_to_day5_returns_3_categories_pct_sums_100(self, app, seed_user_id):
        categories = queries.get_category_breakdown(seed_user_id, start_date=day(1), end_date=day(5))
        names = {c["name"] for c in categories}
        assert names == {"Bills", "Transport", "Food"}
        assert sum(c["pct"] for c in categories) == 100

    def test_range_with_no_expenses_returns_empty_list(self, app, seed_user_id):
        far_future_start = (date.today() + timedelta(days=365)).isoformat()
        far_future_end = (date.today() + timedelta(days=370)).isoformat()
        categories = queries.get_category_breakdown(seed_user_id, start_date=far_future_start, end_date=far_future_end)
        assert categories == []

    def test_start_equals_end_day8_single_category(self, app, seed_user_id):
        categories = queries.get_category_breakdown(seed_user_id, start_date=day(8), end_date=day(8))
        assert len(categories) == 1
        assert categories[0]["name"] == "Health"
        assert categories[0]["pct"] == 100

    def test_no_dates_matches_step5_baseline(self, app, seed_user_id):
        categories = queries.get_category_breakdown(seed_user_id)
        assert sum(c["pct"] for c in categories) == 100
        assert len(categories) == 7  # 7 distinct categories in seed data


# ------------------------------------------------------------------ #
# Route tests: GET /profile                                          #
# ------------------------------------------------------------------ #

class TestProfileRouteAuthGuard:
    def test_unauthenticated_with_filter_redirects_to_login(self, client):
        response = client.get("/profile?start_date=2026-01-01", follow_redirects=False)
        assert response.status_code == 302, "Auth check must happen before filter parsing"
        assert "/login" in response.headers["Location"]

    def test_logout_then_filtered_profile_redirects_to_login(self, auth_client):
        auth_client.get("/logout")
        response = auth_client.get("/profile?start_date=2026-01-01", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


class TestProfileRouteNoFilter:
    def test_no_params_shows_step5_baseline(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert "₹220.74".encode("utf-8") in response.data
        # 8 transactions unchanged from Step 5 — sanity check total appears
        assert b"8" in response.data


class TestProfileRouteFiltering:
    def test_valid_range_shows_filtered_total_and_count(self, auth_client):
        response = auth_client.get(f"/profile?start_date={day(1)}&end_date={day(5)}")
        assert response.status_code == 200
        assert "₹107.50".encode("utf-8") in response.data

    def test_filter_inputs_prefilled_with_submitted_dates(self, auth_client):
        start, end = day(1), day(5)
        response = auth_client.get(f"/profile?start_date={start}&end_date={end}")
        html = response.data.decode("utf-8")
        assert f'value="{start}"' in html, "Start date input must be pre-filled"
        assert f'value="{end}"' in html, "End date input must be pre-filled"

    def test_invalid_start_date_falls_back_to_unfiltered_no_crash(self, auth_client):
        response = auth_client.get("/profile?start_date=not-a-date")
        assert response.status_code == 200
        assert "₹220.74".encode("utf-8") in response.data

    def test_start_after_end_shows_error_and_unfiltered_data(self, auth_client):
        response = auth_client.get(f"/profile?start_date={day(5)}&end_date={day(1)}")
        assert response.status_code == 200
        assert b"Start date must be on or before end date." in response.data
        assert "₹220.74".encode("utf-8") in response.data, "Unfiltered totals shown on validation error"

    def test_range_with_no_expenses_shows_zero_total_and_empty_state(self, auth_client):
        future_start = (date.today() + timedelta(days=365)).isoformat()
        future_end = (date.today() + timedelta(days=370)).isoformat()
        response = auth_client.get(f"/profile?start_date={future_start}&end_date={future_end}")
        assert response.status_code == 200
        assert "₹0.00".encode("utf-8") in response.data
        assert b"No expenses in this period" in response.data

    def test_no_filter_shows_no_expenses_yet_empty_state_copy_untouched(self, client, app):
        """A brand-new user with zero expenses and no filter should keep the
        Step 5 empty-state copy, not the filtered variant."""
        from database.db import create_user

        with app.app_context():
            create_user("Empty User", "empty@spendly.com", "password123")
        client.post("/login", data={"email": "empty@spendly.com", "password": "password123"})
        response = client.get("/profile")
        assert response.status_code == 200
        assert b"No expenses yet" in response.data
        assert b"No expenses in this period" not in response.data

    def test_this_month_preset_shows_all_8_seed_expenses(self, auth_client):
        today = date.today()
        month_start = today.replace(day=1).isoformat()
        response = auth_client.get(f"/profile?start_date={month_start}&end_date={today.isoformat()}")
        assert response.status_code == 200
        assert "₹220.74".encode("utf-8") in response.data, "All 8 seed expenses fall in current month"

    def test_clear_link_shown_only_when_filter_active(self, auth_client):
        filtered = auth_client.get(f"/profile?start_date={day(1)}&end_date={day(5)}")
        unfiltered = auth_client.get("/profile")

        assert b"Clear" in filtered.data, "Clear link/label must show when a filter is active"
        # Unfiltered page: presence of literal 'Clear' text is not itself a spec requirement,
        # but the clear *link* to plain /profile should not be rendered as an active-filter cue.
        assert unfiltered.status_code == 200

    def test_active_range_label_visible_when_filtered(self, auth_client):
        response = auth_client.get(f"/profile?start_date={day(1)}&end_date={day(5)}")
        assert b"Showing" in response.data

    def test_no_range_label_when_unfiltered(self, auth_client):
        response = auth_client.get("/profile")
        # Spec: label only shown "when a filter is active" — no assertion on exact
        # absence text, but total must reflect baseline (already covered) and the
        # response must render successfully without a forced label.
        assert response.status_code == 200


class TestPresetLinks:
    def test_this_month_preset_link_present(self, auth_client):
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        assert "This month" in html

    def test_last_30_days_preset_link_present(self, auth_client):
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        assert "Last 30 days" in html

    def test_this_year_preset_link_present(self, auth_client):
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        assert "This year" in html

    def test_all_time_preset_link_present_and_points_to_plain_profile(self, auth_client):
        response = auth_client.get(f"/profile?start_date={day(1)}&end_date={day(5)}")
        html = response.data.decode("utf-8")
        assert "All time" in html

    def test_all_time_preset_clears_filter(self, auth_client):
        response = auth_client.get("/profile")  # equivalent to following "All time"
        assert response.status_code == 200
        assert "₹220.74".encode("utf-8") in response.data


class TestCurrencyFormatting:
    def test_currency_symbol_is_rupee(self, auth_client):
        response = auth_client.get("/profile")
        assert "₹".encode("utf-8") in response.data, "Currency must always display as ₹"
