import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
#if not os.environ.get("API_KEY"):
#    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    #user_name = db.execute("SELECT username FROM users WHERE id = :user_id", user_id = user_id)
    user_stocks = db.execute("SELECT stock_symbol, stock_name, shares FROM stocks WHERE user_id = :user_id", user_id=user_id)
    total = 0
    for i in range(0, len(user_stocks)):
        stock = lookup(user_stocks[i]["stock_symbol"])
        user_stocks[i]["price"] = usd(stock["price"])
        user_stocks[i]["total"] = stock["price"] * user_stocks[i]["shares"]
        total += user_stocks[i]["total"]
        user_stocks[i]["total"] = usd(user_stocks[i]["total"])
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id;", user_id=user_id)[0]["cash"]
    total = usd(total + cash)
    cash = usd(cash)
    return render_template("index.html", user_stocks=user_stocks, total=total, cash=cash)


# dodać że udało sie wykonać transakcje
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # datetime of transaction
        datetime_transaction = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        stock = lookup(request.form.get("symbol"))

        # check if stock exist
        if stock == None:
            return apology("invalid symbol", 404)

        # min 1 shares
        shares = int(request.form.get("shares"))
        if shares < 1:
            return apology("minimum 1 shares", 403)

        stock_symbol = stock["symbol"]
        stock_name = stock["name"]
        stock_price = stock["price"]
        total = stock_price * shares
        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id = :user_id;", user_id=user_id)[0]["cash"]

        # check if user have enough cash
        if total > cash:
            return apology("You have not enough cash", 403)

        # create history of transaction
        db.execute("INSERT INTO history (user_id, stock_symbol, stock_name, shares, price, total, date) VALUES (:user_id, :stock_symbol, :stock_name, :shares, :price, :total, :date );", user_id=user_id, stock_symbol=stock_symbol, stock_name=stock_name, shares=shares, price=stock_price, total=total, date=datetime_transaction)

        current_stock = db.execute("SELECT * FROM stocks WHERE (user_id = :user_id AND stock_symbol = :stock_symbol);", user_id = user_id, stock_symbol = stock_symbol)

        # check if user already have this stock and update db
        if len(current_stock) == 1:
            new_total = current_stock[0]["total"] + total
            new_shares = current_stock[0]["shares"] + shares
            new_price = new_total / new_shares
            db.execute("UPDATE stocks SET shares = :new_shares, total = :new_total, price = :new_price WHERE (user_id = :user_id AND stock_symbol = :stock_symbol);", new_shares = new_shares, new_total = new_total, new_price = new_price, user_id = user_id, stock_symbol = stock_symbol)

        # create new row in table if user hasn't got this stock
        else:
            db.execute("INSERT INTO stocks (user_id, stock_symbol, stock_name, shares, price, total) VALUES (:user_id, :stock_symbol, :stock_name, :shares, :price, :total);", user_id = user_id, stock_symbol = stock_symbol, stock_name = stock_name, shares = shares, price = stock_price, total = total)
        cash -= total
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id;", cash=cash, user_id=user_id)
        flash("You have successfully bought stocks.")
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    user_history = db.execute("SELECT stock_symbol, stock_name, shares, price, total, date FROM history WHERE user_id = :user_id", user_id=user_id)
    for i in range(0, len(user_history)):
        if user_history[i]["price"]:
            user_history[i]["price"] = usd(user_history[i]["price"])
        user_history[i]["total"] = usd(user_history[i]["total"])
    #test = usd(user_history[0]['price'])

    return render_template("history.html", user_history=user_history)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        # Redirect user to home page
        flash("You were successfully logged in")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    flash("You have been successfully logged out.")
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if stock == None:
            return apology("invalid symbol", 404)
        stock_name = stock["name"]
        stock_symbol = stock["symbol"]
        stock_price = stock["price"]
        return render_template("quoted.html", stock_name=stock_name, stock_symbol=stock_symbol, stock_price=stock_price)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Check if username exist
        elif len(db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))) == 1:
            return apology("username exist", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure confirmation password was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password again", 403)

        # Check if password and re-type password are the same
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("must re-type password", 403)

        # Add user to database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash_password)", username=request.form.get("username"), hash_password=generate_password_hash(request.form.get("password")))

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        # Redirect user to home page
        flash("You have been successfully registered")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]
    # all users stocks
    user_stocks = db.execute("SELECT * FROM stocks WHERE user_id = :user_id", user_id = user_id)
    user_stocks_symbol = []
    for stock in user_stocks:
        user_stocks_symbol.append(stock["stock_symbol"])

    if request.method == "POST":
        # datetime of transaction
        datetime_transaction = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # stock from form to sell
        stock = lookup(request.form.get("symbol"))

        # check if stock exist
        if stock == None:
            return apology("invalid symbol", 404)

        # min 1 shares
        shares = int(request.form.get("shares"))
        if shares < 1:
            return apology("minimum 1 shares", 403)

        stock_symbol = stock["symbol"]
        stock_name = stock["name"]
        stock_price = stock["price"]
        total = stock_price * shares

        current_stock = db.execute("SELECT * FROM stocks WHERE (user_id = :user_id AND stock_symbol = :stock_symbol);", user_id = user_id, stock_symbol = stock_symbol)

        if len(current_stock) != 1:
            return apology("You haven't got this stock", 403)
        new_shares = current_stock[0]["shares"] - shares
        if new_shares < 0:
            return apology("You haven't got that many shares")

        cash = db.execute("SELECT cash FROM users WHERE id = :user_id;", user_id=user_id)[0]["cash"]
        cash += total
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id;", cash=cash, user_id=user_id)

        # create history of transaction
        db.execute("INSERT INTO history (user_id, stock_symbol, stock_name, shares, price, total, date) VALUES (:user_id, :stock_symbol, :stock_name, :shares, :price, :total, :date );", user_id=user_id, stock_symbol=stock_symbol, stock_name=stock_name, shares = -shares, price=stock_price, total=total, date=datetime_transaction)
        if new_shares == 0:
            db.execute("DELETE FROM stocks WHERE (user_id = :user_id AND stock_symbol = :stock_symbol);", user_id = user_id, stock_symbol = stock_symbol)
        else:
            # update db
            new_total = current_stock[0]["total"] - total
            new_price = new_total / new_shares
            db.execute("UPDATE stocks SET shares = :new_shares, total = :new_total, price = :new_price WHERE (user_id = :user_id AND stock_symbol = :stock_symbol);", new_shares = new_shares, new_total = new_total, new_price = new_price, user_id = user_id, stock_symbol = stock_symbol)
        flash("You have successfully sold your stocks.")
        return redirect("/")
    else:
        return render_template("sell.html", user_stocks_symbol=user_stocks_symbol)


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    if request.method == "POST":
        datetime_transaction = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        amount = float(request.form.get("amount"))
        action = request.form.get("action")
        user_id = session["user_id"]
        if action == "withdraw":
            db.execute("UPDATE users SET cash = cash - :amount WHERE id = :user_id", amount = amount, user_id = user_id)
            db.execute("INSERT INTO history (user_id, stock_symbol, total, date) VALUES (:user_id, :stock_symbol, :total, :date );", user_id=user_id, stock_symbol = "CASH", total = -amount, date=datetime_transaction)
            flash("You have successfully withdrawn cash.")
        else:
            db.execute("UPDATE users SET cash = cash + :amount WHERE id = :user_id", amount = amount, user_id = user_id)
            db.execute("INSERT INTO history (user_id, stock_symbol, total, date) VALUES (:user_id, :stock_symbol, :total, :date );", user_id=user_id, stock_symbol = "CASH", total = amount, date=datetime_transaction)
            flash("You have successfully deposited cash.")
        return redirect("/")
    else:
        return render_template("transfer.html")

