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
        tool = self.get_pipette(name=tool, volume=volume)
        self.pickup_tip(tool)
        self.move_volume(tool, start, end, volume)
        self.dispose_tip(tool)

    def transfer_group(self, transfers=None, tool=None, volume=None, **kwargs):
        tool = self.get_pipette(name=tool, volume=volume)
        self.pickup_tip(tool)
        for t in transfers:
            self.move_volume(tool, t['start'], t['end'], t['volume'])
        self.dispose_tip(tool)

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
        tool = self.get_pipette(name=tool, volume=volume)
        self.pickup_tip(tool)
        for i in range(reps):
            self.move_volume(tool, start, start, volume)
        self.dispose_tip(tool)

    def move_volume(self, pipette, start, end, volume):
        self.move_to_well(start)
        pipette.plunge(volume)
        self.move_into_well(start)
        pipette.reset()
        self.move_to_well(end)
        self.move_into_well(end)
        pipette.blowout()
        self.move_up()
        pipette.reset()

    def pickup_tip(self, pipette):
        coords = self._context.get_next_tip_coordinates(pipette)
        self.move_motors(x=coords['x'], y=coords['y'])
        self.move_motors(z=coords['top'])

    def dispose_tip(self, pipette):
        coords = self._context.get_trash_coordinates(pipette.axis)
        self.move_motors(x=coords['x'], y=coords['y'])
        self.move_motors(z=coords['top'])
        pipette.droptip()
        pipette.reset()

    def move_to_well(self, well):
        self.move_motors(z=0)  # Move up so we don't hit things.
        coords = self._context.get_coordinates(well)
        self.move_motors(x=coords['x'], y=coords['y'])
        self.move_motors(z=coords['top'])

    def move_into_well(self, well):
        coords = self._context.get_coordinates(well)
        self.move_motors(x=coords['x'], y=coords['y'])
        self.move_motors(z=coords['bottom'])

    def move_up(self):
        self.move_motors(z=0)

    def depress_plunger(self, pipette, volume):
        pipette.plunge(volume)

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

        def reset(self):
            debug(
                "PipetteMotor",
                "Resetting {} axis ({}).".format(self.axis, self.name)
            )
            self.move(0)

        def plunge(self, volume):
            debug(
                "PipetteMotor",
                "Plunging {} axis ({}) to volume of {}µl."
                .format(self.axis, self.name, volume)
            )
            depth = self.pipette.plunge_depth(volume)
            self.move(depth)

        def blowout(self):
            debug(
                "PipetteMotor",
                "Blowout on {} axis ({}).".format(self.axis, self.name)
            )
            self.move(self.pipette.blowout)

        def droptip(self):
            debug(
                "PipetteMotor",
                "Droptip on {} axis ({}).".format(self.axis, self.name)
            )
            self.move(self.pipette.droptip)

        def move(self, position):
            axis = self.axis
            self.motor.move_motors(**{axis: position})

        def __getattr__(self, name):
            """ Fallback to Pipette for everything else. """
            return getattr(self.pipette, name)
