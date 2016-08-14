import unittest
from labsuite.labware.microplates import Microplate
from labsuite.labware.deck import Deck
from labsuite.util import exceptions as x


class MicroplateTest(unittest.TestCase):

    expected_margin = 9  # ANSI standard.

    def setUp(self):
        self.plate = Microplate()

    def a2_coordinate_test(self):
        """Calibrated coordinates of A2."""
        a2 = self.plate.well('A2').coordinates()
        self.assertEqual(a2, (0, self.expected_margin))

    def b1_coordinate_test(self):
        """Calibrated coordinates of B1."""
        b1 = self.plate.well('B1').coordinates()
        self.assertEqual(b1, (self.expected_margin, 0))

    def b2_coordinate_test(self):
        """Calibrated coordinates of B2."""
        b2 = self.plate.well('B2').coordinates()
        margin = self.expected_margin
        self.assertEqual(b2, (margin, margin))

    def coordinate_lowercase_test(self):
        """Lowercase coordinates."""
        b2 = self.plate.well('b2').coordinates()
        margin = self.expected_margin
        self.assertEqual(b2, (margin, margin))

    def col_sanity_test(self):
        """Don't return out-of-range columns."""
        col = chr(ord('a') + self.plate.cols + 1)
        with self.assertRaises(x.SlotMissing):
            self.plate.well('{}1'.format(col))

    def unicode_coord_test(self):
        """Unicode coordinates."""
        self.plate.well(u'A1')

    def row_sanity_test(self):
        """Don't return out-of-range rows."""
        row = self.plate.rows + 1
        with self.assertRaises(x.SlotMissing):
            self.plate.well('A{}'.format(row))

    def col_type_sanity_test(self):
        """Sanity check on well coordinates."""
        with self.assertRaises(ValueError):
            self.plate.well('ABC')


class MicroplateWellTest(unittest.TestCase):

    def setUp(self):
        self.plate = Microplate()
        self.well  = self.plate.well('A1')

    def liquid_allocation_test(self):
        """Add volume to well."""
        set_vol = 50
        # Add an initial value of 100ul water to this well.
        self.well.allocate(water=set_vol)
        vol = self.well.get_volume()
        self.assertEqual(vol, set_vol)

    def liquid_capacity_test(self):
        """Reject well overflow volumes."""
        set_vol = 10000
        # Way too much water for a microplate!
        with self.assertRaises(x.LiquidOverflow):
            self.well.allocate(water=set_vol)

    def liquid_total_capacity_test(self):
        """Reject combined well overflow."""
        self.well.allocate(water=90)
        self.well.add_liquid(water=10)
        with self.assertRaises(x.LiquidOverflow):
            self.well.add_liquid(water=1)

    def liquid_total_mixture_test(self):
        """Reject combined well overflow from mixed liquids."""
        self.well.allocate(water=90)
        self.well.add_liquid(buffer=10)
        with self.assertRaises(x.LiquidOverflow):
            self.well.add_liquid(saline=1)

    def mixture_transfer_test(self):
        """Mixture transfers."""
        wellA = self.well
        wellB = self.plate.well('A2')

        wellA.allocate(water=90, buffer=9, saline=1)
        wellA.transfer(20, wellB)

        # Check Well A to ensure things have been removed.
        wat = wellA.get_proportion('water')
        buf = wellA.get_proportion('buffer')
        sal = wellA.get_proportion('saline')

        # We use almostEqual because it's floating-point.
        self.assertAlmostEqual(wat, .9)
        self.assertAlmostEqual(buf, .09)
        self.assertAlmostEqual(sal, .01)

        self.assertEqual(wellA.get_volume(), 80)

        # Check WellB to ensure things have been added.
        wat = wellB.get_proportion('water')
        buf = wellB.get_proportion('buffer')
        sal = wellB.get_proportion('saline')

        # We use almostEqual because it's floating-point.
        self.assertAlmostEqual(wat, .9)
        self.assertAlmostEqual(buf, .09)
        self.assertAlmostEqual(sal, .01)

        self.assertEqual(wellB.get_volume(), 20)

    def proportion_key_error_test(self):
        """Raises for proportion of liquid not present in mixture."""
        with self.assertRaises(x.LiquidMismatch):
            self.well.get_proportion('water')

    def liquid_key_error_test(self):
        """Raises if wrong liquid named in get_volume."""
        self.well.allocate(saline=10)
        with self.assertRaises(x.LiquidMismatch):
            self.well.get_volume('water')

    def liquid_value_error_test(self):
        """Raises on named get_volume if multiple liquids present."""
        self.well.allocate(water=10, saline=10)
        with self.assertRaises(x.LiquidMismatch):
            self.well.get_volume('water')

    def ml_conversion_test(self):
        """ml to µl conversion."""
        self.well.allocate(water=.1, ml=True)
        self.assertEqual(self.well.get_volume(), 100)
