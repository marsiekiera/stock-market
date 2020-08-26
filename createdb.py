from cs50 import SQL
import sqlite3

conn = sqlite3.connect('finance.db')

db = SQL("sqlite:///finance.db")

db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, hash TEXT NOT NULL, cash NUMERIC DEFAULT 50);")
db.execute("CREATE TABLE history (id INTEGER PRIMARY KEY, user_id INTEGER, stock_symbol TEXT NOT NULL, stock_name TEXT, shares INTEGER, price REAL, total REAL, date TEXT);")
db.execute("CREATE TABLE stocks (id INTEGER PRIMARY KEY, user_id INTEGER, stock_symbol TEXT NOT NULL, stock_name TEXT, shares INTEGER, price REAL, total REAL);")