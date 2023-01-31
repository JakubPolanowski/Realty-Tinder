from flask import Flask, render_template
from glob import glob
from pathlib import Path

app = Flask(__name__)


@app.route('/')
def index():
    files = glob("data/listings/*.xlsx")
    files = [(p.stem, p) for p in [Path(f) for f in files]]
    return render_template('index.html', files=files)
