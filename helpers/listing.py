from typing import Dict, Any


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
