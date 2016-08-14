from labsuite.labware import containers, deck, pipettes
from labsuite.labware.grid import normalize_position, humanize_position
import labsuite.drivers.motor as motor_drivers
from labsuite.util.log import debug
from labsuite.protocol.handlers import ContextHandler, MotorControlHandler
from labsuite.util import hashing
from labsuite.util import exceptions as x

import time
import copy
import logging


class Protocol():

    # Operational data.
    _ingredients = None  # { 'name': "A1:A1" }
    _instruments = None  # { motor_axis: instrument }
    _container_labels = None  # Aliases. { 'foo': (0,0), 'bar': (0,1) }
    _label_case = None  # Capitalized labels.
    _containers = None  # { slot: container_name }
    _commands = None  # []

    # Metadata
    _name = None
    _description = None
    _created = None
    _updated = None
    _author = None
    _version = (0, 0, 0)
    _version_hash = None  # Only saved when the version is updated.

    # Context and Motor are important handlers, so we provide
    # a way to get at them.
    _handlers = None  # List of attached handlers for run_next.
    _context_handler = None  # Operational context (virtual robot).
    _motor_handler = None

    def __init__(self):
        self._ingredients = {}
        self._container_labels = {}
        self._label_case = {}
        self._instruments = {}
        self._containers = {}
        self._commands = []
        self._handlers = []
        self._initialize_context()

    def set_info(self, name=None, description=None, created=None,
                 updated=None, author=None, version=None, **kwargs):
        """
        Sets the information metatadata of the protocol.
        """
        if name is not None:
            self._name = name
        if description is not None:
            self._description = description
        if author is not None:
            self._author = author
        if created is not None:
            self._created = created
        if updated is not None:
            self._updated = updated
        if version is not None:
            self._version = tuple(map(int, version.split('.')))
            self._version_hash = self.hash

    @property
    def info(self):
        """
        Returns information metatadata of the protocol (author, name,
        description, etc).
        """
        o = {}
        if self._name is not None:
            o['name'] = self._name
        if self._author is not None:
            o['author'] = self._author
        if self._description is not None:
            o['description'] = self._description
        o['created'] = self._created or str(time.strftime("%c"))
        o['updated'] = self._updated or str(time.strftime("%c"))
        o['version'] = self.version
        o['version_hash'] = self.hash
        return o

    @property
    def commands(self):
        return copy.deepcopy(self._commands)

    @property
    def instruments(self):
        return copy.deepcopy(self._instruments)

    @property
    def version(self):
        return ".".join(map(str, self._version))

    def bump_version(self, impact="minor"):
        vhash = self.hash
        if vhash == self._version_hash:
            # Don't bump the version if it's the same.
            return self.version
        major, feature, minor = self._version
        if impact == "minor":
            minor += 1
        elif impact == "feature":
            minor = 0
            feature += 1
        elif impact == "major":
            minor = 0
            feature = 0
            major += 1
        else:
            raise ValueError(
                "Impact must be one of: minor, feature, major."
            )
        self._version = (major, feature, minor)
        self._version_hash = vhash
        return self.version

    @property
    def hash(self):
        return hashing.hash_data([
            self._ingredients,
            self._instruments,
            self._container_labels,
            self._label_case,
            self._containers,
            self._commands
        ])

    def __eq__(self, protocol):
        return self.hash == protocol.hash

    def add_container(self, slot, name, label=None):
        slot = normalize_position(slot)
        if (label):
            lowlabel = label.lower()
            if lowlabel in self._container_labels:
                raise x.ContainerConflict(
                    "Label already in use: {}".format(label)
                )
            # Maintain label capitalization, but only one form.
            if lowlabel not in self._label_case:
                self._label_case[lowlabel] = label
            self._container_labels[lowlabel] = slot
        self._context_handler.add_container(slot, name)
        self._containers[slot] = name

    def add_instrument(self, axis, name):
        self._instruments[axis] = name
        self._context_handler.add_instrument(axis, name)

    def calibrate(self, position, **kwargs):
        if ':' in position:
            pos = self._normalize_address(position)
        else:
            pos = normalize_position(position)
        self._context_handler.calibrate(pos, **kwargs)

    def calibrate_instrument(self, axis, top=None, blowout=None, droptip=None,
                             bottom=None):
        self._context_handler.calibrate_instrument(
            axis, top=top, blowout=blowout, droptip=droptip
        )

    def add_command(self, command, **kwargs):
        self._run_in_context_handler(command, **kwargs)
        d = {'command': command}
        d.update(**kwargs)
        self._commands.append(d)

    def transfer(self, start, end, ul=None, ml=None,
                 blowout=True, touchtip=True, tool=None):
        if ul:
            volume = ul
        else:
            volume = ml * 1000
        if tool is None:
            inst = self._context_handler.get_instrument(volume=volume)
            tool = inst.name

        self.add_command(
            'transfer',
            volume=volume,
            tool=tool,
            start=self._normalize_address(start),
            end=self._normalize_address(end),
            blowout=blowout,
            touchtip=touchtip
        )

    def transfer_group(self, *wells, ul=None, ml=None, **defaults):
        if ul:
            volume = ul
        elif ml:
            volume = ul * 1000
        else:
            volume = None
        defaults.update({
            'touchtip': True,
            'blowout': True,
            'volume': volume
        })
        transfers = []
        for item in wells:
            options = defaults.copy()
            if len(item) is 3:
                start, end, opts = item
                options.update(opts)
            else:
                start, end = item
            vol = options.get('ul') or options.get('ml', 0) * 1000
            vol = vol or volume
            transfers.append({
                'volume': vol,
                'start': self._normalize_address(start),
                'end': self._normalize_address(end),
                'blowout': options['blowout'],
                'touchtip': options['touchtip']
            })
        self.add_command(
            'transfer_group',
            tool=options['tool'],
            transfers=transfers
        )

    def distribute(self, start, *wells, blowout=True):
        transfers = []
        for item in wells:
            end, volume = item
            transfers.append({
                'volume': volume,
                'end': self._normalize_address(end)
            })
        self.add_command(
            'distribute',
            tool='p10',
            start=self._normalize_address(start),
            blowout=blowout,
            transfers=transfers
        )

    def consolidate(self, end, *wells, blowout=True):
        transfers = []
        for item in wells:
            start, volume = item
            transfers.append({
                'volume': volume,
                'start': self._normalize_address(start)
            })
        self.add_command(
            'consolidate',
            tool='p10',
            end=self._normalize_address(end),
            blowout=blowout,
            transfers=transfers
        )

    def mix(self, start, volume=None, repetitions=None, blowout=True):
        self.add_command(
            'mix',
            tool='p10',
            start=self._normalize_address(start),
            blowout=blowout,
            volume=volume,
            reps=repetitions
        )

    @property
    def actions(self):
        return copy.deepcopy(self._commands)

    def _get_slot(self, name):
        """
        Returns a container within a given slot, can take a slot position
        as a tuple (0, 0) or as a user-friendly name ('A1') or as a label
        ('ingredients').
        """
        slot = None

        try:
            slot = normalize_position(name)
        except TypeError:
            # Try to find the slot as a label.
            if slot in self._container_labels:
                slot = self._container_labels[slot]

        if not slot:
            raise x.MissingContainer("No slot defined for {}".format(name))
        if slot not in self._deck:
            raise x.MissingContainer("Nothing in slot: {}".format(name))

        return self._deck[slot]

    def _normalize_address(self, address):
        """
        Takes an address like "A1:A1" or "Ingredients:A1" and returns a tuple
        like ((0, 0), (0, 0)).

        To retain label names, use humanize_address.
        """

        if ':' not in address:
            raise ValueError(
                "Address must be in the form of 'container:well'."
            )

        container, well = address.split(':')
        well = normalize_position(well)

        try:
            container = normalize_position(container)
        except ValueError:
            # Try to find the slot as a label.
            container = container.lower()
            if container not in self._container_labels:
                raise x.MissingContainer(
                    "Container not found: {}".format(container)
                )
            container = self._container_labels[container]

        return (container, well)

    def humanize_address(self, address):
        """
        Returns a human-readable string for a particular address.

        If ((0, 0), (1, 0)) is passed and no labels are attached to
        A1, this will return 'A1:B1'.

        For ('label', (1, 0)), it will return the valid label with
        the first provided capitalization, for example "LaBeL:B1".
        """
        start, end = address
        try:
            start = normalize_position(start)  # Try to convert 'A1'.
            # Find a label for that tuple position.
            label = self.get_container_label(start)
            if label is not None:
                start = label
        except ValueError:
            # If it's not a tuple position, it's a string label.
            if start.lower() not in self._container_labels:
                raise x.ContainerMissing(
                    "Invalid container: {}".format(start)
                )
            start = self._label_case.get(start.lower(), start)
        end = humanize_position(end)
        return "{}:{}".format(start, end)

    def get_container_label(self, position):
        for label, pos in self._container_labels.items():
            if pos == position:
                return self._label_case[label]
        return None

    def run(self):
        """
        A generator that runs each command and yields the current command
        index and the number of total commands.
        """
        self._initialize_context()
        i = 0
        yield(0, len(self._commands))
        while i < len(self._commands):
            self._run(i)
            i += 1
            yield (i, len(self._commands))

    def run_all(self):
        """
        Convenience method to run every command in a protocol.

        Useful for when you don't care about the progress.
        """
        for _ in self.run():
            pass

    def _initialize_context(self):
        """
        Initializes the context.
        """
        calibration = None
        if self._context_handler:
            calibration = self._context_handler._calibration
        self._context_handler = ContextHandler(self)
        for slot, name in self._containers.items():
            self._context_handler.add_container(slot, name)
        for axis, name in self._instruments.items():
            self._context_handler.add_instrument(axis, name)
        if calibration:
            self._context_handler._calibration = calibration

    def _run_in_context_handler(self, command, **kwargs):
        """
        Runs a command in the virtualized context.

        This is useful for letting us know if there's a problem with a
        particular command without having to wait to run it on the robot.

        If you use this on your own you're going to end up with weird state
        bugs that have nothing to do with the protocol.
        """
        method = getattr(self._context_handler, command)
        if not method:
            raise x.MissingCommand("Command not defined: " + command)
        method(**kwargs)

    def _run(self, index):
        kwargs = copy.deepcopy(self._commands[index])
        command = kwargs.pop('command')
        self._run_in_context_handler(command, **kwargs)
        for h in self._handlers:
            debug(
                "Protocol",
                "{}.{}: {}"
                .format(type(h).__name__, command, kwargs)
            )
            h.before_each()
            method = getattr(h, command)
            method(**kwargs)
            h.after_each()

    def _virtual_run(self):
        """
        Runs protocol on a virtualized MotorHandler to ensure that there are
        no run-specific problems.
        """
        logger = logging.getLogger()
        logger.disabled = True
        mh = self._motor_handler
        self.attach_motor()  # Virtualized motor handler.
        self.run_all()
        self._motor_handler = mh  # Put everything back the way it was.
        logger.disabled = False

    def attach_handler(self, handler_class):
        """
        When you attach a handler, commands are run on the handler in sequence
        when Protocol.run_next() is called.

        You don't have to attach the ContextHandler, you get that for free.
        It's a good example implementation of what these things are
        supposed to do.

        Any command that the robot supports must be present on the Handler
        you pass in, or you'll get exceptions. Just make sure you subclass
        from ProtocolHandler and you'll be fine; empty methods are stubbed
        out for all supported commands.

        Pass in the class, not an instance. This method returns the
        instantiated object, which you can use to do any additional setup
        required for the particular Handler.
        """
        handler = handler_class(self, self._context_handler)
        self._handlers.append(handler)
        return handler

    def export(self, Formatter, validate_run=False, **kwargs):
        """
        Takes a ProtocolFormatter class (see protocol.formats), initializes
        it with any relevant options kwargs, passes in the current protocol,
        and outputs the data appropriate to the specific format.

        If validate_run is set to True, the protocol will be run on a
        virtual robot to catch any runtime errors (ie, no tipracks or
        trash assigned).
        """
        self.bump_version()  # Bump if it hasn't happened manually.
        if validate_run:
            self._virtual_run()
        f = Formatter(self, **kwargs)
        return f.export()

    def attach_motor(self, port=None):
        self._motor_handler = self.attach_handler(MotorControlHandler)
        if port is not None:
            self._motor_handler.connect(port)
        else:
            self._motor_handler.simulate()
        return self._motor_handler

    def disconnect(self):
        if self._motor_handler:
            self._motor_handler.disconnect()
