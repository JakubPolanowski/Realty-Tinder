from typing import Dict, List, Any
from bs4 import BeautifulSoup
import requests
import json
import re


def prepare_special_values(listing: Dict[str, Any]):
    try:
        listing['pretty price'] = f"{listing['price']:,}"
    except TypeError:
        listing['pretty price'] = listing['price']

    try:
        listing['pretty built'] = f"{listing['year built']:.0f}"
    except TypeError:
        listing['pretty built'] = listing['year built']

    try:
        listing['pretty hoa'] = f"{listing['hoa fee']:,.0f}"
    except TypeError:
        listing['pretty hoa'] = listing['hoa fee']

    try:
        listing['pretty sqft'] = f"{listing['interior sqft']:,.0f}"
    except TypeError:
        listing['pretty sqft'] = listing['interior sqft']

    try:
        listing['price per sqft'] = f"{listing['price']/listing['interior sqft']:,.2f}"
    except TypeError:
        listing['price per sqft'] = ""

    try:
        listing['acres'] = listing['lot sqft']/43560
        listing['pretty acres'] = f"{listing['acres']:,.2f}"
    except TypeError:
        listing['acres'] = 0
        listing['pretty acres'] = ""

    try:
        listing['pretty minutes'] = f"{listing['Minutes to Work']:,.0f}"
    except:
        listing['pretty minutes'] = listing['Minutes to Work']

    if listing['Minutes to Work'] <= 15:
        listing['minutes class'] = "has-text-success"
    elif listing['Minutes to Work'] <= 25:
        listing['minutes class'] = 'has-text-warning'
    else:
        listing['minutes class'] = 'has-text-danger'

    if listing['flags'] is None:
        listing['flags'] = ""

    return listing


def get_images_from_realtor(listing_url: str) -> List[str]:

    HEADER = {
        "authority": "www.realtor.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    }

    # TODO add some error handling if get response other than 200
    response = requests.get(listing_url, headers=HEADER)

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        ndata = soup.find("script", id="__NEXT_DATA__").text
        ndata = json.loads(ndata)

        photos = ndata['props']['pageProps']['initialState']['propertyDetails']['home_photos']['collection']
        photos = [re.sub(r's\.jpg$', 'od-w1024_h768_x2_var-A2.webp',
                         photo['href']) for photo in photos if isinstance(photo['href'], str)]

        return photos

    except:
        return ["https://bulma.io/images/placeholders/1280x960.png"]
