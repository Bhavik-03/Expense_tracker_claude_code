import math
import sqlite3
from datetime import date, timedelta

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import queries
from database.db import (
    CATEGORIES,
    create_expense,
    create_user,
    get_db,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.before_request
def load_current_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        g.user = get_user_by_id(user_id)
        if g.user is None:
            session.clear()


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        return render_template("register.html", error="All fields are required.")

    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email already registered.")

    flash("Account created — please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    if request.method != "POST":
        abort(405)

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="All fields are required.")

    user = get_user_by_email(email)

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    flash("Welcome back!")
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))

    filter_error = None
    if start and end and start > end:
        filter_error = "Start date must be on or before end date."
        start = end = None

    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None

    user_id = g.user["id"]
    user = queries.get_user_by_id(user_id)

    transactions = queries.get_recent_transactions(user_id, start_date=start_iso, end_date=end_iso)
    stats = queries.get_summary_stats(user_id, start_date=start_iso, end_date=end_iso)
    categories = queries.get_category_breakdown(user_id, start_date=start_iso, end_date=end_iso)

    presets = _date_presets(date.today())
    for preset in presets:
        preset["active"] = (preset["start"], preset["end"]) == (start_iso, end_iso)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        start_date=start_iso,
        end_date=end_iso,
        filter_active=bool(start_iso or end_iso),
        presets=presets,
        range_label=_range_label(start, end),
        filter_error=filter_error,
    )


def _parse_date(value):
    try:
        return date.fromisoformat(value.strip())
    except (AttributeError, ValueError):
        return None


def _date_presets(today):
    return [
        {"label": "This month", "start": today.replace(day=1).isoformat(), "end": today.isoformat()},
        {"label": "Last 30 days", "start": (today - timedelta(days=29)).isoformat(), "end": today.isoformat()},
        {"label": "This year", "start": today.replace(month=1, day=1).isoformat(), "end": today.isoformat()},
        {"label": "All time", "start": None, "end": None},
    ]


def _range_label(start, end):
    fmt = "%d %b %Y"
    if start and end:
        return f"Showing {start.strftime(fmt)} – {end.strftime(fmt)}"
    if start:
        return f"Showing from {start.strftime(fmt)}"
    if end:
        return f"Showing up to {end.strftime(fmt)}"
    return None


@app.route("/analytics")
def analytics():
    if g.user is None:
        return redirect(url_for("login"))

    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if g.user is None:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            form={"date": date.today().isoformat()},
        )

    form = {
        "amount": request.form.get("amount", "").strip(),
        "category": request.form.get("category", "").strip(),
        "date": request.form.get("date", "").strip(),
        "description": request.form.get("description", "").strip(),
    }

    error = None
    try:
        amount = float(form["amount"])
    except ValueError:
        amount = None

    expense_date = _parse_date(form["date"])

    if amount is None or not math.isfinite(amount) or amount <= 0:
        error = "Amount must be a positive number."
    elif form["category"] not in CATEGORIES:
        error = "Please choose a valid category."
    elif expense_date is None:
        error = "Please enter a valid date."
    elif len(form["description"]) > 200:
        error = "Description must be 200 characters or fewer."

    if error:
        return render_template("add_expense.html", categories=CATEGORIES, form=form, error=error)

    create_expense(
        g.user["id"],
        round(amount, 2),
        form["category"],
        expense_date.isoformat(),
        form["description"] or None,
    )
    flash("Expense added.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
