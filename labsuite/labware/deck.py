from labsuite.labware.grid import GridContainer, humanize_position
from labsuite.labware.containers import load_container
from labsuite.util import exceptions as x

class Deck(GridContainer):

    rows = 3
    cols = 5

    def __init__(self, **kwargs):
        super(Deck, self).__init__()
        self.add_modules(**kwargs)

    def add_modules(self, **kwargs):
        for position in kwargs:
            self.add_module(position, kwargs[position])

    def add_module(self, position, mod):
        pos = self._normalize_position(position)
        if isinstance(mod, str):
            mod = load_container(mod)()
        if pos not in self._children:
            self._children[pos] = mod
            mod.position = position
        else:
            raise x.ContainerConflict(
                "Module already allocated to slot: {}."
                .format(humanize_position(pos))
            )

    def find_module(self, **filters):
        for pos, mod in sorted(self._children.items()):
            match = True
            for k, v in filters.items():
                if getattr(mod, k, None) != filters[k]:
                    match = False
                    break
            if match:
                return mod

    def slot(self, position):
        pos = self._normalize_position(position)
        if pos not in self._children:
            raise x.ContainerMissing(
                "No deck module at slot {}."
                .format(humanize_position(pos))
            )
        return self._children[pos]
