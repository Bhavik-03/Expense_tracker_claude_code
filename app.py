import sqlite3
from datetime import datetime

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, get_user_by_id, init_db, seed_db

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

    # The logged-in user's row is already loaded into g.user by load_current_user()
    name = g.user["name"]
    user = {
        "name": name,
        "email": g.user["email"],
        "initials": "".join(part[0] for part in name.split()[:2]).upper(),
        "member_since": datetime.strptime(g.user["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y"),
    }

    # Hardcoded sample data — replaced with real queries in Step 5
    transactions = [
        {"date": "2026-09-16", "description": "Dinner out", "category": "Food", "amount": 22.30},
        {"date": "2026-09-14", "description": "Miscellaneous", "category": "Other", "amount": 9.99},
        {"date": "2026-09-12", "description": "New shoes", "category": "Shopping", "amount": 45.20},
        {"date": "2026-09-10", "description": "Movie tickets", "category": "Entertainment", "amount": 15.75},
        {"date": "2026-09-08", "description": "Pharmacy", "category": "Health", "amount": 20.00},
        {"date": "2026-09-05", "description": "Electricity bill", "category": "Bills", "amount": 60.00},
        {"date": "2026-09-04", "description": "Gas", "category": "Transport", "amount": 35.00},
        {"date": "2026-09-02", "description": "Groceries", "category": "Food", "amount": 12.50},
    ]

    total_spent = sum(t["amount"] for t in transactions)

    totals = {}
    for t in transactions:
        totals[t["category"]] = totals.get(t["category"], 0) + t["amount"]

    categories = [
        {"name": name, "total": total, "pct": round(total / total_spent * 100)}
        for name, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]

    stats = {
        "total_spent": total_spent,
        "transaction_count": len(transactions),
        "top_category": categories[0]["name"],
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
