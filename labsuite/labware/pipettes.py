import sys
from labsuite.util import exceptions as x


def load_instrument(name):
    cname = name.replace('.', '_')  # conform to dot notation standard
    p = getattr(
        sys.modules[__name__],
        'Pipette_{}'.format(cname.capitalize())
    )()
    p.set_name(name)
    return p


class Pipette():

    channels = 1
    size = 'P10'
    min_vol = 0
    max_vol = 10

    _name = None  # Labware name used to load this object.

    _context = None

    __calibration = None  # {} Only gets used when no context is available.

    _axis = None

    _points = None  # {} (See init below.)

    _tip_plunge = 6  # Distance from calibrated top of tiprack to pickup tip.

    def __init__(self):
        self.__calibration = {}
        self._points = [
            {'f1': 1, 'f2': 1},
            {'f1': 2000, 'f2': 2000}
        ]

    def calibrate(self, top=None, blowout=None, droptip=None, axis='A'):
        """Set calibration values for the pipette plunger.

        This can be called multiple times as the user sets each value,
        or you can set them all at once.

        Parameters
        ----------

        top : int
           Touching but not engaging the plunger.

        blowout : int
            Plunger has been pushed down enough to expell all liquids.

        droptip : int
            This position that causes the tip to be released from the
            pipette.

        """
        if top is not None:
            self._calibration['top'] = top
        if blowout is not None:
            self._calibration['blowout'] = blowout
        if droptip is not None:
            self._calibration['droptip'] = droptip

    @property
    def _calibration(self):
        if self._context:
            return self._context._calibration
        else:
            return self.__calibration

    def set_context(self, context):
        """
        Sets the operational context (ContextHandler) so that we can access
        operational data, such as which head axis this instrument is attached
        to.
        """
        self._context = context

    def plunge_depth(self, volume):
        """Calculate axis position for a given liquid volume.

        Translates the passed liquid volume to absolute coordinates
        on the axis associated with this pipette.

        Calibration of the top and blowout positions are necessary for
        these calculations to work.
        """
        if self.blowout is None or self.top is None:
            raise x.CalibrationMissing(
                "Pipette {} not calibrated.".format(self.axis)
            )
        percent = self._volume_percentage(volume)
        travel = self.blowout - self.top
        distance = travel * percent
        return self.top + distance

    def _volume_percentage(self, volume):
        """Returns the plunger percentage for a given volume.

        We use this to calculate what actual position the plunger axis
        needs to be at in order to achieve the correct volume of liquid.
        """
        if volume < 0:
            raise IndexError("Volume must be a positive number.")
        if volume > self.max_vol:
            raise IndexError("{}µl exceeds maximum volume.".format(volume))

        p1 = None
        p2 = None

        # Find the correct point.
        points = sorted(self._points, key=lambda a: a['f1'])
        for i in range(len(points) - 1):
            if volume >= points[i]['f1'] and volume <= points[i + 1]['f1']:
                p1 = points[i]
                p2 = points[i + 1]
                break

        if not (p1 and p2):
            raise IndexError(
                "Point data not found for volume {}.".format(volume)
            )

        # Calculate the volume based on this point (piecewise linear).
        diff = p2['f1'] - p1['f1']
        f1 = (volume - p1['f1']) / diff
        lower = p1['f1'] / p1['f2']
        upper = p2['f1'] / p2['f2']
        scale = ((upper - lower) * f1) + lower

        return volume * scale / self.max_vol

    def supports_volume(self, volume):
        if volume is None:
            # If the user doesn't care about volume, neither do we.
            return True
        return volume <= self.max_vol and volume >= self.min_vol

    def has_volumes(self, minv, maxv):
        return self.supports_volume(minv) and self.supports_volume(maxv)

    def has_volume(self, volume):
        return self.supports_volume(volume)

    @property
    def axis(self):
        if self._context:
            return self._context.get_axis(self)
        return None

    @property
    def top(self):
        return self._calibration['top']

    @property
    def blowout(self):
        return self._calibration['blowout']

    @property
    def droptip(self):
        return self._calibration['droptip']

    @property
    def name(self):
        return self._name or self.size.lower()

    def set_name(self, name):
        self._name = name


class Pipette_8(Pipette):
    channels = 8


class Pipette_12(Pipette):
    channels = 12


class Pipette_P2(Pipette):
    size = 'P2'
    min_vol = 0.0
    max_vol = 2


class Pipette_P2_8(Pipette_P2, Pipette_8):
    pass


class Pipette_P2_12(Pipette_P2, Pipette_12):
    pass


class Pipette_P10(Pipette):
    size = 'P10'
    min_vol = 0.5
    max_vol = 10


class Pipette_P10_8(Pipette_P10, Pipette_8):
    pass


class Pipette_P10_12(Pipette_P10, Pipette_12):
    pass


class Pipette_P20(Pipette):
    size = 'P20'
    min_vol = 2
    max_vol = 20


class Pipette_P20_8(Pipette_P20, Pipette_8):
    pass


class Pipette_P20_12(Pipette_P20, Pipette_12):
    pass


class Pipette_P200(Pipette):
    size = 'P200'
    min_vol = 20
    max_vol = 200


class Pipette_P200_8(Pipette_P200, Pipette_8):
    pass


class Pipette_P200_12(Pipette_P200, Pipette_12):
    pass


class Pipette_P1000(Pipette):
    size = 'P1000'
    min_vol = 200
    max_vol = 1000


class Pipette_P1000_8(Pipette_P1000, Pipette_8):
    pass


class Pipette_P1000_12(Pipette_P1000, Pipette_12):
    pass
