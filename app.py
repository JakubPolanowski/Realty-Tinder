from flask import Flask, render_template, session, request, redirect, url_for, send_file
from flask_session import Session
from glob import glob
from pathlib import Path
import uuid
import pandas as pd
import json
import helpers
from helpers.admin import get_superuser
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
    return dict(user=session.get('user'), superuser=(session.get('user') == get_superuser()))


@app.route('/')
def index():

    if not Path('data', 'superuser.json').exists():
        return redirect(url_for('first_time_config'))

    return redirect(url_for('spotlight'))

    files = glob("data/listings/*.xlsx")
    files = [(p.stem.replace('_', ' '), p.stem)
             for p in [Path(f) for f in files]]
    return render_template('explore.html', files=files)


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
            if (super_path := Path('data', 'superuser.json')).exists():
                with open(super_path, 'r') as f:
                    super_config = json.load(f)
            else:
                super_config = {'user': None, 'password': None}

            if super_config.get('user') == form['user']:
                if 'pwd' in form:
                    if super_config.get("password") == form['pwd']:
                        session['user'] = form['user']
                        if 'feedback' in session:
                            session.pop('feedback')
                        if 'current_page' in form:
                            return redirect(form['current_page'])
                        else:
                            return redirect('/')
                    else:
                        return render_template('error.html', error=400), 400

                else:
                    return redirect(url_for('login', ask_pass=True))
            else:
                session['user'] = form['user']
                if 'feedback' in session:
                    session.pop('feedback')
                if 'current_page' in form:
                    return redirect(form['current_page'])
                else:
                    return redirect('/')

    else:
        return render_template('login.html')


@app.route('/explore')
def explore():

    files = glob("data/listings/*.xlsx")
    files = [(p.stem.replace('_', ' '), p.stem)
             for p in [Path(f) for f in files]]
    return render_template('explore.html', files=files)


@app.route('/spotlight')
def spotlight():

    if not (spotlight_path := Path('data', 'spotlight')).exists():
        return render_template('spotlight.html')

    with open(spotlight_path, 'r') as f:
        spotlight_name = f.read()

    try:
        df = pd.read_excel(Path('data', 'listings', f'{spotlight_name}.xlsx'))
        df['list date'] = df['list date'].dt.strftime('%m/%d/%Y')
        df['price'] = df['price']/1000
        df['acres'] = df['lot sqft'].apply(
            lambda x: '' if pd.isna(x) else f'{x/43560:,.2f}')
        df['interior sqft'] = df['interior sqft'].apply(
            lambda x: '' if pd.isna(x) else f'{x:.0f}'
        )
        df.fillna('', inplace=True)
    except:
        return render_template('error.html', error=404, subtitle='The listings file does not exist'), 404

    spotlight_data = df.drop(columns=['photos']).to_dict(orient='records')
    return render_template('spotlight.html', spotlight_file=spotlight_name, spotlight_data=spotlight_data, spotlight_name=spotlight_name.replace('_', ' '))


@app.route('/ratings')
def ratings():

    ratings = {}
    total = -1  # should be obvious if wrong

    ratings_path = Path('data', 'ratings')

    # yes this would scale TERRIBLY, but this is supposed to be a nano scale web app - not like the security or user management is sufficient for large scale either
    if ratings_path.is_dir():
        for usr_ratings in ratings_path.iterdir():

            ratings[usr_ratings.name] = {}
            for rating_file in usr_ratings.iterdir():
                with open(rating_file, 'r') as f:
                    ratings[usr_ratings.name][rating_file.stem] = json.load(
                        f)

    stats = {}
    for usr, usr_ratings in ratings.items():
        stats[usr] = {}
        for file, file_ratings in usr_ratings.items():
            total = ratings[usr][file].pop('total')
            stats[usr][file] = {'Hate': 0, 'Ok': 0,
                                'Love': 0, 'Total': len(file_ratings),
                                'Listings': total}

            for _, rating in file_ratings.items():
                # better error handling if unexpected value could be used
                # but at that point should switch to using a database
                # but that is overkill for current scope
                stats[usr][file][rating] += 1

    return render_template('ratings.html', ratings=ratings, stats=stats)


