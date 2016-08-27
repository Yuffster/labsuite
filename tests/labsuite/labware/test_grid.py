import unittest
from labsuite.labware.grid import GridContainer, ItemGroup, normalize_position, humanize_position
from labsuite.compilers.plate_map import PlateMap
from labsuite.labware.microplates import Microplate
from labsuite.labware.deck import Deck
import os


class MockGroup(ItemGroup):
    pass


class MockItem():

    n = 0  # Just a counter for testing.
    thing = None  # Instance variable.

    def __init__(self, n):
        self.n = n

    def add(self, n):
        self.n += n
        return self.n

    def set_thing(self, thing):
        self.thing = thing

    @property
    def successor(self):
        return self.n + 1  # I've been doing Haskell. :3


class GridTest(unittest.TestCase):

    def test_normalize_position(self):
        """
        Normalize coordinate strings ('A1')
        """
        expected = normalize_position('A1')
        self.assertEqual(expected, (0, 0))

        expected = normalize_position('B1')
        self.assertEqual(expected, (1, 0))

        expected = normalize_position('C2')
        self.assertEqual(expected, (2, 1))

    def test_lowercase(self):
        """
        Normalize lowercase coordinate strings ('a1')
        """
        expected = normalize_position('c2')
        self.assertEqual(expected, (2, 1))

    def test_multidigit_row(self):
        """
        Multiple digits in the coordinate row ('b222')
        """
        expected = normalize_position('b222')
        self.assertEqual(expected, (1, 221))

    def test_nonletter_colum(self):
        """
        Exception on invalid coordinate string (']1').
        """
        # Make sure the entire valid range works.
        normalize_position('A1')
        normalize_position('Z1')
        # Test out of range (@ and ] are the edges of A-Z in ASCII).
        with self.assertRaises(ValueError):
            normalize_position(']1')
        with self.assertRaises(ValueError):
            normalize_position('@1')

    def test_invalid_coordinate_string(self):
        """
        Exception on invalid coordinate string ('11').
        """
        with self.assertRaises(ValueError):
            normalize_position('11')

    def test_tuple(self):
        """
        Passthrough normalization of 2-member tuple.
        """
        expected = normalize_position((2, 1))
        self.assertEqual(expected, (2, 1))

    def test_short_tuple(self):
        """
        Raise exception on one-member tuple.
        """
        with self.assertRaises(TypeError):
            normalize_position((1))

    def test_long_tuple(self):
        """
        Raise exception on three-member tuple.
        """
        with self.assertRaises(TypeError):
            normalize_position((1, 2, 3))

    def test_mistyped_tuple(self):
        """
        Raise exception on mistyped tuple (char, int).
        """
        with self.assertRaises(TypeError):
            normalize_position(('a', 1))

    def test_well_offsets(self):
        """
        Well offsets.
        """

        # We have a plate map listing offset order.
        cdir = os.path.dirname(os.path.realpath(__file__))
        self.csv_file = os.path.join(
            cdir,
            '../../fixtures/offset_map.csv'
        )
        self.plate_map = PlateMap(self.csv_file)
        plate = self.plate_map.get_plate('A1', rotated=True)

        # Go through every row, col in a standard 96 well plate
        # and check against the documented offset order.
        n = 0
        for col in range(0, 8):
            for row in range(0, 12):
                c = humanize_position((col, row))
                self.assertEqual(int(plate.get_well(c)), n)
                n += 1

    def test_item_group(self):
        """ Item group test (mocked). """
        group = MockGroup([MockItem(i) for i in range(10)])
        added = group.add(2)
        ex1 = [n + 2 for n in range(10)]
        self.assertEqual(ex1, added)
        successor = group.successor
        # Three because we just added two. Two tests in one!
        ex2 = [n + 3 for n in range(10)]
        self.assertEqual(ex2, successor)
        self.assertEqual(group.thing, None)
        self.assertEqual(group.set_thing('hi'), None)
        self.assertEqual(group.thing, ['hi' for _ in range(10)])

    def test_grid_row_group(self):
        """ Grid row acts as group. """
        plate = Microplate()
        plate.col('A').allocate(water=10)
        vols = [plate.well((0, r)).get_volume('water') for r in range(12)]
        self.assertEqual([10 for _ in range(12)], vols)
        self.assertEqual(plate.col('A').get_volume('water'), vols)
        vols = [plate.well((0, r)).get_volume('water') for r in range(12)]
        expected_vols = [15 for _ in range(8)]
        expected_vols[0] += 10  # Remember, we added to the column.
        plate.row(0).allocate(water=15)
        rvols = [plate.well((c, 0)).get_volume('water') for c in range(8)]
        self.assertEqual(plate.row(0).get_volume('water'), expected_vols)
        self.assertEqual(rvols, plate.row(0).get_volume('water'))
        self.assertEqual(plate.row(0).get_volume('water'), rvols)

    def test_address(self):
        """ Address. """
        plate = Microplate()
        self.assertEqual(plate.well('A1').address, [(0, 0)])
        self.assertEqual(plate.well('a1').human_address, 'A1')
        deck = Deck()
        deck.add_module('A1', 'microplate')
        well = deck.slot('A1').well('B4')
        self.assertEqual(well.human_address, 'A1:B4')
        self.assertEqual(well.address, [(0, 0), (1, 3)])
