def find_objects(collection, limit=None, **kwargs):
    """
    Takes a list of objects and goes through the dict of criteria to
    determine whther or not the object meets the criteria.
    """
    results = []
    if isinstance(collection, dict):
        # Sort collection keys.
        collection = [collection[k] for k in sorted(collection)]
    for thing in collection:
        match = True
        for k, v in kwargs.items():
            # If the property is a method, take the tuple arguments
            # and pass that on, then except a boolean value of True.
            # This lets us do things like supports_volume=(5, 10).
            prop = getattr(thing, k, None)
            if prop is None:
                match = False
                break
            if getattr(prop, '__call__', None) is not None:
                if not isinstance(v, tuple):
                    v = [v]
                if prop(*v) is not True:
                    match = False
            elif prop != v:
                match = False
                break
        if match is True:
            results.append(thing)
            if limit == len(results):
                if limit == 1:
                    return results[0]  # For convenience.
                return results
    return results