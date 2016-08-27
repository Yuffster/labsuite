from labsuite.labware.grid import GridContainer, GridItem, normalize_position
from labsuite.util import exceptions as x

class TiprackSlot(GridItem):

    _used = False
    _tag = None

    def set_used(self, used=True):
        if self._used and used and self._tag is None:
            raise x.TipMissing(
                "Tip at {} has already been used.".format(self.human_address)
            )
        self._used = True

    def set_tag(self, tag):
        self._tag = tag

    @property
    def used(self):
        return self._used

    @property
    def tag(self):
        return self._tag


class Tiprack(GridContainer):

    size = None

    rows = 12
    cols = 8

    child_class = TiprackSlot

    """
    Taken from microplate specs.
    """
    spacing = 9
    a1_x = 14.38
    a1_y = 11.24

    def tip(self, position):
        return self.get_child(position)

    def set_tips_used(self, number):
        """
        Sets the number of used tips in the tiprack. Must be in sequence.
        """
        for n in range(number):
            tip = self.get_child(self._position_in_sequence(n))
            if tip.used is False:
                tip.set_used()

    @property
    def tips_used(self):
        """
        Returns the number of tips used so far in this tiprack.
        """
        used = 0
        for _, c in self._children.items():
            if c.used:
                used += 1
        return used

    @property
    def has_tips(self):
        # Tips can't be used if they've never been initialized.
        if len(self._children) < self.rows * self.cols:
            return True
        return self.get_clean_tip() is not None

    def get_clean_tip(self, tag=None):
        for n in range(self.rows * self.cols):
            tip = self.tip(self._position_in_sequence(n))
            if tag and tip.tag == tag:  # Previously tagged tip.
                return tip
            if tip.used is False:  # Clean tip!
                if tag:  # Tag it for later use.
                    tip.set_tag(tag)
                elif tip.tag is not None:  # This one's allocated.
                    continue
                return tip

    def get_next_tip(self, tag=None):
        """
        Returns the next clean tip in the rack and marks it as used.

        This might be deprecated at some point.
        """
        tip = self.get_clean_tip(tag)
        tip.set_used()
        return tip

    def tip_offset(self, offset=0):
        """
        Returns the x, y, z offset for a tip position.
        """
        return self.coordinates(self._position_in_sequence(offset))


class Tiprack_P10(Tiprack):
    size = 'P10'


class Tiprack_P20(Tiprack):
    size = 'P20'


class Tiprack_P200(Tiprack):
    size = 'P200'


class Tiprack_P1000(Tiprack):
    size = 'P1000'
