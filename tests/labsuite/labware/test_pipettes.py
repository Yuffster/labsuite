import unittest
from labsuite.labware import pipettes


class MockPipette(pipettes.Pipette):
    min_vol = 1
    max_vol = 10

    _top = None
    _blowout = None
    _droptip = None

    _points = [
        {'f1': 1, 'f2': 1},
        {'f1': 10, 'f2': 10}
    ]


class PipetteTest(unittest.TestCase):

    def setUp(self):
        self.pipette = MockPipette()

    def test_volume_beyond_range(self):
        """Rejects volume beyond max range."""
        with self.assertRaises(IndexError):
            self.pipette._volume_percentage(11)

    def test_volume_below_zero(self):
        """Rejects volume below zero."""
        with self.assertRaises(IndexError):
            self.pipette._volume_percentage(-1)

    def test_percentages(self):
        """Linear percentages."""
        # The point map is just linear...
        for i in range(1, 10):
            n = self.pipette._volume_percentage(i)
            self.assertEqual(n, i / 10)

    def test_plunge_depth(self):
        """Calculates plunger depth."""
        self.pipette.calibrate(top=15, blowout=115)
        depth = self.pipette.plunge_depth(1)
        self.assertEqual(depth, 25)

    def test_max_volume(self):
        """Returns percentage for max volume."""
        self.pipette._volume_percentage(10)

    def test_load_instrument(self):
        """Loads instruments."""
        p = pipettes.load_instrument('p10')
        self.assertIsInstance(p, pipettes.Pipette_P10)

    def test_volume_support(self):
        """ Volume support. """
        self.assertEqual(self.pipette.supports_volume(10), True)
        self.assertEqual(self.pipette.supports_volume(1), True)
        self.assertEqual(self.pipette.supports_volume(0), False)
        self.assertEqual(self.pipette.supports_volume(11), False)

    def test_multichannel_pipettes(self):
        # p2
        p2 = pipettes.load_instrument('p2')
        p2_12 = pipettes.load_instrument('p2.12')
        p2_8 = pipettes.load_instrument('p2.8')
        self.assertEqual(p2.channels, 1)
        self.assertEqual(p2_12.channels, 12)
        self.assertEqual(p2_8.channels, 8)
        # p10
        p10 = pipettes.load_instrument('p10')
        p10_12 = pipettes.load_instrument('p10.12')
        p10_8 = pipettes.load_instrument('p10.8')
        self.assertEqual(p10.channels, 1)
        self.assertEqual(p10_12.channels, 12)
        self.assertEqual(p10_8.channels, 8)
        # p20
        p20 = pipettes.load_instrument('p20')
        p20_12 = pipettes.load_instrument('p20.12')
        p20_8 = pipettes.load_instrument('p20.8')
        self.assertEqual(p20.channels, 1)
        self.assertEqual(p20_12.channels, 12)
        self.assertEqual(p20_8.channels, 8)
        # p200
        p200 = pipettes.load_instrument('p200')
        p200_12 = pipettes.load_instrument('p200.12')
        p200_8 = pipettes.load_instrument('p200.8')
        self.assertEqual(p200.channels, 1)
        self.assertEqual(p200_12.channels, 12)
        self.assertEqual(p200_8.channels, 8)
        # p1000
        p1000 = pipettes.load_instrument('p1000')
        p1000_12 = pipettes.load_instrument('p1000.12')
        p1000_8 = pipettes.load_instrument('p1000.8')
        self.assertEqual(p1000.channels, 1)
        self.assertEqual(p1000_12.channels, 12)
        self.assertEqual(p1000_8.channels, 8)
