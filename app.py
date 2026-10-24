
import os
import secrets
from decimal import Decimal, InvalidOperation

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from mysql.connector import IntegrityError

from database import get_db_connection


app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not full_name or not email or len(full_name) > 100:
        flash("Please enter a valid name and email address.", "error")
        return redirect(url_for("register"))

    if len(password) < 12:
        flash("Password must be at least 12 characters long.", "error")
        return redirect(url_for("register"))

    password_hash = generate_password_hash(password)
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor()

        # Create the user
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (full_name, email, password_hash)
        )

        user_id = cursor.lastrowid

        # Generate a 12-digit demonstration account number
        account_number = (
            "1" + "".join(
                secrets.choice("0123456789")
                for _ in range(11)
            )
        )

        # Create the user's bank account
        cursor.execute(
            """
            INSERT INTO accounts (user_id, account_number, balance)
            VALUES (%s, %s, %s)
            """,
            (user_id, account_number, 0.00)
        )

        # Save both records together
        connection.commit()

        flash("Account created successfully. You can now sign in.", "success")
        return redirect(url_for("login"))

    except IntegrityError:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Registration conflict")
        flash(
            "This email or account number already exists. Please try again.",
            "error"
        )
        return redirect(url_for("register"))

    except Exception:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Registration failed")
        flash("Registration failed. Please try again.", "error")
        return redirect(url_for("register"))

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, full_name, email, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    except Exception:
        app.logger.exception("Login failed")
        flash("Unable to sign in right now. Please try again.", "error")
        return redirect(url_for("login"))

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, account_number, balance
            FROM accounts
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )
        account = cursor.fetchone()

        transactions = []

        if account:
            cursor.execute(
                """
                SELECT transaction_type, amount, description, created_at
                FROM transactions
                WHERE account_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 10
                """,
                (account["id"],)
            )
            transactions = cursor.fetchall()

        return render_template(
            "dashboard.html",
            user_name=session.get("user_name", "Customer"),
            account=account,
            transactions=transactions
        )

    except Exception:
        app.logger.exception("Dashboard loading failed")
        return "Unable to load dashboard. Check the terminal.", 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



@app.route("/deposit", methods=["POST"])
def deposit():
    if "user_id" not in session:
        return redirect(url_for("login"))

    try:
        amount = Decimal(request.form.get("amount", "").strip())

        if not amount.is_finite() or amount <= 0:
            flash("Enter a valid deposit amount.", "error")
            return redirect(url_for("dashboard"))

        if amount.as_tuple().exponent < -2:
            flash("Use no more than two decimal places.", "error")
            return redirect(url_for("dashboard"))

    except (InvalidOperation, ValueError):
        flash("Enter a valid deposit amount.", "error")
        return redirect(url_for("dashboard"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, balance
            FROM accounts
            WHERE user_id = %s
            FOR UPDATE
            """,
            (session["user_id"],)
        )
        account = cursor.fetchone()

        if not account:
            connection.rollback()
            flash("No bank account was found.", "error")
            return redirect(url_for("dashboard"))

        cursor.execute(
            """
            UPDATE accounts
            SET balance = balance + %s
            WHERE id = %s
            """,
            (amount, account["id"])
        )

        cursor.execute(
            """
            INSERT INTO transactions
                (account_id, transaction_type, amount, description)
            VALUES (%s, %s, %s, %s)
            """,
            (account["id"], "deposit", amount, "Cash deposit")
        )

        connection.commit()
        flash("Deposit successful.", "success")

    except Exception:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Deposit failed")
        flash("Deposit failed. Please try again.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("dashboard"))




@app.route("/withdraw", methods=["POST"])
def withdraw():
    if "user_id" not in session:
        return redirect(url_for("login"))

    try:
        amount = Decimal(request.form.get("amount", "").strip())

        if not amount.is_finite() or amount <= 0:
            flash("Enter a valid withdrawal amount.", "error")
            return redirect(url_for("dashboard"))

        if amount.as_tuple().exponent < -2:
            flash("Use no more than two decimal places.", "error")
            return redirect(url_for("dashboard"))

    except (InvalidOperation, ValueError):
        flash("Enter a valid withdrawal amount.", "error")
        return redirect(url_for("dashboard"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, balance
            FROM accounts
            WHERE user_id = %s
            FOR UPDATE
            """,
            (session["user_id"],)
        )
        account = cursor.fetchone()

        if not account:
            connection.rollback()
            flash("No bank account was found.", "error")
            return redirect(url_for("dashboard"))

        if amount > Decimal(str(account["balance"])):
            connection.rollback()
            flash("Insufficient balance.", "error")
            return redirect(url_for("dashboard"))

        cursor.execute(
            """
            UPDATE accounts
            SET balance = balance - %s
            WHERE id = %s
            """,
            (amount, account["id"])
        )

        cursor.execute(
            """
            INSERT INTO transactions
                (account_id, transaction_type, amount, description)
            VALUES (%s, %s, %s, %s)
            """,
            (account["id"], "withdrawal", amount, "Cash withdrawal")
        )

        connection.commit()
        flash("Withdrawal successful.", "success")

    except Exception:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Withdrawal failed")
        flash("Withdrawal failed. Please try again.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("dashboard"))





@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
