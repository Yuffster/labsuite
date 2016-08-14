import json
import hashlib


def hash_data(data):
    """ Converts a complex data structure to a SHA256 hash. """
    data = json.dumps(to_s(data), sort_keys=True).encode('utf-8')
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def to_s(data):
    """
    Recursively converts all keys and values in a data structure to strings.
    """
    if type(data) == list:
        return list(map(to_s, data))
    elif type(data) == dict:
        o = {}
        for k, d in data.items():
            o[to_s(k)] = to_s(d)
        return o
    else:
        return str(data)
