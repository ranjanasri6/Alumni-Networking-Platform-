from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect("alumni.db")
    c = conn.cursor()

    # Users Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        field TEXT,
        company TEXT,
        bio TEXT
    )
    """)

    # Mentorship Requests Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS mentorship_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        alumni_id INTEGER,
        message TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]
        field = request.form["field"]
        company = request.form["company"]
        bio = request.form["bio"]

        conn = sqlite3.connect("alumni.db")
        c = conn.cursor()

        try:
            c.execute("""
            INSERT INTO users (name, email, password, role, field, company, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, email, password, role, field, company, bio))
            conn.commit()
        except:
            conn.close()
            return "Email already registered!"

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("alumni.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["role"] = user[4]
            return redirect(url_for("dashboard"))

        return "Invalid email or password!"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("alumni.db")
    c = conn.cursor()

    if session["role"] == "student":

        # Show all alumni
        c.execute("SELECT * FROM users WHERE role='alumni'")
        alumni = c.fetchall()

        # Student's requests
        c.execute("""
        SELECT mentorship_requests.id,
               users.name,
               mentorship_requests.message,
               mentorship_requests.status,
               mentorship_requests.created_at
        FROM mentorship_requests
        JOIN users ON mentorship_requests.alumni_id = users.id
        WHERE mentorship_requests.student_id=?
        """, (session["user_id"],))

        my_requests = c.fetchall()

        conn.close()

        return render_template("dashboard.html",
                               role="student",
                               alumni=alumni,
                               my_requests=my_requests,
                               name=session["name"])

    else:

        # Alumni sees requests sent to them
        c.execute("""
        SELECT mentorship_requests.id,
               users.name,
               mentorship_requests.message,
               mentorship_requests.status,
               mentorship_requests.created_at
        FROM mentorship_requests
        JOIN users ON mentorship_requests.student_id = users.id
        WHERE mentorship_requests.alumni_id=?
        """, (session["user_id"],))

        requests = c.fetchall()

        conn.close()

        return render_template("dashboard.html",
                               role="alumni",
                               requests=requests,
                               name=session["name"])

# ---------------- SEND REQUEST ----------------
@app.route("/request/<int:alumni_id>", methods=["POST"])
def send_request(alumni_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    message = request.form["message"]

    conn = sqlite3.connect("alumni.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO mentorship_requests (student_id, alumni_id, message, created_at)
    VALUES (?, ?, ?, ?)
    """, (session["user_id"], alumni_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

# ---------------- UPDATE STATUS ----------------
@app.route("/update/<int:req_id>/<status>")
def update_status(req_id, status):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("alumni.db")
    c = conn.cursor()

    c.execute("UPDATE mentorship_requests SET status=? WHERE id=?", (status, req_id))
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
