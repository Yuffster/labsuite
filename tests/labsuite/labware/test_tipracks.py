import unittest
from labsuite.labware import tipracks
from labsuite.util import exceptions as x
from labsuite.labware.grid import humanize_position


class TiprackTest(unittest.TestCase):

    expected_margin = 9  # ANSI standard.

    def setUp(self):
        self.rack = tipracks.Tiprack()

    def test_a2_coordinate(self):
        """
        Calibration included in A2 slot coordinates.
        """
        a2 = self.rack.tip('A2').coordinates()
        self.assertEqual(a2, (0, self.expected_margin))

    def test_b1_coordinate(self):
        """
        Coordinates for B1 position.
        """
        b1 = self.rack.tip('B1').coordinates()
        self.assertEqual(b1, (self.expected_margin, 0))

    def test_b2_coordinate(self):
        """
        Coordinates for B2 position.
        """
        b2 = self.rack.tip('B2').coordinates()
        margin = self.expected_margin
        self.assertEqual(b2, (margin, margin))

    def test_coordinate_lowercase(self):
        """
        Accept lowercase coordinates.
        """
        b2 = self.rack.tip('b2').coordinates()
        margin = self.expected_margin
        self.assertEqual(b2, (margin, margin))

    def test_col_sanity(self):
        """
        Maintain sanity of column values.
        """
        col = chr(ord('a') + self.rack.cols)
        with self.assertRaises(x.SlotMissing):
            self.rack.tip('{}1'.format(col))

        col = chr(ord('a') + self.rack.cols - 1)
        self.rack.tip('{}1'.format(col))

    def test_row_sanity(self):
        """
        Maintain sanity of row values.
        """
        row = self.rack.rows + 1

        with self.assertRaises(x.SlotMissing):
            self.rack.tip('A{}'.format(row))

        row = self.rack.rows
        self.rack.tip('A{}'.format(row))

    def test_tiprack_tag(self):
        """
        Tips on specific racks can be tagged for reuse.
        """
        rack = self.rack

        a1 = rack.get_next_tip().position
        a2 = rack.get_next_tip().position
        a3 = rack.get_next_tip().position

        a4 = rack.get_next_tip(tag='water').position
        a5 = rack.get_next_tip(tag='saline').position

        also_a4 = rack.get_next_tip(tag='water').position
        also_a5 = rack.get_next_tip('saline').position

        self.assertEqual(a1, rack.tip('a1').position)
        self.assertEqual(a2, rack.tip('a2').position)
        self.assertEqual(a3, rack.tip('a3').position)
        self.assertEqual(a4, rack.tip('a4').position)
        self.assertEqual(a5, rack.tip('a5').position)
        self.assertEqual(also_a4, rack.tip('a4').position)
        self.assertEqual(also_a5, rack.tip('a5').position)

    def test_set_tips_used_test(self):
        """ Dump and reload tips used. """
        self.rack.set_tips_used(10)
        self.assertEqual(self.rack.tips_used, 10)

    def test_used_tip_offset(self):
        """ Account for used tip offset. """
        self.rack.set_tips_used(1)
        self.assertEqual(
            self.rack.tip('A2').position,
            self.rack.get_next_tip().position
        )
        self.rack.set_tips_used(12)
        self.assertEqual(
            self.rack.tip('B1').position,
            self.rack.get_next_tip().position  # 13th tip
        )

    def test_has_tips(self):
        self.rack.set_tips_used(95)
        self.assertEqual(self.rack.has_tips, True)
        self.rack.set_tips_used(96)
        self.assertEqual(self.rack.has_tips, False)

    def test_slot_row_col_exceptions(self):
        tip = self.rack.tip('A1')
        tip.set_used()
        self.assertEqual(
            self.rack.tip('A2').position,
            self.rack.get_next_tip().position
        )
        with self.assertRaises(x.TipMissing):
            self.rack.row(0).set_used()
        with self.assertRaises(x.TipMissing):
            self.rack.row(1).set_used()
        with self.assertRaises(x.TipMissing):
            self.rack.col('A').set_used()

    def test_get_next_row(self):
        self.rack.tip('A1').set_used()
        row2 = self.rack.row(2)
        row2.set_used()
        colc = self.rack.col('c')
        with self.assertRaises(x.TipMissing):
            colc.set_used()
        row3 = self.rack.get_clean_row().position
        self.assertEqual(row3, [(i, 3) for i in range(8)])
        # Same because get_clean_row is nondestructive.
        row4 = self.rack.get_next_row().position
        self.assertEqual(row4, [(i, 3) for i in range(8)])

    def test_slot_get_clean_col(self):
        self.rack.tip('A1').set_used()
        col = self.rack.get_clean_col().position
        self.assertEqual(col, [(1, i) for i in range(12)])
        # Same because get_clean_col is nondestructive.
        col2 = self.rack.get_next_col().position
        self.assertEqual(col2, [(1, i) for i in range(12)])
        col3 = self.rack.get_clean_col().position
        self.assertEqual(col3, [(2, i) for i in range(12)])

    def test_no_clean_col(self):
        for _ in range(self.rack.cols):
            self.rack.get_next_col()
        with self.assertRaises(x.TipMissing):
            self.rack.get_next_col()

    def test_no_clean_row(self):
        for _ in range(self.rack.rows):
            self.rack.get_next_row()
        with self.assertRaises(x.TipMissing):
            self.rack.get_next_row()

    def test_no_clean_tip(self):
        for _ in range(self.rack.rows):
            self.rack.get_next_row()
        with self.assertRaises(x.TipMissing):
            self.rack.get_next_tip()
