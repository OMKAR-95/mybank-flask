
# MyBank — Banking Web Application

MyBank is a simple banking web application built using Python, Flask, and MySQL. It demonstrates account registration, login, deposits, withdrawals, and transaction history.

## Features

- User registration and login
- Password hashing
- Automatic demo account creation
- Account number and balance display
- Deposit and withdrawal functionality
- Recent transaction history
- MySQL database integration
- Responsive user interface

## Technologies

- Python
- Flask
- MySQL
- HTML
- CSS
- Jinja2
- Werkzeug

## Project Structure

- `app.py` — Flask routes and application logic
- `database.py` — MySQL connection
- `templates/` — HTML templates
- `static/css/style.css` — application styling
- `requirements.txt` — Python dependencies

## Setup

1. Install Python 3 and MySQL.
2. Create a MySQL database named `bank`.
3. Create the required `users`, `accounts`, and `transactions` tables.
4. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Set the database and Flask environment variables in your terminal:

   ```bash
   export DB_HOST="localhost"
   export DB_USER="root"
   export DB_NAME="bank"
   export DB_PASSWORD="your_mysql_password"
   export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```

   Replace `your_mysql_password` with your own local MySQL password. Never publish real credentials.

7. Start the application:

   ```bash
   python app.py
   ```

8. Open `http://127.0.0.1:5000` in your browser.

## Disclaimer

This is an educational banking demo. It does not process real money and is not intended for real financial use.
