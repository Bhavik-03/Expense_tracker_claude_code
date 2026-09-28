from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    name = row["name"]
    return {
        "name": name,
        "email": row["email"],
        "initials": "".join(part[0] for part in name.split()[:2]).upper(),
        "member_since": datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y"),
    }


# ------------------------------------------------------------------ #
# Transaction history                                                 #
# ------------------------------------------------------------------ #

def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


# ------------------------------------------------------------------ #
# Summary stats                                                       #
# ------------------------------------------------------------------ #

def get_summary_stats(user_id):
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    count = totals["count"] if totals else 0
    if not count:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": round(float(totals["total"]), 2),
        "transaction_count": int(count),
        "top_category": top["category"] if top else "—",
    }


# ------------------------------------------------------------------ #
# Category breakdown                                                  #
# ------------------------------------------------------------------ #

def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS amount FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY amount DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    total = sum(row["amount"] for row in rows)
    if not rows or not total:
        return []

    categories = [
        {
            "name": row["category"],
            "amount": row["amount"],
            "pct": int(round(row["amount"] / total * 100)),
        }
        for row in rows
    ]
    categories[0]["pct"] += 100 - sum(c["pct"] for c in categories)
    return categories
