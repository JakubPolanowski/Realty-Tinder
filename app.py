from flask import Flask, render_template
from glob import glob
from pathlib import Path

app = Flask(__name__)


@app.route('/')
def index():
    files = glob("data/listings/*.xlsx")
    files = [(p.stem.replace('_', ' '), p.stem)
             for p in [Path(f) for f in files]]
    return render_template('index.html', files=files)


@app.route('/listings/<string:listings_file>')
def listings(listings_file: str):
    # TODO read listing file then parse

    return render_template('listings.html', listings_file=listings_file)
