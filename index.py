from flask import Flask, redirect, url_for, render_template
import sqlite3
from sqlalchemy import sql

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('base.html')


if __name__ == '__main__':
    app.run(debug=True)