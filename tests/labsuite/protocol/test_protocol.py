import unittest
from labsuite.protocol import Protocol
from labsuite.protocol.formatters import JSONFormatter
from labsuite.util import exceptions as x

class ProtocolTest(unittest.TestCase):

    def setUp(self):
        self.protocol = Protocol()
        self.maxDiff = None

    @property
    def instructions(self):
        return self.protocol._commands

    def test_normalize_address(self):
        self.protocol.add_container('A1', 'microplate.96', label="Output")
        label = self.protocol._normalize_address('Output:A1')
        self.assertEqual(label, ((0, 0), (0, 0)))
        slot = self.protocol._normalize_address('A1:A1')
        self.assertEqual(slot, ((0, 0), (0, 0)))

    def test_info(self):
        name = "Foo Bar"
        desc = "Lorem ipsum dolor set amet."
        auth = "Jane Doe"
        self.protocol.set_info(name=name, description=desc, author=auth)
        i = self.protocol.info
        self.assertEqual(i['name'], name)
        self.assertEqual(i['description'], desc)
        self.assertEqual(i['author'], auth)
        self.assertTrue('created' in i)
        self.assertTrue('updated' in i)

    def test_humanize_address(self):
        self.protocol.add_container("A1", 'microplate.96', label="LaBeL")
        with self.assertRaises(x.ContainerConflict):
            self.protocol.add_container("A2", 'microplate.96', label="label")
        self.protocol.add_container("A2", 'microplate.96', label="stuff")
        lA1 = self.protocol.humanize_address(('label', 'A1'))
        sA1 = self.protocol.humanize_address(('STUFF', 'A1'))
        self.assertEqual(lA1, 'LaBeL:A1')
        self.assertEqual(sA1, 'stuff:A1')

    def test_transfer(self):
        """ Basic transfer. """
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_container('B1', 'microplate.96')
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_instrument('B', 'p20')
        self.protocol.transfer('A1:A1', 'B1:B1', ul=100, tool='p200')
        expected = [{
            'command': 'transfer',
            'tool': 'p200',
            'volume': 100,
            'start': ((0, 0), (0, 0)),
            'end': ((1, 0), (1, 0)),
            'blowout': True,
            'touchtip': True
        }]
        self.assertEqual(self.instructions, expected)

    def test_transfer_without_pipette(self):
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(x.InstrumentMissing):
            self.protocol.transfer('A1:A1', 'A1:A2', ul=10)

    def test_transfer_without_volume(self):
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.transfer("A1:A1", "A1:A1")

    def test_transfer_zero_volume(self):
        with self.assertRaises(ValueError):
            self.protocol.transfer("A1:A1", "A1:A1", ul=0)
        with self.assertRaises(ValueError):
            self.protocol.transfer("A1:A1", "A1:A1", ml=0)

    def test_transfer_conflicting_volume(self):
        with self.assertRaises(ValueError):
            self.protocol.transfer("A1:A1", "A1:A1", ul=1, ml=1)

    def test_transfer_group(self):
        """ Transfer group. """
        expected = [{
            'command': 'transfer_group',
            'tool': 'p20',
            'transfers': [
                {
                    'volume': 15,
                    'start': ((0, 0), (0, 0)),  # A1:A1
                    'end': ((0, 0), (1, 0)),  # A1:B1
                    'blowout': True,
                    'touchtip': True
                },
                {
                    'volume': 10,
                    'start': ((0, 0), (0, 1)),  # A1:A2
                    'end': ((0, 0), (1, 1)),  # A1:B2
                    'blowout': True,
                    'touchtip': True
                },
                {
                    'volume': 12,
                    'start': ((0, 0), (0, 2)),  # A1:A3
                    'end': ((0, 0), (1, 2)),  # A1:B3
                    'blowout': False,
                    'touchtip': True
                },
                {
                    'volume': 12,
                    'start': ((0, 0), (0, 3)),  # A1:A4
                    'end': ((0, 0), (1, 3)),  # A1:B4
                    'blowout': True,
                    'touchtip': True
                },
                {
                    'volume': 12,
                    'start': ((0, 0), (0, 4)),  # A1:A5
                    'end': ((0, 0), (1, 4)),  # A1:B5
                    'blowout': True,
                    'touchtip': True
                }
            ]
        }]
        self.protocol.add_container('A1', 'microplate.96', label="Label")
        self.protocol.add_instrument('A', 'p20')
        self.protocol.transfer_group(
            ('A1:A1', 'A1:B1', {'ul': 15}),
            ('A1:A2', 'A1:B2', {'ul': 10}),
            ('A1:A3', 'A1:B3', {'blowout': False}),
            ('A1:A4', 'A1:B4'),
            ('A1:A5', 'A1:B5'),
            ul=12,
            tool='p20'
        )
        self.assertEqual(self.instructions, expected)

    def test_transfer_group_without_pipette(self):
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(x.InstrumentMissing):
            self.protocol.transfer_group(
                ('A1:A1', 'A1:B1', {'ul': 15}),
                ('A1:A2', 'A1:B2', {'ml': 1}),
                ('A1:A3', 'A1:B3', {'blowout': False}),
                ('A1:A4', 'A1:B4'),
                ('A1:A5', 'A1:B5'),
                ul=12,
                tool='p10'
            )

    def test_transfer_group_without_volume(self):
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.add_instrument('A', 'p10')
            self.protocol.transfer_group(
                ('A1:A1', 'A1:B1'),
                ('A1:A2', 'A1:B2'),
                ('A1:A3', 'A1:B3', {'blowout': False}),
                ('A1:A4', 'A1:B4'),
                ('A1:A5', 'A1:B5'),
                tool='p10'
            )

    def test_transfer_group_zero_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.transfer_group(
                ('A1:A1', 'A1:B1'),
                ('A1:A2', 'A1:B2'),
                ('A1:A3', 'A1:B3', {'blowout': False}),
                ('A1:A4', 'A1:B4'),
                ('A1:A5', 'A1:B5'),
                ul=0,
                tool='p10'
            )
        with self.assertRaises(ValueError):
            self.protocol.transfer_group(
                ('A1:A1', 'A1:B1'),
                ('A1:A2', 'A1:B2'),
                ('A1:A3', 'A1:B3', {'blowout': False}),
                ('A1:A4', 'A1:B4'),
                ('A1:A5', 'A1:B5'),
                ml=0,
                tool='p10'
            )

    def test_transfer_group_conflicting_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.transfer_group(
                ('A1:A1', 'A1:B1'),
                ('A1:A2', 'A1:B2'),
                ('A1:A3', 'A1:B3', {'blowout': False}),
                ('A1:A4', 'A1:B4'),
                ('A1:A5', 'A1:B5'),
                ul=5,
                ml=4,
                tool='p10'
            )

    def test_distribute(self):
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.distribute(
            'A1:A1',
            ('A1:B1', {'ul': 50}),
            ('A1:C1'),
            ('A1:D1', {'ul': 30}),
            ul=20
        )
        expected = [{
            'command': 'distribute',
            'tool': 'p200',
            'start': ((0, 0), (0, 0)),
            'transfers': [
                {
                    'volume': 50,
                    'end': ((0, 0), (1, 0)),  # A1:B1
                    'blowout': True,
                    'touchtip': True
                },
                {
                    'volume': 20,  # Default
                    'end': ((0, 0), (2, 0)),  # A1:C1
                    'blowout': True,
                    'touchtip': True
                },
                {
                    'volume': 30,
                    'end': ((0, 0), (3, 0)),  # A1:D1
                    'blowout': True,
                    'touchtip': True
                }
            ]
        }]
        self.assertEqual(self.instructions, expected)

    def test_distribute_without_pipette(self):
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(x.InstrumentMissing):
            self.protocol.distribute(
                'A1:A1',
                ('A1:B1', {'ul': 50}),
                ('A1:C1', {'ul': 5}),
                ('A1:D1', {'ul': 10})
            )

    def test_distribute_zero_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.distribute(
                'A1:A1',
                ('A1:B1', {'ul': 4}),
                ('A1:C1', {'ul': 5}),
                ('A1:D1', {'ul': 0})
            )

    def test_distribute_conflicting_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.distribute(
                'A1:A1',
                ('A1:B1'),
                ('A1:C1'),
                ('A1:D1', {'ul': 10, 'ml': 5}),
                ul=5
            )

    def test_consolidate(self):
        """ Consolidate. """
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_instrument('A', 'p200')
        self.protocol.consolidate(
            'A1:A1',
            ('A1:B1', {'ul': 50}),
            ('A1:C1', {'ul': 25}),
            ('A1:D1'),
            ul=30
        )
        expected = [{
            'command': 'consolidate',
            'tool': 'p200',
            'end': ((0, 0), (0, 0)),
            'transfers': [
                {
                    'volume': 50,
                    'start': ((0, 0), (1, 0)),  # A1:B1
                    'blowout': True,
                    'touchtip': True
                },
                {
                    'volume': 25,
                    'start': ((0, 0), (2, 0)),  # A1:C1
                    'blowout': True,
                    'touchtip': True
                },
                {
                    'volume': 30,
                    'start': ((0, 0), (3, 0)), # A1:D1
                    'blowout': True,
                    'touchtip': True
                }
            ]
        }]
        self.assertEqual(self.instructions, expected)

    def test_consolidate_without_pipette(self):
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(x.InstrumentMissing):
            self.protocol.consolidate(
                'A1:A1',
                ('A1:B1', {'ul': 50}),
                ('A1:C1', {'ul': 5}),
                ('A1:D1', {'ul': 10})
            )

    def test_consolidate_zero_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.consolidate(
                'A1:A1',
                ('A1:B1', {'ul': 4}),
                ('A1:C1', {'ul': 5}),
                ('A1:D1', {'ul': 0})
            )

    def test_consolidate_conflicting_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.consolidate(
                'A1:A1',
                ('A1:B1', {'ul': 5}),
                ('A1:C1', {'ul': 5}),
                ('A1:D1', {'ul': 10, 'ml': 5})
            )

    def test_mix(self):
        """ Mix. """
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_instrument('A', 'p200')
        self.protocol.mix('A1:A1', ul=50, repetitions=10)
        expected = [{
            'command': 'mix',
            'tool': 'p200',
            'start': ((0, 0), (0, 0)),  # A1:A1
            'blowout': True,
            'touchtip': True,
            'volume': 50,
            'reps': 10
        }]
        self.assertEqual(self.instructions, expected)

    def test_mix_without_pipette(self):
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(x.InstrumentMissing):
            self.protocol.mix('A1:A1', ul=50, repetitions=10, tool='p200')

    def test_mix_without_volume(self):
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_instrument('A', 'p10')
        with self.assertRaises(ValueError):
            self.protocol.mix('A1:A1', repetitions=10, tool='p10')

    def test_mix_zero_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.mix('A1:A1', ul=0, repetitions=10, tool='p10')
        with self.assertRaises(ValueError):
            self.protocol.mix('A1:A1', ml=0, repetitions=10, tool='p10')

    def test_mix_conflicting_volume(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96')
        with self.assertRaises(ValueError):
            self.protocol.mix('A1:A1', ul=1, ml=1, repetitions=10, tool='p10')

    def test_protocol_run_twice(self):
        """ Run a protocol twice without error. """
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_container('C1', 'tiprack.p200')
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.calibrate('A1', x=1, y=2, z=3)
        self.protocol.calibrate_instrument('A', top=0, blowout=10)
        self.protocol.transfer('A1:A1', 'A1:A2', ul=100)
        self.protocol.transfer('A1:A2', 'A1:A3', ul=80)
        self.protocol.run_all()
        self.protocol.run_all()

    def test_protocol_equality(self):
        # Set up a protocol.
        p1 = Protocol()
        p1.add_instrument('A', 'p200')
        p1.add_container('C1', 'tiprack.p200')
        p1.add_container('A1', 'microplate.96')
        p1.calibrate('A1', x=1, y=2, z=3)
        p1.calibrate_instrument('A', top=0, blowout=10)
        p1.transfer('A1:A1', 'A1:A2', ul=100)
        p1.transfer('A1:A2', 'A1:A3', ul=80)

        # And a copy.
        p2 = Protocol()
        p2.add_container('A1', 'microplate.96')
        p2.add_container('C1', 'tiprack.p200')
        p2.add_instrument('A', 'p200')
        p2.calibrate('A1', x=1, y=2, z=3)
        p2.calibrate_instrument('A', top=0, blowout=10)
        p2.transfer('A1:A1', 'A1:A2', ul=100)
        p2.transfer('A1:A2', 'A1:A3', ul=80)

        # They're identical.
        self.assertEqual(p1, p2)

        # Make a change.
        p2.add_instrument('B', 'p10')

        # No longer identical.
        self.assertNotEqual(p1, p2)

    def test_protocol_version(self):
        # Set up a protocol.
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_container('C1', 'tiprack.p200')
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.calibrate('A1', x=1, y=2, z=3)
        self.protocol.calibrate_instrument('A', top=0, blowout=10)
        self.protocol.transfer('A1:A1', 'A1:A2', ul=100)
        self.protocol.transfer('A1:A2', 'A1:A3', ul=80)

        # First version bump.
        v1 = self.protocol.bump_version()
        self.assertEqual(v1, '0.0.1')

        # No changes, version will stay the same.
        v2 = self.protocol.bump_version()
        self.assertEqual(v1, v2)

        # Make a change, bump the version.
        self.protocol.transfer('A1:A2', 'A1:A3', ul=80)
        v3 = self.protocol.bump_version()
        self.assertEqual(v3, '0.0.2')

        # Make a change, bump the version.
        self.protocol.transfer('A1:A1', 'A1:A1', ul=20)
        v4 = self.protocol.bump_version('feature')
        self.assertEqual(v4, '0.1.0')

        # Make a change, bump the version.
        self.protocol.transfer('A1:A1', 'A1:A1', ul=20)
        v5 = self.protocol.bump_version('major')
        self.assertEqual(v5, '1.0.0')

    def test_partial_protocol(self):
        p = Protocol.partial()
        p.transfer('A1:A1', 'A1:A3', ul=1)
        # As long as it doesn't throw an Exception, we're good.

    def test_partial_protocol_run(self):
        p = Protocol.partial()
        p.transfer('A1:A1', 'A1:A3', ul=1)
        with self.assertRaises(x.PartialProtocolException):
            # This shouldn't run because it's not valid.
            p.run_all()

    def test_valid_partial_protocol_run(self):
        p = Protocol.partial()
        p.add_instrument('A', 'p10')
        p.add_container("A1", "microplate.96")
        p.transfer('A1:A1', 'A1:A3', ul=1)
        # This should run because there are no Partial problems.
        p.run_all()

    def test_partial_protocol_export(self):
        p = Protocol.partial()
        p.transfer('A1:A1', 'A1:A3', ul=1)
        with self.assertRaises(x.PartialProtocolException):
            # This shouldn't export because it's not valid.
            p.export(JSONFormatter)

    def test_valid_partial_protocol_export(self):
        p = Protocol.partial()
        p.add_instrument('A', 'p10')
        p.add_container("A1", "microplate.96")
        p.transfer('A1:A1', 'A1:A3', ul=1)
        # This should export because there are no Partial problems.
        p.export(JSONFormatter)

    def test_protocol_addition_of_partial(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p20')
        p1.add_container('A1', 'microplate.96')
        p1.transfer('A1:A1', 'A1:A2', ul=10)

        p2 = Protocol.partial()
        p2.add_container('A2', 'microplate.96')
        p2.transfer('A1:A1', 'A1:A3', ul=20)
        p2.transfer('A2:A1', 'A2:A4', ul=15)

        p3 = Protocol()
        p3.add_instrument('A', 'p20')
        p3.add_container('A1', 'microplate.96')
        p3.add_container('A2', 'microplate.96')
        p3.transfer('A1:A1', 'A1:A2', ul=10)
        p3.transfer('A1:A1', 'A1:A3', ul=20)
        p3.transfer('A2:A1', 'A2:A4', ul=15)

        self.assertEqual(p3, p1 + p2)

    def test_protocol_addition_of_partials(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p20')
        p1.add_container('A1', 'microplate.96')
        p1.transfer('A1:A1', 'A1:A2', ul=10)

        p2 = Protocol.partial()
        p2.add_container('A2', 'microplate.96')
        p2.transfer('A1:A1', 'A1:A3', ul=20)
        p2.transfer('A2:A1', 'A2:A4', ul=15)

        p3 = Protocol.partial()
        p3.add_container('A3', 'microplate.96')
        p3.transfer('A1:A1', 'A1:A3', ul=20)
        p3.transfer('A1:A1', 'A3:A4', ul=15)

        p4 = Protocol()
        p4.add_instrument('A', 'p20')
        p4.add_container('A1', 'microplate.96')
        p4.add_container('A2', 'microplate.96')
        p4.add_container('A3', 'microplate.96')
        p4.transfer('A1:A1', 'A1:A2', ul=10)
        p4.transfer('A1:A1', 'A1:A3', ul=20)
        p4.transfer('A2:A1', 'A2:A4', ul=15)
        p4.transfer('A1:A1', 'A1:A3', ul=20)
        p4.transfer('A1:A1', 'A3:A4', ul=15)

        self.assertEqual(p4, p1 + p2 + p3)

    def test_protocol_added_to_partial(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p20')
        p1.add_container('A1', 'microplate.96')
        p1.transfer('A1:A1', 'A1:A2', ul=10)

        p2 = Protocol.partial()
        p2.add_container('A2', 'microplate.96')
        p2.transfer('A1:A1', 'A1:A3', ul=20)
        p2.transfer('A2:A1', 'A2:A4', ul=15)

        with self.assertRaises(TypeError):
            p2 + p1

    def test_protocol_addition(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p10')
        p1.add_container('A1', 'microplate.96')
        p1.transfer('A1:A1', 'A1:A1', ul=10)

        p2 = Protocol()
        p2.add_instrument('A', 'p10')  # Same definition; no conflict.
        p2.add_instrument('B', 'p20')  # New instrument.
        p2.add_container('A1', 'microplate.96')  # No conflict.
        p2.add_container('A2', 'microplate.96')  # New container.
        p2.transfer('A1:A1', 'A1:A1', ul=12)
        p2.transfer('A1:A1', 'A2:A2', ul=20)

        p3 = Protocol()
        p3.add_instrument('A', 'p10')
        p3.add_instrument('B', 'p20')
        p3.add_container('A1', 'microplate.96')
        p3.add_container('A2', 'microplate.96')
        p3.transfer('A1:A1', 'A1:A1', ul=10)
        p3.transfer('A1:A1', 'A1:A1', ul=12)
        p3.transfer('A1:A1', 'A2:A2', ul=20)

        self.assertEqual(p3, p1 + p2)

    def test_protocol_label_addition(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p10')
        p1.add_container('A1', 'microplate.96', label="Input")
        p1.transfer('A1:A1', 'A1:A1', ul=10)

        p2 = Protocol()
        p2.add_instrument('A', 'p10')  # Same definition; no conflict.
        p2.add_instrument('B', 'p20')  # New instrument.
        p2.add_container('A1', 'microplate.96', label="Input")  # No conflict.
        p2.add_container('A2', 'microplate.96')  # New container.
        p2.transfer('A1:A1', 'A1:A1', ul=9)
        p2.transfer('Input:A1', 'A2:A2', ul=20)

        p3 = Protocol()
        p3.add_instrument('A', 'p10')
        p3.add_instrument('B', 'p20')
        p3.add_container('A1', 'microplate.96', label="Input")
        p3.add_container('A2', 'microplate.96')
        p3.transfer('A1:A1', 'A1:A1', ul=10)
        p3.transfer('A1:A1', 'A1:A1', ul=9)
        p3.transfer('A1:A1', 'A2:A2', ul=20)

        self.assertEqual(p3, p1 + p2)

    def test_protocol_addition_label_conflict(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p10')
        p1.add_container('A1', 'microplate.96', label="Input")
        p1.transfer('A1:A1', 'A1:A1', ul=10)

        p2 = Protocol()
        p2.add_instrument('A', 'p10')  # Same definition; no conflict.
        p2.add_instrument('B', 'p20')  # New instrument.
        p2.add_container('A1', 'microplate.96', label="Output")  # Conflict.
        p2.add_container('A2', 'microplate.96')  # New container.
        p2.transfer('A1:A1', 'A1:A1', ul=12)
        p2.transfer('Output:A1', 'A2:A2', ul=20)

        with self.assertRaises(x.ContainerConflict):
            p1 + p2

    def test_protocol_addition_label_case(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p10')
        p1.add_container('A1', 'microplate.96', label="Input")

        p2 = Protocol()
        p2.add_instrument('A', 'p10')
        p2.add_container('A1', 'microplate.96', label="INPUT")

        p3 = Protocol()
        p3.add_instrument('A', 'p10')
        p3.add_container('A1', 'microplate.96', label="INPUT")

        self.assertEqual((p1 + p2), p3)

    def test_protocol_addition_info(self):
        p1 = Protocol()
        p1.set_info(author="John Doe", name="Lorem Ipsum")

        p2 = Protocol()
        p2.set_info(author="Jane Doe")

        p3 = p1 + p2

        self.assertEqual('Jane Doe', p3.info['author'])
        self.assertEqual('Lorem Ipsum', p3.info['name'])

    def test_protocol_addition_container_conflict(self):
        p1 = Protocol()
        p1.add_instrument('A', 'p10')
        p1.add_container('A1', 'microplate.96')
        p1.transfer('A1:A1', 'A1:A2', ul=10)

        p2 = Protocol()
        p2.add_container('A1', 'tiprack.p20')

        with self.assertRaises(x.ContainerConflict):
            p1 + p2
