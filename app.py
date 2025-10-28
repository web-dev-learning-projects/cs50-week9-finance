import os
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session.get("user_id")
    try:
        stocks = db.execute("SELECT * FROM user_shares WHERE user = ? AND quantity > 0", user_id)
        user = db.execute("SELECT * FROM users WHERE id=?", user_id)[0]
        user["stock_values"] = 0
    except Exception as error:
        return apology(f"Could not fetch the data. {error}", 500)
    
    stock_data = {}
    for stock in stocks:
        if stock["symbol"] not in stock_data:
            res = lookup(stock["symbol"])
            if res:
              stock_data[stock["symbol"]] = res
        user["stock_values"] += stock["quantity"]*stock_data[stock["symbol"]]["price"]

    return render_template("index.html", stocks=stocks, user=user, stock_data=stock_data)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol", "").strip()
        try:
            quantity = int(request.form.get("shares", "").strip())
        except:
            return apology("Enter positive integer for number of shares.")
        try:
            stock_data = lookup(symbol)
        except Exception as error:
            return apology(f"Error: {error}.", 400)
        
        if not stock_data:
            return apology("Invalid symbol.", 404)

        cost = quantity*stock_data["price"]

        try:
            user = db.execute("SELECT * FROM users WHERE id = ?", session.get("user_id"))[0]
        except:
            return apology("Could Not find the user.", 403)
        if cost > user.get("cash"):
            return apology("Not enough money to buy, you brook.")
        
        try:
            buy_stock = db.execute("INSERT INTO user_shares (user, symbol, price, quantity) VALUES(?, ?, ?, ?)", user.get("id"), symbol, stock_data["price"], quantity)
            user_update = db.execute("UPDATE users SET cash = ? WHERE id = ?", user.get("cash")-cost, user.get("id"))
            db.execute("INSERT INTO user_histories (user, symbol, buying_price, activity, quantity) VALUES(?, ?, ?, ?, ?)", user["id"], symbol, stock_data["price"], 'buy', quantity)

        except Exception as error:
            return apology(f"Couldn't buy the stock. {error}")
        
        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session.get("user_id")
    try:
        user = db.execute("SELECT * FROM users WHERE id = ?", user_id)[0]
    except:
        return apology("Could Not find the user.", 403)
    
    histories = db.execute("SELECT * FROM user_histories WHERE user=?", user_id)
    return render_template("history.html", histories=histories)


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
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
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("qoute.html")
    else:
        symbol = request.form.get("symbol", "")
        if not symbol:
            return apology("Provide valid symbol.", 400)
        try:
            data = lookup(symbol)
        except Exception as error:
            return apology(f"ERROR: {error}", 500)
        if not data:
            return apology(f"Code does not exist", 400)
        return render_template("qoute.html", data=data)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template('register_user.html')
    else:
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirmation", "").strip()
        
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)
        
        # Ensure confirm was submitted and equal
        elif not confirm or confirm != password:
            return apology("confirm password must match with password", 403)
    
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Ensure username exists and password is correct
        if len(rows) != 0:
            return apology("Username already exists.", 403)
        
        try:
            # register user 
            user = db.execute("INSERT INTO users (username, hash)  VALUES(?, ?)", username, generate_password_hash(password))
        except:
            return apology("INTERNAL SERVER ERROR", 500)
        
        # Remember which user has logged in
        session["user_id"] = user

        return redirect("/")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session.get("user_id")
    user = db.execute("SELECT * FROM users WHERE id=?", user_id)[0]
    if not user:
        return apology("Can't find you in database.") # TODO: not sure yet about this line
    share_list = db.execute("SELECT * FROM user_shares WHERE user=? AND quantity > 0", user_id)
    stock_data = {}
    for stock in share_list:
        if stock["symbol"] not in stock_data:
            res = lookup(stock["symbol"])
            if res:
              stock_data[stock["symbol"]] = res

    if request.method == "GET":
        return render_template("sell.html", stock_data=stock_data, share_list=share_list)
    else:
        share_symbol = request.form.get("symbol", "")
        try:
            quantity = int(request.form.get("shares", ""))
            if quantity < 0:
                raise ValueError("Shares must be non-negative integer.")
        except Exception as error:
            return apology(f"Error: Invalid share count {error}", 400)
        
        # find total share of that symbol
        share_list = db.execute("SELECT * FROM user_shares WHERE user=? AND symbol=? AND quantity > 0 ORDER BY created_at", user_id, share_symbol)
        if not share_list:
            return apology("This share doesn't exists", 404)
        
        res = lookup(share_symbol)
        curr_price = res["price"]
        share_count = db.execute("SELECT SUM(quantity) as count FROM user_shares WHERE user=? AND symbol=? AND quantity > 0 ORDER BY created_at", user_id, share_symbol)[0]['count']
        capital_gain = 0

        if share_count < quantity:
            return apology("Error: Not enough share to sell.", 400)
        for share in share_list:
            share_id = share["id"]
            if quantity <= 0:
                break
            if share["quantity"] >= quantity:
                # update quantity or add if unequal
                share_count = share["quantity"]
                curr_time = datetime.now()
                db.execute("UPDATE user_shares SET quantity=? , sold_quantity=? , updated_at=? WHERE id=?", share_count-min(share_count, quantity), min(share_count, quantity), curr_time, share_id)
                # add entry in history
                db.execute("INSERT INTO user_histories (user, symbol, buying_price, selling_price, activity, quantity) VALUES(?, ?, ?, ?, ?, ?)", user_id, share_symbol, share["price"], curr_price, 'sell', min(share_count, quantity))
                capital_gain += (curr_price*min(share_count, quantity))
                quantity -= share_count
        
        # update cash for user
        db.execute("UPDATE users SET cash=? WHERE id=?", user["cash"]+capital_gain, user_id)

        return redirect("/")