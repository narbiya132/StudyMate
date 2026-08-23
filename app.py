from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

DATABASE = "database.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    # Tasks table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            deadline TEXT NOT NULL,
            priority TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Student performance table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT UNIQUE NOT NULL,
            score REAL NOT NULL
        )
    """)

    # Add some sample performance data if table is empty
    existing = conn.execute(
        "SELECT COUNT(*) FROM performance"
    ).fetchone()[0]

    if existing == 0:
        sample_data = [
            ("Python", 45),
            ("DBMS", 75),
            ("Mathematics", 60),
            ("Computer Networks", 80)
        ]

        conn.executemany(
            "INSERT INTO performance (subject, score) VALUES (?, ?)",
            sample_data
        )

    conn.commit()
    conn.close()


# ---------------- RECOMMENDATION ----------------

def get_recommendation():
    conn = get_db()

    tasks = conn.execute("""
        SELECT * FROM tasks
        WHERE status = 'Pending'
    """).fetchall()

    performance = conn.execute("""
        SELECT * FROM performance
    """).fetchall()

    conn.close()

    if not tasks:
        return {
            "subject": "No pending tasks",
            "reason": "Add an academic task to get a study recommendation."
        }

    performance_dict = {
        row["subject"]: row["score"]
        for row in performance
    }

    best_task = None
    highest_score = -1
    best_reason = ""

    today = datetime.now().date()

    for task in tasks:

        score = 0
        reasons = []

        # Priority score
        if task["priority"] == "High":
            score += 30
            reasons.append("high priority")

        elif task["priority"] == "Medium":
            score += 15

        else:
            score += 5

        # Deadline score
        try:
            deadline = datetime.strptime(
                task["deadline"],
                "%Y-%m-%d"
            ).date()

            days_left = (deadline - today).days

            if days_left <= 0:
                score += 40
                reasons.append("deadline is today or overdue")

            elif days_left <= 2:
                score += 30
                reasons.append("deadline is very close")

            elif days_left <= 5:
                score += 15
                reasons.append("deadline is approaching")

        except ValueError:
            pass

        # Performance score
        subject_score = performance_dict.get(
            task["subject"],
            70
        )

        if subject_score < 50:
            score += 30
            reasons.append("your performance is low")

        elif subject_score < 60:
            score += 20
            reasons.append("your performance needs improvement")

        elif subject_score < 70:
            score += 10

        # Select highest scoring task
        if score > highest_score:
            highest_score = score
            best_task = task
            best_reason = ", ".join(reasons)

    return {
        "subject": best_task["subject"],
        "task": best_task["title"],
        "reason": best_reason.capitalize()
    }


# ---------------- DASHBOARD ----------------

@app.route("/")
def home():

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM tasks"
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status = 'Pending'"
    ).fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status = 'Completed'"
    ).fetchone()[0]

    high_priority = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE priority = 'High' AND status = 'Pending'"
    ).fetchone()[0]

    recent_tasks = conn.execute("""
        SELECT * FROM tasks
        ORDER BY deadline ASC
        LIMIT 5
    """).fetchall()

    conn.close()

    recommendation = get_recommendation()

    return render_template(
        "index.html",
        total=total,
        pending=pending,
        completed=completed,
        high_priority=high_priority,
        recent_tasks=recent_tasks,
        recommendation=recommendation
    )


# ---------------- ADD TASK ----------------

@app.route("/add", methods=["GET", "POST"])
def add_task():

    if request.method == "POST":

        title = request.form["title"]
        subject = request.form["subject"]
        deadline = request.form["deadline"]
        priority = request.form["priority"]
        description = request.form["description"]

        conn = get_db()

        conn.execute("""
            INSERT INTO tasks
            (title, subject, deadline, priority, description)
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            subject,
            deadline,
            priority,
            description
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return render_template("tasks.html")


# ---------------- COMPLETE TASK ----------------

@app.route("/complete/<int:task_id>")
def complete_task(task_id):

    conn = get_db()

    conn.execute("""
        UPDATE tasks
        SET status = 'Completed'
        WHERE id = ?
    """, (task_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ---------------- DELETE TASK ----------------

@app.route("/delete/<int:task_id>")
def delete_task(task_id):

    conn = get_db()

    conn.execute("""
        DELETE FROM tasks
        WHERE id = ?
    """, (task_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)