@app.route('/ratings/download')
def download_ratings():

    if request.args.get('listing') is None or not (listing_path := Path('data', 'listings', f'{request.args.get("listing")}.xlsx')).exists():
        return render_template('error.html', error=400, subtitle="Invalid listing file name"), 400

    df = pd.read_excel(listing_path)
    # df.drop(columns=['photos'], inplace=True)

    if request.args.get('usr') is not None:
        if not (ratings_path := Path('data', 'ratings', request.args.get('usr'), f'{request.args.get("listing")}.json')).exists():
            return render_template('error.html', error=400, subtitle="Invalid user"), 400
        else:

            with open(ratings_path, 'r') as f:
                ratings = json.load(f)

            ratings.pop('total')
            ratings = {int(k): v for k, v in ratings.items()}

            df['Rating'] = df.index.map(ratings)

    temp_save_path = Path('temp', 'ratings_download.xlsx')
    temp_save_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(temp_save_path)

    return send_file(temp_save_path)


@app.route('/view/<string:listings_file>', defaults={'index': 0}, methods=["GET", "POST"])
@app.route('/view/<string:listings_file>/<int:index>', methods=["GET", "POST"])
def listing_view(listings_file: str, index: int):

    if request.method == "POST":
        form = request.form

        if 'page' in form:
            return redirect(
                url_for('listing_view', listings_file=listings_file,
                        index=int(form['page'])-1, **request.args)
            )

        else:
            return render_template('error.html', error=400, subtitle="Invalid form POST"), 400

    else:

        if not (listing_path := Path(f"data/listings/{listings_file}.xlsx")).exists():
            return render_template('error.html', error=404, subtitle='The listings file does not exist'), 404

        if session.get('listings_file') != listings_file:
            df = pd.read_excel(listing_path)
            df['list date'] = df['list date'].dt.strftime('%m/%d/%Y')

            df['photos'] = df['photos'].apply(json.loads)

            session['listings_file'] = listings_file
            session['listings'] = df.to_json(orient='records')

        dataset = json.loads(session['listings'])
        if index >= len(dataset):
            return render_template('error.html', error=404, subtitle=f'Out of bounds! There are only {len(dataset)} listing(s), {index+1} is invalid.'), 404

        listing = dataset[index]

        # special values
        listing = helpers.listing.prepare_special_values(listing)

        # check if user feedback specified
        if (feedback_of_user := request.args.get('usr_feedback')) is not None:
            if (user_feedback_path := Path('data', 'ratings', feedback_of_user, f'{listings_file}.json')).exists():
                with open(user_feedback_path, 'r') as f:
                    user_feedback = json.load(f)

                user_feedback.pop('total')

                rated = [int(k) for k in user_feedback.keys()]
                rated.sort()
                rating = user_feedback.get(str(index))

                # render
                return render_template('listings_view.html', listings_file=listings_file, index=index, total=len(dataset), rated=rated, rating=rating, listing=listing, images=listing['photos'])

        # render
        return render_template('listings_view.html', listings_file=listings_file, index=index, total=len(dataset), listing=listing, images=listing['photos'])


@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if request.method == "POST":

        if (uploaded_file := request.files.get('listing_upload')) is not None and uploaded_file.filename != '' and 'upload' in request.form:
            print(uploaded_file.filename)
            if uploaded_file.filename[-5:] == ".xlsx":

                # should build in addition checks to chekc if file is correct

                upload_save_path = Path(
                    'data', 'listings', uploaded_file.filename)

                if upload_save_path.exists():
                    return render_template(
                        'error.html', subtitle="File already exists", error=400), 400

                upload_save_path.parent.mkdir(parents=True, exist_ok=True)

                uploaded_file.save(upload_save_path)

                return redirect(url_for('admin'))

            else:
                return render_template(
                    'error.html', subtitle="Invalid file", error=400), 400

        elif (file := request.form.get('file')) is not None:

            if 'spotlight' in request.form:
                splotlight_path = Path('data', 'spotlight')
                splotlight_path.parent.mkdir(parents=True, exist_ok=True)

                with open(splotlight_path, 'w') as f:
                    f.write(file)

                return redirect(url_for('admin'))

            elif 'delete' in request.form:
                delete_path = Path('data', 'listings', f'{file}.xlsx')
                delete_path.unlink(missing_ok=True)
                return redirect(url_for('admin'))

            else:
                return render_template(
                    'error.html', subtitle="Invalid values", error=400), 400

        else:
            return render_template(
                'error.html', subtitle="Invalid values", error=400), 400

    else:

        if session.get('user') != get_superuser():
            return render_template('error.html', error=404), 404

        files = glob("data/listings/*.xlsx")
        files = [(p.stem.replace('_', ' '), p.stem)
                 for p in [Path(f) for f in files]]

        # TODO upload listing files
        return render_template('admin.html', files=files)


