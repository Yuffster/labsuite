from labsuite.protocol.handlers import ProtocolHandler
from labsuite.labware import deck, pipettes
from labsuite.labware.grid import humanize_position
from labsuite.util import exceptions as ex
from labsuite.util.filters import find_objects


class ContextHandler(ProtocolHandler):

    """
    ContextHandler runs all the stuff on the virtual robot in the background
    and makes relevant data available.
    """

    _deck = None
    _instruments = None  # Axis as keys; Pipette object as vals.

    def setup(self):
        self._deck = deck.Deck()
        self._instruments = {}

    @property
    def _calibration(self):
        """
        We're always reinitializing this object, but calibration needs to
        remain the same.  So we go up a level and grab it from the parent
        Protocol.
        """
        return self._protocol._calibration

    def add_instrument(self, axis, name):
        axis = axis.upper()
        # We only have pipettes now so this is pipette-specific.
        self._instruments[axis] = pipettes.load_instrument(name)
        self._instruments[axis].set_context(self)

    def get_axis(self, instrument):
        for k in self._instruments:
            if instrument is self._instruments[k]:
                return k

    def get_instrument(self, axis=None, name=None, **kwargs):
        if axis is not None:
            axis = self.normalize_axis(axis)
            collection = [self._instruments[axis]]
        else:
            collection = self._instruments
        # Sometimes people just pass this as None, in which case we want to
        # skip it.
        if name is not None:
            kwargs['name'] = name
        return find_objects(collection, limit=1, **kwargs)

    def find_container(self, **filters):
        return self._deck.find_module(**filters)

    def add_container(self, slot, container_name):
        self._deck.add_module(slot, container_name)

    def get_only_instrument(self):
        ks = list(self._instruments)
        if len(ks) is 1:
            return self.get_instrument(axis=ks[0])
        if len(ks) is 0:
            raise ex.InstrumentMissing("No instruments loaded.")
        else:
            return None

    def normalize_axis(self, axis):
        """
        Returns an axis by axis, after normalizing axis input.

        If axis is none, the first instrument axis if only one instrument is
        attached to the protocol.
        """
        if axis is None:
            raise ex.DataMissing("Axis must be specified.")
        axis = axis.upper()
        if axis not in self._instruments:
            raise ex.InstrumentMissing(
                "Can't find instrument for axis {}.".format(axis)
            )
        return axis

    def get_axis_calibration(self, axis):
        """
        Initializes and returns calibration for a particular axis.
        """
        if axis is None:
            instrument = self.get_only_instrument()
            if instrument:
                axis = instrument.axis
        if axis is None:
            raise ex.CalibrationMissing(
                "Calibration axis must be specified when multiple " +
                "instruments are loaded."
            )
        axis = self.normalize_axis(axis)
        if axis not in self._calibration:
            self._calibration[axis] = {}
        return self._calibration[axis]

    def calibrate(self, pos, axis=None, x=None, y=None, z=None, top=None,
                  bottom=None, tool=None):
        if tool:
            axis = tool.axis
        if axis is None:
            instrument = self.get_only_instrument()
            if instrument is None:
                raise ex.DataMissing(
                    "Calibration axis must be specified when multiple " +
                    "instruments are loaded."
                )
            axis = instrument.axis
        cal = self.get_axis_calibration(axis)
        if pos not in cal:
            cal[pos] = {}
        pos_cal = cal[pos]
        # Roll in all the new calibration changes.
        if x is not None:
            pos_cal['x'] = x
        if y is not None:
            pos_cal['y'] = y
        if z is not None:
            pos_cal['z'] = z
        if top is not None:
            pos_cal['top'] = top
        if bottom is not None:
            pos_cal['bottom'] = bottom

    def calibrate_instrument(self, axis, top=None, blowout=None, droptip=None,
                             bottom=None):
        cal = self.get_axis_calibration(axis)
        if '_instrument' not in cal:
            cal['_instrument'] = {}
        a_cal = cal['_instrument']
        # Roll in all the new calibration changes.
        if top is not None:
            a_cal['top'] = top
        if blowout is not None:
            a_cal['blowout'] = blowout
        if droptip is not None:
            a_cal['droptip'] = droptip
        if bottom is not None:
            a_cal['bottom'] = bottom
        self.get_instrument(axis=axis).calibrate(**a_cal)

    def get_coordinates(self, position, axis=None, tool=None):
        """ Returns the calibrated coordinates for a position. """
        if tool is not None:
            axis = tool.axis
        cal = self.get_axis_calibration(axis)
        slot, well = position
        if slot not in cal:
            raise ex.CalibrationMissing(
                "No calibration for {} (axis {}).".
                format(humanize_position(slot), axis)
            )
        defaults = ({'top': 0, 'bottom': 0, 'x': 0, 'y': 0})
        output = {}
        # Calibration for A1 in this container (x, y, top, bottom).
        slot_cal = {}
        slot_cal.update(defaults)
        slot_cal.update(cal.get((slot), {}))
        # Default offset on x, y calculated from container definition.
        ox, oy = self._deck.slot(slot).get_child(well).coordinates()
        # x, y, top bottom
        well_cal = cal.get((slot, well), {})
        output.update(well_cal)
        # Use calculated offsets if no custom well calibration provided.
        if 'x' not in output:
            output['x'] = slot_cal['x'] + ox
        if 'y' not in output:
            output['y'] = slot_cal['y'] + oy
        # Merge slot and well calibration
        if 'top' not in output:
            output['top'] = slot_cal['top']
        if 'bottom' not in output:
            output['bottom'] = slot_cal['bottom']
        return output

    def get_next_tip_coordinates(self, pipette):
        """
        Returns the next tip coordinates and decrements tip inventory.
        """
        name = 'tiprack.{}'.format(pipette.size.lower())
        # We won't necessarily use this rack, but we need its properties.
        xrack = self.find_container(name=name)
        if xrack is None:
            raise ex.ContainerMissing("No tiprack found for {}.".format(name))
        # Multichannel support.
        if pipette.channels == xrack.cols:
            tiprack = self.find_container(name=name, has_row=True)
            if tiprack:
                tip = tiprack.get_next_row()[0]
        elif pipette.channels == xrack.rows:
            tiprack = self.find_container(name=name, has_col=True)
            if tiprack:
                tip = tiprack.get_next_col()[0]
        else:
            tiprack = self.find_container(name=name, has_tips=True)
            if tiprack:
                tip = tiprack.get_next_tip()
        if tiprack is None:
            raise ex.TipMissing(
                "No tiprack found with enough tips for {}-channel {}."
                .format(pipette.channels, pipette.size)
            )
        return self.get_coordinates(tip.address, axis=pipette.axis)

    def get_trash_coordinates(self, tool):
        trash = self.find_container(name='point.trash')
        if trash is None:
            raise ex.ContainerMissing("No disposal point (trash) on deck.")
        return self.get_coordinates(trash.address + [(0, 0)], tool=tool)

    def get_volume(self, well):
        slot, well = self._protocol._normalize_address(well)
        return self._deck.slot(slot).get_child(well).get_volume()

    def transfer(self, start=None, end=None, volume=None, tool=None,
                 **kwargs):
        start_slot, start_well = start
        end_slot, end_well = end
        start_container = self._deck.slot(start_slot)
        end_container = self._deck.slot(end_slot)
        start = None
        end = None
        if tool:  # Account for multichannel.
            inst = self.get_instrument(name=tool)
            if start_container.cols == start_container.rows:
                # Users are gonna love this one.
                raise Exception(
                    "Ambiguous multichannel transfer; plate is square."
                )
            elif inst.channels == start_container.rows:  # Column transfer.
                start = start_container.col(start_well[0])
                end = end_container.col(end_well[0])
            elif inst.channels == start_container.cols:  # Row transfer.
                start = start_container.row(start_well[1])
                end = end_container.row(end_well[1])
        if start is None:
            start = self._deck.slot(start_slot).get_child(start_well)
            end = self._deck.slot(end_slot).get_child(end_well)
        start.transfer(volume, end)

    def transfer_group(self, transfers=None, **kwargs):
        for t in transfers:
            self.transfer(t['start'], t['end'], t['volume'])

    def distribute(self, start, transfers, **kwargs):
        start_slot, start_well = start
        start = self._deck.slot(start_slot).get_child(start_well)
        for c in transfers:
            slot, well = c.get('end')
            end = self._deck.slot(slot).get_child(well)
            start.transfer(c.get('volume'), end)

    def consolidate(self, end, transfers, **kwargs):
        end_slot, end_well = end
        end = self._deck.slot(end_slot).get_child(end_well)
        for c in transfers:
            slot, well = c.get('start')
            start = self._deck.slot(slot).get_child(well)
            start.transfer(c.get('volume'), end)

    def mix(self, start=None, reps=None, tool=None, volume=None, **kwargs):
        slot, well = start
        start = self._deck.slot(slot).get_child(well)
        for i in range(reps):
            start.transfer(volume, start)
