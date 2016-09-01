import unittest
from labsuite.compilers import pfusx
import json


class PFUSXTest(unittest.TestCase):

    def test_dna_to_rvd(self):
        """
        Translate DNA to RVD pairs.
        """
        expected = 'NI NG NI HD HD NN NG HD NG NG NI NG NG NG NG'
        rvd = pfusx.dna_to_rvd('ATACCGTCTTATTTT')
        self.assertEqual(rvd, expected)

    def test_dna_to_rvd_allow_unspecified_purine(self):
        """
        Translate DNA to RVD pairs with unspecified purines.
        """
        expected = 'NI NG NI HD HD NN NG HD NG NG NI NG NG NG NG'
        rvd = pfusx.dna_to_rvd('ATACCRTCTTATTTT')
        self.assertEqual(rvd, expected)

    def test_dna_to_rvd_disallow_unspecified_pyrimidines(self):
        """
        Translate DNA to RVD pairs only with specified pyrimidines.
        """
        with self.assertRaises(ValueError):
            pfusx.dna_to_rvd('AYACCGTCTTATTTT')

    def test_dna_to_rvd_invalid_character(self):
        """
        Translate DNA to RCD pairs, minus invalid characters.
        """
        with self.assertRaises(ValueError):
            pfusx.dna_to_rvd('AXACCGTCTTATTTT')

    def test_rvd_to_tal(self):
        """
        Translate RVD2 to TAL2.
        """

        # Various input formats.
        stripped = 'NIHDNGNNNN'
        slashes = 'NI/HD/NG/NN/NN'
        spaces = 'NI HD NG NN NN'
        dashes = 'NI-HD-NG-NN-NN'
        commas = 'NI,HD,NG,NN,NN'
        space_commas = 'NI, HD, NG, NN, NN'

        # Uniform output.
        expected = 'ACTGG'

        self.assertEqual(pfusx.rvd_to_tal(stripped), expected)
        self.assertEqual(pfusx.rvd_to_tal(slashes), expected)
        self.assertEqual(pfusx.rvd_to_tal(spaces), expected)
        self.assertEqual(pfusx.rvd_to_tal(dashes), expected)
        self.assertEqual(pfusx.rvd_to_tal(commas), expected)
        self.assertEqual(pfusx.rvd_to_tal(space_commas), expected)

    def test_rvd_invalid_input(self):
        """
        Don't accept invalid RVD sequences.
        """
        with self.assertRaises(ValueError):
            pfusx.rvd_to_tal("This is not valid input.")
        with self.assertRaises(ValueError):
            pfusx.rvd_to_tal("atatatagatataga")  # DNA and not RVD

    def test_tal_sequence(self):
        """
        Segment TAL sequence.
        """
        result = pfusx.tal_to_codons('ATACCRTCTTATTT')
        expected = ['ATA', 'CCR', 'TCT', 'TAT', 'TT']
        self.assertEqual(result, expected)

    def test_invalid_tal_sequence(self):
        with self.assertRaises(ValueError):
            pfusx.tal_to_codons('HELLO :)')

    def test_tal_sequence_sixteen(self):
        """
        Segment 16-character TAL sequence.
        """
        result = pfusx.tal_to_codons('ATACCRTCTTATTTA')
        expected = ['ATA', 'CCR', 'TCT', 'TAT', 'TTA']
        self.assertEqual(result, expected)

    def test_well_locations(self):
        target = 'NI NG NI HD HD NN NG HD NG NG NI NG NG NG NG'
        result = pfusx.get_plasmid_wells(target)

        expected = {
            'TALE1': 'E2',
            'TALE2': 'G3',
            'TALE3': 'H7',
            'TALE4': 'D7',
            'TALE5': 'H10',
            'pLR': 'D11',
            'receiver': 'B12'
        }
        self.assertEqual(result, expected)

    def test_large_well_sequence(self):
        target = 'NI NG NI HD HD NN NG HD NG HD NI NG NI NG NG NG NG NG'
        with self.assertRaises(ValueError):
            pfusx.get_plasmid_wells(target)

    def test_tal_transfers(self):
        """
        Construct TAL transfers.
        """

        seq = 'NI NG NI HD HD NN NG HD NG NG NI NG NG NG NG'
        result = pfusx._get_tal_transfers(seq, well='B2')

        expected = [
            ('TALE1:E2', 'FusX Output:B2', 3),
            ('TALE2:G3', 'FusX Output:B2', 3),
            ('TALE3:H7', 'FusX Output:B2', 3),
            ('TALE4:D7', 'FusX Output:B2', 3),
            ('TALE5:H10', 'FusX Output:B2', 3),
            ('TALE5:D11', 'FusX Output:B2', 3),  # pLR
            ('TALE5:B12', 'FusX Output:B2', 3)  # Receiver
        ]

        self.assertEqual(expected, result)

    def test_invalid_receiver(self):
        seq = 'NI NG NI HD HD NN NG HD NG NG NI NG NG NG NG'
        with self.assertRaises(ValueError):
            pfusx._get_tal_transfers(seq, well='B2', receiver="foo")

    def test_compile_dna(self):
        """
        Should compile single DNA sequence.
        """
        text = pfusx.compile('ATACCGTCTTATTTT')
        json.loads(text)

    def test_compile_multi_dna(self):
        """
        Should compile multiple DNA sequences.
        """
        text = pfusx.compile('ATACCGTCTTATTTT', 'ATACCGTCTTATTTA')
        json.loads(text)

    def test_compile_short_dna_input(self):
        """
        Compiler should return error on short input.
        """
        with self.assertRaises(ValueError):
            pfusx.compile('GATTACA')

    def test_compile_invalid_sequence(self):
        """
        Compiler validates input.
        """
        with self.assertRaises(ValueError):
            pfusx.compile("Cats with laser eyes.")

    def test_compile_dna_rvd_mix(self):
        """
        Compile DNA and RVD mixture.
        """
        text = pfusx.compile(
            'NI NN NN NN HD NG NI NI NG NN NI NG NI NN NG',
            'ATACCGTCTTATTTT'
        )
        json.loads(text)