@app.route("/account")
@login_required
def account():
    return render_template("account.html")


@app.route("/password", methods=["GET", "POST"])
@login_required
def password():
    if request.method == "POST":
        if not request.form.get("old_password"):
            return apology("You must provide current password", 400)
        elif not request.form.get("new_password"):
            return apology("You must provide new password", 400)
        elif not request.form.get("confirmation"):
            return apology("You must re-type new password", 400)
        elif request.form.get("new_password") != request.form.get("confirmation"):
            return apology("You must re-type password correct", 400)
        elif request.form.get("new_password") == request.form.get("old_password"):
            return apology("The new password cannot be the same as the old password.", 400)
        user_id = session["user_id"]
        hash_user = db.execute("SELECT hash FROM users WHERE id = ?;", user_id)[0]["hash"]
        if not check_password_hash(hash_user, request.form.get("old_password")):
            return apology("You must provide correct current password", 400)
        else:
            db.execute("UPDATE users SET hash = ? WHERE id = ?;", generate_password_hash(request.form.get("new_password")), user_id)
            
        # Forget any user_id
        session.clear()

        # Redirect user to login form
        flash("You have successfully changed your password. Please login again.")
        return redirect("/")
    else:
        return render_template("password.html")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    if request.method == "POST":
        user_id = session["user_id"]

        # Query database
        rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=user_id)

        # Ensure password is correct
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid password", 403)

        db.execute("DELETE FROM users WHERE id = :user_id;", user_id = user_id)
        db.execute("DELETE FROM stocks WHERE user_id = :user_id;", user_id = user_id)
        db.execute("DELETE FROM history WHERE user_id = :user_id;", user_id = user_id)

        # Forget any user_id
        session.clear()

        # Redirect user to login form
        flash("You have successfully deleted your account.")
        return redirect("/")
    else:
        return render_template("delete.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
