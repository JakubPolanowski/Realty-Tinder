from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
from glob import glob
from pathlib import Path
import uuid
import pandas as pd
import json
import helpers

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


@app.errorhandler(404)
def error404(e):
    return render_template('404.html'), 404


@app.route('/listings/<string:listings_file>', defaults={'index': 0}, methods=["GET", "POST"])
@app.route('/listings/<string:listings_file>/<int:index>', methods=["GET", "POST"])
def listings(listings_file: str, index: int):

    if request.method == "POST":
        form = request.form

        if 'page' in form:
            return redirect(
                url_for('listings', listings_file=listings_file,
                        index=int(form['page'])-1)
            )

        else:  # TODO pick proper error code
            return render_template('404.html', subtitle="Invalid form POST"), 404

    else:

        if not (listing_path := Path(f"data/listings/{listings_file}.xlsx")).exists():
            return render_template('404.html', subtitle='The listings file does not exist'), 404

        if session.get('listings_file') != listings_file:
            df = pd.read_excel(listing_path)
            df['list date'] = df['list date'].dt.strftime('%m/%d/%Y')

            session['listings_file'] = listings_file
            session['listings'] = df.to_json(orient='records')

        dataset = json.loads(session['listings'])
        if index >= len(dataset):
            return render_template('404.html', subtitle=f'Out of bounds! There are only {len(dataset)} listing(s), {index+1} is invalid.'), 404

        listing = dataset[index]

        # special values
        listing = helpers.listings.prepare_special_values(listing)

        # render
        return render_template('listings.html', listings_file=listings_file, index=index, total=len(dataset), listing=listing)
