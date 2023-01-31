from flask import Flask, render_template, session
from flask_session import Session
from glob import glob
from pathlib import Path
import uuid
import pandas as pd

app = Flask(__name__)

# secret key is used only for client side sessions
# therefore randomly generating at runtime seems preferrable
app.secret_key = uuid.uuid4().hex

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route('/')
def index():
    files = glob("data/listings/*.xlsx")
    files = [(p.stem.replace('_', ' '), p.stem)
             for p in [Path(f) for f in files]]
    return render_template('index.html', files=files)


@app.route('/listings/<string:listings_file>')
def listings(listings_file: str):

    session['listings'] = pd.read_excel(
        f"data/listings/{listings_file}.xlsx").to_json(orient='records')

    return render_template('listings.html', listings_file=listings_file)
