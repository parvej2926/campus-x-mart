import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import get_connection


def generate_market_report() -> bytes:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM items;")
        total_listings = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM users;")
        total_users = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'COMPLETED';")
        completed_orders = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COALESCE(SUM(agreed_price), 0) FROM orders WHERE status = 'COMPLETED';")
        revenue = float(cursor.fetchone()[0] or 0)

        cursor.execute(
            "SELECT category, COUNT(*) FROM items GROUP BY category ORDER BY COUNT(*) DESC LIMIT 3;"
        )
        top_categories = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setTitle("Campus X Mart Market Report")
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "Campus X Mart Market Report")

    c.setFont("Helvetica", 12)
    lines = [
        f"- Total listings: {total_listings}",
        f"- Registered users: {total_users}",
        f"- Completed orders: {completed_orders}",
        f"- Revenue from completed orders: ৳{revenue:,.2f}",
        "- Top categories: " + (
            ", ".join(f"{category} ({count})" for category, count in top_categories) if top_categories else "N/A"
        ),
        "- Admin notes: Review item quality, verification status, and seller activity.",
    ]

    y = height - 110
    for line in lines:
        c.drawString(60, y, line)
        y -= 22

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 120, "Prepared for campus marketplace review")
    c.save()

    return buffer.getvalue()


if __name__ == "__main__":
    print(len(generate_market_report()))
