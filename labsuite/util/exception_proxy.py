import copy

class ExceptionProxy():

    """
    This is a utility class to act as a proxy to real objects while
    catching and storing exceptions within a selection of allowable types.

    The ExceptionLogger instance can then be reapplied to full instances
    of the object, or used as normal if no Exceptions have been logged.

    You'll want to extend this class to block any calls to methods with
    side effects on the normal class. For example, Protocol.run should not
    run on an invalid protocol.
    """

    _original = None  # Act as a proxy to this object.
    _problems = None  # [] Holds caught Exceptions.
    _calls = None  # [] Remember every call made to this proxy.
    _allowed_exceptions = None  # tuple of Exception classes to log.

    def __init__(self, original, *allowed):
        """
        Wrap the original object so we can log calls and exceptions.

        Exception classes passed after the original object will be logged.
        All other exceptions will be thrown as normal.
        """
        self._original = original
        self._original._partial_proxy = self
        self._problems = []
        self._calls = []
        for e in allowed:
            if not issubclass(e, Exception):
                raise TypeError(
                    "Exceptions must inherit from BaseException."
                )
        self._allowed_exceptions = tuple(allowed)

    def __getattr__(self, name):
        """
        Act as a proxy to the wrapped object and store all the calls for
        later application on the desired instance.

        If Exceptions occur, log them so they can be fixed.
        """
        prop = getattr(self._original, name)
        if getattr(prop, '__call__', None) is not None:
            def catch(*args, **kwargs):
                try:
                    self._calls.append((name, args, kwargs))
                    prop(*args, **kwargs)
                except self._allowed_exceptions as e:
                    self._problems.append(str(e))
            return catch
        return prop

    def apply(self, b):
        """
        Combines other objects with this one by concatenating the
        list of stored calls.

        Raises an exception if the user tries to add an actual instance to
        this proxy, since actual instances don't log their calls and we want
        to preserve the call order.
        """
        if isinstance(b, type(self)):
            # Combine the stored calls of other proxy objects.
            for method, args, kwargs in b._calls:
                getattr(self, method)(*args, **kwargs)
            return self
        else:
            # We can't concat a normal object because normal objects don't
            # log their calls.
            raise TypeError(
                "Can't add {} to {}; try reversing the operand order."
                .format(type(self), 'partial')
            )

    def __add__(self, b):
        """
        Concat operator; creates a copy of this instance and returns
        new combined result.
        """
        # Copy self so we don't mess with it directly.
        a = self.__class__(self._original, *self._allowed_exceptions)
        a.apply(self)
        a.apply(b)
        return a

    def reapply(self, thing):
        """
        Take all the stored calls and call them on an actual instance.

        Or get a bunch of method missing errors.

        We don't check for instance compatibility by type because we might
        want to combine disparate objects with the same interface.
        """
        for method, args, kwargs in self._calls:
            getattr(thing, method)(*args, **kwargs)

    @property
    def problems(self):
        return copy.deepcopy(self._problems)

    @property
    def is_valid(self):
        return len(self._problems) == 0
