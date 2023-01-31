from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
from glob import glob
from pathlib import Path
import uuid
import pandas as pd
import json
import helpers
import re

app = Flask(__name__)

# secret key is used only for client side sessions
# therefore randomly generating at runtime seems preferrable
app.secret_key = uuid.uuid4().hex

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.context_processor
def inject_user():
    return dict(user=session.get('user'))


@app.route('/')
def index():
    files = glob("data/listings/*.xlsx")
    files = [(p.stem.replace('_', ' '), p.stem)
             for p in [Path(f) for f in files]]
    return render_template('index.html', files=files)


@app.errorhandler(404)
def error404(e):
    return render_template('error.html', error=404), 404


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == "POST":

        form = request.form

        if 'user' not in form:
            return render_template('error.html', error=400, subtitle="Bad request, user is required")
        if not re.match(r'^(?=.{3,20}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$', str(form['user'])):
            return render_template('error.html', error=400, subtitle="Invalid username. Should be 3-20 characters long, alpha numeric")
        else:
            session['user'] = form['user']
            return redirect(form['current_page'])

    else:
        return render_template('error.html', error=501, subtitle="dedicated login page not implemented"), 501


@app.route('/listings/<string:listings_file>', defaults={'index': 0}, methods=["GET", "POST"])
@app.route('/listings/<string:listings_file>/<int:index>', methods=["GET", "POST"])
def listings(listings_file: str, index: int):

    if request.method == "POST":
        form = request.form

        print(form.keys())

        if 'page' in form:
            return redirect(
                url_for('listings', listings_file=listings_file,
                        index=int(form['page'])-1)
            )

        if 'feedback' in form:
            if 'feedback' not in session:
                session['feedback'] = {}
            if form['filename'] not in session['feedback']:
                session['feedback'][form['filename']] = {}

            feedback = session['feedback'][form['filename']]
            feedback[int(form['index'])] = form['feedback']

            return redirect(
                url_for(
                    'listings', listings_file=form['filename'], index=int(form['index'])+1)
            )

        else:
            return render_template('error.html', error=400, subtitle="Invalid form POST"), 400

    else:

        if not (listing_path := Path(f"data/listings/{listings_file}.xlsx")).exists():
            return render_template('error.html', error=404, subtitle='The listings file does not exist'), 404

        if session.get('listings_file') != listings_file:
            df = pd.read_excel(listing_path)
            df['list date'] = df['list date'].dt.strftime('%m/%d/%Y')

            session['listings_file'] = listings_file
            session['listings'] = df.to_json(orient='records')

        dataset = json.loads(session['listings'])
        if index >= len(dataset):
            return render_template('error.html', error=404, subtitle=f'Out of bounds! There are only {len(dataset)} listing(s), {index+1} is invalid.'), 404

        listing = dataset[index]

        # special values
        listing = helpers.listing.prepare_special_values(listing)

        # added feedback to listing if exists
        listing['feedback'] = session.get('feedback', {})\
            .get(listings_file, {})\
            .get(index)

        # images
        images = helpers.listing.get_images_from_realtor(listing['url'])

        # render
        return render_template('listings.html', listings_file=listings_file, index=index, total=len(dataset), listing=listing, images=images)
