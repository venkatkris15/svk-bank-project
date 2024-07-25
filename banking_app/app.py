from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import mysql.connector
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Establish MySQL connection
conn = mysql.connector.connect(
    user='root',
    password='2525',
    host='127.0.0.1',
    port=3306,
    database='banking_system'
)
cursor = conn.cursor()

# Create tables if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_id INT AUTO_INCREMENT PRIMARY KEY,
        account_number VARCHAR(20) UNIQUE NOT NULL,
        account_name VARCHAR(100) NOT NULL,
        balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
        account_number VARCHAR(20) NOT NULL,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description VARCHAR(255),
        amount DECIMAL(15, 2),
        balance DECIMAL(15, 2),
        FOREIGN KEY (account_number) REFERENCES accounts(account_number)
    )
""")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        account_number = request.form['account_number']
        account_name = request.form['account_name']
        try:
            cursor.execute("""
                INSERT INTO accounts (account_number, account_name, balance)
                VALUES (%s, %s, 0.00)
            """, (account_number, account_name))
            conn.commit()
            flash(f"Account '{account_number}' created successfully!", 'success')
            return redirect(url_for('index'))
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f"Error: {err}", 'danger')
    return render_template('create_account.html')

@app.route('/show_balance', methods=['GET', 'POST'])
def show_balance():
    if request.method == 'POST':
        account_number = request.form['account_number']
        try:
            cursor.execute("SELECT balance FROM accounts WHERE account_number = %s", (account_number,))
            result = cursor.fetchone()
            if result:
                balance = result[0]
                return render_template('show_balance.html', balance=balance, account_number=account_number)
            else:
                flash(f"Account '{account_number}' not found.", 'danger')
        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
    return render_template('show_balance.html')

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if request.method == 'POST':
        account_number = request.form['account_number']
        amount = float(request.form['amount'])
        try:
            cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_number = %s", (amount, account_number))
            conn.commit()
            cursor.execute("""
                INSERT INTO transactions (account_number, description, amount, balance)
                VALUES (%s, 'Deposit', %s, (SELECT balance FROM accounts WHERE account_number = %s))
            """, (account_number, amount, account_number))
            conn.commit()
            flash(f"Deposited ₹{amount:.2f} to account '{account_number}'", 'success')
            return redirect(url_for('index'))
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f"Error: {err}", 'danger')
    return render_template('deposit.html')

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if request.method == 'POST':
        account_number = request.form['account_number']
        amount = float(request.form['amount'])
        try:
            cursor.execute("UPDATE accounts SET balance = balance - %s WHERE account_number = %s", (amount, account_number))
            conn.commit()
            cursor.execute("""
                INSERT INTO transactions (account_number, description, amount, balance)
                VALUES (%s, 'Withdrawal', %s, (SELECT balance FROM accounts WHERE account_number = %s))
            """, (account_number, -amount, account_number))
            conn.commit()
            flash(f"Withdrew ₹{amount:.2f} from account '{account_number}'", 'success')
            return redirect(url_for('index'))
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f"Error: {err}", 'danger')
    return render_template('withdraw.html')

@app.route('/account_statement', methods=['GET', 'POST'])
def account_statement():
    if request.method == 'POST':
        account_number = request.form['account_number']
        download = request.form.get('download', False)
        try:
            cursor.execute("""
                SELECT transaction_date, description, amount, balance
                FROM transactions
                WHERE account_number = %s
                ORDER BY transaction_date
            """, (account_number,))
            statement = cursor.fetchall()
            
            if download:
                pdf_filename = f"account_statement_{account_number}.pdf"
                generate_pdf(account_number, statement, pdf_filename)
                return send_file(pdf_filename, as_attachment=True)
            
            return render_template('account_statement.html', statement=statement, account_number=account_number)
        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
    return render_template('account_statement.html')

@app.route('/account_holders', methods=['GET', 'POST'])
def account_holders():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '2525':
            try:
                cursor.execute("SELECT account_number, account_name, balance FROM accounts")
                account_holders = cursor.fetchall()
                return render_template('account_holders.html', account_holders=account_holders, show_table=True)
            except mysql.connector.Error as err:
                flash(f"Error: {err}", 'danger')
        else:
            flash("Incorrect password", 'danger')
    return render_template('account_holders.html', show_table=False)


def generate_pdf(account_number, statement, pdf_filename):
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"Account Statement for Account Number: {account_number}")
    c.setFont("Helvetica", 12)
    
    # Set initial y-coordinate for the statement entries
    y = 700
    
    for transaction in statement:
        transaction_date, description, amount, balance = transaction
        c.drawString(100, y, f"Date: {transaction_date}")
        c.drawString(250, y, f"Description: {description}")
        c.drawString(450, y, f"Amount: ₹{amount:.2f}")
        c.drawString(600, y, f"Balance: ₹{balance:.2f}")
        y -= 20
    
    c.save()
    flash(f"PDF generated: {pdf_filename}", 'success')

if __name__ == '__main__':
    app.run(debug=True)
