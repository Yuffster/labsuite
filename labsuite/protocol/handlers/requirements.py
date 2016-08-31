from labsuite.protocol.handlers import ProtocolHandler
from labsuite.util import exceptions as x
from copy import deepcopy


class RequirementsHandler(ProtocolHandler):
    """
    Doesn't really do anything, just goes through each of the transfers,
    figures out which tools and containers are going to be involved, and
    determines whether or not they've been calibrated properly.

    In the future this could get smarter and automatically fill in 
    some calibration if enough auxilary data is available.
    """

    _requirements = None  # {}

    def setup(self):
        self._requirements = []

    def transfer(self, start=None, end=None, volume=None, tool=None, **kwargs):
        self._assert_calibration(tool, start, end)
        self._advance_tip(tool)

    def transfer_group(self, transfers=None, tool=None, volume=None, **kwargs):
        for t in transfers:
            self._assert_calibration(tool, t['start'], t['end'])
        self._advance_tip(tool)

    def distribute(self, start=None, transfers=None, tool=None, **kwargs):
        for t in transfers:
            self._assert_calibration(tool, start, t['end'])
            self._advance_tip(tool)

    def consolidate(self, end=None, transfers=None, tool=None, **kwargs):
        for t in transfers:
            self._assert_calibration(tool, start=t['start'], end=end)
            self._advance_tip(tool)

    def mix(self, start=None, reps=None, tool=None, volume=None, **kwargs):
        for i in range(reps):
            self._assert_calibration(tool, start, start)
            self._advance_tip(tool)

    def _assert_calibration(self, tool, start, end):
        tool = self._context.get_instrument(name=tool)
        # Get the tiprack for the tool.
        tiprack = self._context.get_tiprack(tool, has_tips=True)
        for c in [start, end, tiprack.address]:
            self._check_container_calibration(c, tool)
        self._check_instrument_calibration(tool)

    def _advance_tip(self, tool_name):
        """
        Advances the tip inventory for the tool in question. We need this
        because otherwise we'll ignore calibration issues on tipracks beyond
        the first one assuming the tips in the first container are exhausted.
        """
        tool = self._context.get_instrument(name=tool_name)
        try:
            self._context.get_next_tip_coordinates(tool)
        except x.CalibrationMissing:
            pass  # We know it's not calibrated. :D

    def _request_calibration(self, tool=None, position=None):
        if tool is not None and position is None:
            req = {
                'type': 'calibrate_instrument',
                'axis': tool.axis,
                'instrument_name': tool.name
            }
        if tool is not None and position is not None:
            container = self._context._deck.slot(position[0])
            req = {
                'type': 'calibrate_container', 'axis': tool.axis,
                'address': position[0], 'container_name': container.name,
                'instrument_name': tool.name
            }
        self._add_requirement(req)

    def _requirements_contains(self, item):
        for req in self._requirements:
            match = True
            for k in req:
                if k in item and item[k] != req[k]:
                    match = False
                    break
            if match:
                return True
        return False

    def _add_requirement(self, req):
        if not self._requirements_contains(req):
            self._requirements.append(req)

    def _check_instrument_calibration(self, instrument):
        if not instrument.is_calibrated:
            self._request_calibration(tool=instrument)

    def _check_container_calibration(self, position, tool):
        try:
            self._context.get_coordinates(position, axis=tool.axis)
        except (x.CalibrationMissing):
            self._request_calibration(position=position, tool=tool)

    @property
    def requirements(self):
        return deepcopy(self._requirements)
