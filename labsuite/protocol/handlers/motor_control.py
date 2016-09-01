from labsuite.util.log import debug
from labsuite.protocol.handlers import ProtocolHandler
import labsuite.drivers.motor as motor_drivers
from labsuite.util import exceptions as x


class MotorControlHandler(ProtocolHandler):

    _driver = None
    _pipette_motors = None  # {axis: PipetteMotor}

    def setup(self):
        self._pipette_motors = {}

    def set_driver(self, driver):
        self._driver = driver

    def connect(self, port):
        """
        Connects the MotorControlHandler to a serial port.

        If a device connection is set, then any dummy or alternate motor
        drivers are replaced with the serial driver.
        """
        self.set_driver(motor_drivers.OpenTrons())
        self._driver.connect(device=port)

    def simulate(self):
        self._driver = motor_drivers.MoveLogger()
        return self._driver

    def disconnect(self):
        self._driver.disconnect()

    def transfer(self, start=None, end=None, volume=None, tool=None, **kwargs):
        tool = self.get_pipette(name=tool, has_volume=volume)
        tool.pickup_tip()
        self.move_volume(tool, start, end, volume)
        tool.dispose_tip()

    def transfer_group(self, transfers=None, tool=None, volume=None, **kwargs):
        tool = self.get_pipette(name=tool, has_volume=volume)
        tool.pickup_tip()
        for t in transfers:
            self.move_volume(tool, t['start'], t['end'], t['volume'])
        tool.dispose_tip()

    def distribute(self, start=None, transfers=None, tool=None, **kwargs):
        for t in transfers:
            self.transfer(
                start=start,
                end=t.pop('end'),
                tool=tool,
                volume=t.pop('volume'),
                **t
            )

    def consolidate(self, end=None, transfers=None, **kwargs):
        for t in transfers:
            self.transfer(start=t.pop('start'), end=end, **t)

    def mix(self, start=None, reps=None, tool=None, volume=None, **kwargs):
        tool = self.get_pipette(name=tool, has_volume=volume)
        tool.pickup_tip()
        for i in range(reps):
            self.move_volume(tool, start, start, volume)
        tool.dispose_tip()

    def move_volume(self, tool, start, end, volume):
        tool.move_to_well(start)
        tool.plunge(volume)
        tool.move_into_well(start)
        tool.reset()
        tool.move_to_well(end)
        tool.move_into_well(end)
        tool.blowout()
        tool.move_up()
        tool.reset()

    def get_pipette(self, **kwargs):
        """
        Returns a closure object that allows for the plunge, release, and
        blowout of a certain pipette and volume.
        """
        pipette = self._context.get_instrument(**kwargs)
        if pipette is None:
            raise x.InstrumentMissing(
                "Can't find instrument for {}".format(kwargs)
            )
        axis = pipette.axis
        if axis not in self._pipette_motors:
            self._pipette_motors[axis] = PipetteMotor(pipette, self)
        return self._pipette_motors[axis]

    def move_motors(self, **kwargs):
        debug("MotorHandler", "Moving: {}".format(kwargs))
        self._driver.move(**kwargs)


class PipetteMotor():

    def __init__(self, pipette, motor):
        self.pipette = pipette
        self.motor = motor
        self.context = self.motor._context

    def reset(self):
        debug(
            "PipetteMotor",
            "Resetting {} axis ({}).".format(self.axis, self.name)
        )
        self.move_axis(0)

    def plunge(self, volume):
        debug(
            "PipetteMotor",
            "Plunging {} axis ({}) to volume of {}µl."
            .format(self.axis, self.name, volume)
        )
        depth = self.pipette.plunge_depth(volume)
        self.move_axis(depth)

    def blowout(self):
        debug(
            "PipetteMotor",
            "Blowout on {} axis ({}).".format(self.axis, self.name)
        )
        self.move_axis(self.pipette.blowout_depth)

    def droptip(self):
        debug(
            "PipetteMotor",
            "Droptip on {} axis ({}).".format(self.axis, self.name)
        )
        self.move_axis(self.droptip_depth)

    def pickup_tip(self):
        coords = self.context.get_next_tip_coordinates(self)
        self.move(x=coords['x'], y=coords['y'])
        self.move(z=coords['top'])

    def dispose_tip(self):
        coords = self.context.get_trash_coordinates(self)
        self.move(x=coords['x'], y=coords['y'])
        self.move(z=coords['top'])
        self.droptip()
        self.reset()

    def move_to_well(self, well):
        self.move(z=0)  # Move up so we don't hit things.
        coords = self.context.get_coordinates(well, tool=self)
        self.move(x=coords['x'], y=coords['y'])
        self.move(z=coords['top'])

    def move_into_well(self, well):
        coords = self.context.get_coordinates(well, tool=self)
        self.move(x=coords['x'], y=coords['y'])
        self.move(z=coords['bottom'])

    def move_up(self):
        self.move(z=0)

    def move(self, **coords):
        self.motor.move_motors(**coords)

    def move_axis(self, depth):
        axis = self.axis
        self.move(**{axis: depth})

    def __getattr__(self, name):
        """ Fallback to Pipette for everything else. """
        return getattr(self.pipette, name)