@app.route('/first-time', methods=['GET', 'POST'])
def first_time_config():

    # if super user is already setup, give error
    if (super_path := Path('data', 'superuser.json')).exists():
        return render_template('error.html', error=500), 500

    if request.method == "POST":

        if (user := request.form.get('user')) is None or (pwd := request.form.get('pwd')) is None:
            return render_template('error.html', subtitle='Invalid user or password', error=400), 400

        super_path.parent.mkdir(parents=True, exist_ok=True)
        with open(super_path, 'w') as f:
            json.dump(
                {'user': user, 'password': pwd}, f
            )

        session['user'] = request.form['user']

        return redirect(url_for('index'))
    else:
        return render_template('first_time_setup.html')


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

        if 'feedback' in form:
            if 'feedback' not in session:
                session['feedback'] = {}
            if form['filename'] not in session['feedback']:
                session['feedback'][form['filename']] = {}

            feedback = session['feedback'][form['filename']]
            feedback[int(form['index'])] = form['feedback']
            feedback['total'] = form['total']

            total = int(form['total'])

            next_index = int(form['index'])+1
            next_index = total - \
                1 if next_index >= total else next_index

            return redirect(
                url_for(
                    'listings', listings_file=form['filename'], index=next_index)
            )

        if 'clear' in form and form.get('clear') == 'clear-feedback':
            if 'feedback' not in session:
                session['feedback'] = {}

            session['feedback'][form['filename']] = {}

            return redirect(
                url_for(
                    'listings', listings_file=form['filename'], index=int(form['index']))
            )

        if 'save' in form:

            if not isinstance(session.get('user'), str):
                return render_template('error.html', error=400, subtitle="Invalid form POST, invalid user/user not logged in"), 400

            save_path = Path('data', 'ratings',
                             session['user'], f"{form['filename']}.json")
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'w') as f:
                json.dump(session['feedback'][form['filename']], f)

            return redirect(
                url_for(
                    'listings', listings_file=form['filename'], index=int(form['index']), just_saved=True)
            )

        else:
            return render_template('error.html', error=400, subtitle="Invalid form POST"), 400

    else:

        if not (listing_path := Path(f"data/listings/{listings_file}.xlsx")).exists():
            return render_template('error.html', error=404, subtitle='The listings file does not exist'), 404

        if session.get('listings_file') != listings_file:
            df = pd.read_excel(listing_path)
            df['list date'] = df['list date'].dt.strftime('%m/%d/%Y')

            df['photos'] = df['photos'].apply(json.loads)

            session['listings_file'] = listings_file
            session['listings'] = df.to_json(orient='records')

        dataset = json.loads(session['listings'])
        if index >= len(dataset):
            return render_template('error.html', error=404, subtitle=f'Out of bounds! There are only {len(dataset)} listing(s), {index+1} is invalid.'), 404

        listing = dataset[index]

        # special values
        listing = helpers.listing.prepare_special_values(listing)

        # if load feedback arg passed, load feedback to session
        if request.args.get('load_feedback'):
            loaded_feedback = helpers.listing.load_saved_ratings(
                session.get('user'), listings_file)

            if not 'feedback' in session:
                session['feedback'] = {}
            if not listings_file in session['feedback']:
                session['feedback'] = {}

            session['feedback'][listings_file] = loaded_feedback

        # added feedback to listing if exists
        listing['feedback'] = session.get('feedback', {})\
            .get(listings_file, {})\
            .get(index)

        # not yet rated
        not_rated = set(range(len(dataset))) - \
            set(session.get('feedback', {}).get(listings_file, {}).keys())

        # images images are now pre extracted
        # images = helpers.listing.get_images_from_realtor(listing['url'])

        # render
        return render_template('listings.html', listings_file=listings_file, index=index, total=len(dataset), not_rated=not_rated, listing=listing, images=listing['photos'])
