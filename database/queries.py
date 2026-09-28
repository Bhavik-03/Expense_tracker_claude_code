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


def _date_clause(start_date=None, end_date=None):
    sql, params = "", []
    if start_date:
        sql += " AND date >= ?"
        params.append(str(start_date))
    if end_date:
        sql += " AND date <= ?"
        params.append(str(end_date))
    return sql, params


# ------------------------------------------------------------------ #
# Transaction history                                                 #
# ------------------------------------------------------------------ #

def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    date_sql, date_params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + date_sql + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *date_params, limit),
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


# ------------------------------------------------------------------ #
# Summary stats                                                       #
# ------------------------------------------------------------------ #

def get_summary_stats(user_id, start_date=None, end_date=None):
    date_sql, date_params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?" + date_sql,
            (user_id, *date_params),
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?" + date_sql + " "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id, *date_params),
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

def get_category_breakdown(user_id, start_date=None, end_date=None):
    date_sql, date_params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS amount FROM expenses "
            "WHERE user_id = ?" + date_sql + " GROUP BY category ORDER BY amount DESC",
            (user_id, *date_params),
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
