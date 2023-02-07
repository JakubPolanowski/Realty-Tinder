import json
from pathlib import Path


def get_superuser() -> str:
    if (super_path := Path('data', 'superuser.json')).exists():
        with open(super_path, 'r') as f:
            super_json = json.load(f)
        superuser = super_json.get('user')
    else:
        superuser = None

    return superuser
