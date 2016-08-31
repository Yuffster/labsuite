import unittest
from labsuite.protocol import Protocol
from labsuite.util import exceptions as x


class MotorHandlerTest(unittest.TestCase):

    def setUp(self):
        self.protocol = Protocol()

    def test_basic_transfer(self):
        """ Basic transfer. """
        motor = self.protocol.attach_motor()
        output_log = motor._driver
        self.protocol.add_instrument('A', 'p20')
        self.protocol.add_instrument('B', 'p200')
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_container('C1', 'tiprack.p200')
        self.protocol.add_container('B1', 'tiprack.p20')
        self.protocol.add_container('B2', 'point.trash')
        self.protocol.calibrate('A1', axis="A", x=1, y=2, top=3, bottom=10)
        self.protocol.calibrate('B1', axis="A", x=4, y=5, top=6, bottom=15)
        self.protocol.calibrate('B2', axis="A", x=50, y=60, top=70)
        self.protocol.calibrate('A1:A2', axis="B", bottom=5)
        self.protocol.calibrate('C1', axis="B", x=100, y=100, top=50)
        self.protocol.calibrate('B2', axis="B", x=200, y=250, top=15)
        self.protocol.calibrate('A1', axis="B", x=1, y=2, top=3, bottom=13)
        self.protocol.calibrate_instrument('A', top=0, blowout=1, droptip=2)
        self.protocol.calibrate_instrument('B', top=0, blowout=10, droptip=25)
        self.protocol.transfer('A1:A1', 'A1:A2', ul=10)
        self.protocol.transfer('A1:A2', 'A1:A3', ul=80)
        prog_out = []
        for progress in self.protocol.run():
            prog_out.append(progress)
        expected = [
            # Transfer 1.
            {'x': 4, 'y': 5},  # Pickup tip.
            {'z': 6},
            {'z': 0},  # Move to well.
            {'x': 1, 'y': 2},
            {'z': 3},
            {'a': 0.5},  # Plunge.
            {'x': 1, 'y': 2},
            {'z': 10},  # Move into well.
            {'a': 0},  # Release.
            {'z': 0},  # Move up.
            {'x': 1, 'y': 11},  # Move to well.
            {'z': 3},
            {'x': 1, 'y': 11},
            {'z': 10},  # Move into well.
            {'a': 1},  # Blowout.
            {'z': 0},  # Move up.
            {'a': 0},  # Release.
            {'x': 50, 'y': 60},  # Dispose tip.
            {'z': 70},
            {'a': 2},
            {'a': 0},
            # Transfer 2.
            {'x': 100, 'y': 100},
            {'z': 50},
            {'z': 0},
            {'x': 1, 'y': 11},
            {'z': 3},
            {'b': 4.0},
            {'x': 1, 'y': 11},
            {'z': 5},
            {'b': 0},
            {'z': 0},
            {'x': 1, 'y': 20},
            {'z': 3},
            {'x': 1, 'y': 20},
            {'z': 13},
            {'b': 10},
            {'z': 0},
            {'b': 0},
            {'x': 200, 'y': 250},
            {'z': 15},
            {'b': 25},
            {'b': 0}
        ]
        self.assertEqual(expected, output_log.movements)
        self.assertEqual([(0, 2), (1, 2), (2, 2)], prog_out)

    def test_calibrate_without_axis(self):
        self.protocol.add_instrument('A', 'p20')
        self.protocol.add_instrument('B', 'p200')
        with self.assertRaises(x.DataMissing):
            self.protocol.calibrate('A1', top=0, bottom=0)

    def test_transfer_without_tiprack(self):
        """ Raise error when no tiprack found. """
        self.protocol.attach_motor()
        self.protocol.add_instrument('B', 'p200')
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.calibrate('A1', top=0, bottom=0)
        self.protocol.calibrate_instrument('B', top=0, blowout=10)
        self.protocol.transfer('A1:A1', 'A1:A2', ul=100)
        with self.assertRaises(x.ContainerMissing):
            self.protocol.run_all()

    def test_transfer_without_dispose_point(self):
        """ Raise when no dispose point set. """
        self.protocol.attach_motor()
        self.protocol.add_instrument('B', 'p200')
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_container('C1', 'tiprack.p200')
        self.protocol.calibrate('A1')
        self.protocol.calibrate('C1')
        self.protocol.calibrate_instrument('B', top=0, blowout=10)
        self.protocol.transfer('A1:A1', 'A1:A2', ul=100)
        self.protocol.transfer('A1:A2', 'A1:A3', ul=80)

        with self.assertRaises(x.ContainerMissing):
            self.protocol.run_all()

    def test_instrument_missing(self):
        with self.assertRaises(x.InstrumentMissing):
            m = self.protocol.attach_motor()
            m.get_pipette(has_volume=1000)

    def test_no_errors_from_commands(self):
        self.protocol.add_instrument('B', 'p200')
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_container('B1', 'tiprack.p200')
        self.protocol.add_container('C1', 'point.trash')
        self.protocol.calibrate('A1')
        self.protocol.calibrate('B1')
        self.protocol.calibrate('C1')
        self.protocol.calibrate('A1', x=1, y=2, top=3, bottom=13)
        self.protocol.calibrate_instrument('B', top=0, blowout=10, droptip=25)
        self.protocol.transfer('A1:A1', 'A1:A2', ul=100)
        self.protocol.transfer_group(
            ('A1:A1', 'A1:A2', {'ul': 100})
        )
        self.protocol.consolidate(
            'A1:A1',
            ('A1:A2', {'ul':100}),
            ('A1:A2', {'ul':150})
        )
        self.protocol.distribute(
            'A1:A1',
            ('A1:A2', {'ul':100}),
            ('A1:A2', {'ul':150})
        )
        self.protocol.mix('A1:A2', ul=100, repetitions=5)
        motor = self.protocol.attach_motor()
        output_log = motor._driver
        movements = output_log.movements

        # We're not really testing anything except that it runs without
        # errors.
        self.protocol.run_all()
