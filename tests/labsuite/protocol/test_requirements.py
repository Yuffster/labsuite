import unittest
from labsuite.protocol import Protocol
from labsuite.util import exceptions as x
from copy import deepcopy


class ProtocolRequirementsTest(unittest.TestCase):

    def setUp(self):
        self.protocol = Protocol()

    def assertRequirements(self, expected, reqs=None):
        reqs = reqs or self.protocol.run_requirements
        ouch = []
        extra = deepcopy(reqs)
        missing = deepcopy(expected)
        for ei, e in enumerate(expected):
            for ri, r in enumerate(reqs):
                try:
                    self.assertEqual(e, r)
                except AssertionError:
                    continue
                extra[ri] = None
                missing[ei] = None
        extra = [x for x in extra if x is not None]
        missing = [x for x in missing if x is not None]
        if len(extra) > 0:
            ouch.append("Found {} extra items: {}".format(len(extra), extra))
        if len(missing) > 0:
            ouch.append("Missing items: {}".format(missing))
        if len(ouch) > 0:
            assert False, "\n".join(ouch)

    def test_requirements_assertion(self):
        self.assertRequirements(
            [{'foo': 'bar'}, {'bizz': 'buzz'}],
            [{'foo': 'bar'}, {'bizz': 'buzz'}]
        )
        with self.assertRaises(AssertionError):
            self.assertRequirements(
                [{'foo': 'bar'}],
                [{'foo': 'bar'}, {'bizz': 'buzz'}]
            )
        with self.assertRaises(AssertionError):
            self.assertRequirements(
                [{'foo': 'bar'}, {'bizz': 'buzz'}],
                [{'foo': 'bar'}]
            )

    def test_require_instrument_calibration(self):
        self.protocol.add_instrument('A', 'p20')
        self.protocol.add_container('A1', 'microplate')
        self.protocol.add_container('A2', 'tiprack.p20')
        self.protocol.transfer('A1:A1', 'A1:A2', ul=10)
        reqs = [
            {'type': 'calibrate_instrument', 'axis': 'A', 'instrument_name': 'p20'},
            {'type': 'calibrate_container', 'axis': 'A', 'address': (0, 0),
             'container_name': 'microplate', 'instrument_name': 'p20'},
            {'type': 'calibrate_container', 'axis': 'A', 'address': (0, 1),
             'container_name': 'tiprack.p20', 'instrument_name': 'p20'}
        ]
        self.assertRequirements(reqs)
        self.protocol.calibrate_instrument(axis='A', top=10, bottom=10, blowout=10)
        reqs.pop(0)
        self.assertRequirements(reqs)
        self.protocol.calibrate('A1', axis='A')
        reqs.pop(0)
        self.assertRequirements(reqs)
        self.protocol.calibrate('A2', axis='A')
        reqs.pop(0)
        self.assertRequirements(reqs)

    def test_requirements_calibration_multiple_racks(self):
        self.protocol.add_instrument('A', 'p20')
        self.protocol.add_container('A1', 'microplate')
        self.protocol.add_container('A2', 'tiprack.p20')
        self.protocol.add_container('A3', 'tiprack.p20')
        for _ in range(50):
            self.protocol.transfer('A1:A1', 'A1:A2', ul=10)
            self.protocol.transfer('A1:A2', 'A1:A1', ul=10)
        reqs = [
            {'type': 'calibrate_instrument', 'axis': 'A', 'instrument_name': 'p20'},
            {'type': 'calibrate_container', 'axis': 'A', 'address': (0, 0),
             'container_name': 'microplate', 'instrument_name': 'p20'},
            {'type': 'calibrate_container', 'axis': 'A', 'address': (0, 1),
             'container_name': 'tiprack.p20', 'instrument_name': 'p20'},
             {'type': 'calibrate_container', 'axis': 'A', 'address': (0, 2),
             'container_name': 'tiprack.p20', 'instrument_name': 'p20'}
        ]
        self.assertRequirements(reqs)

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
        self.protocol.run_requirements
