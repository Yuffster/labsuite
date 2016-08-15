"""
This script takes a 15 nucleotide target sequence followed by a base pair
representing the receiver plasmid.

It outputs an OT-One protocol to assemble a TALEN protein with the pFusX
system, which provides a pre-plated library of plasmids and a database
of well positions for this script to query.

Input is a string representing an RVD sequence, whitespace optional,
such as:

> NI NG NI HD HD NN NG HD NG NG NI NG NG NG NG

Or DNA, such as:

> ATACCGTCTTATTTT

Output is a JSON file which represents a protocol that can run on any
OT-One machine.
"""

import sys
import os
import re
import json
import datetime

from labsuite.protocol import Protocol
from labsuite.protocol.formatters import JSONFormatter

from .plate_map import PlateMap

_fusx_plates = PlateMap(
    os.path.dirname(__file__) + '/data/fusx_platemap.csv',
    rotated=True,
    TALE1='A33',
    TALE2='K33',
    TALE3='U33',
    TALE4='A48',
    TALE5='K48'
)


def dna_to_rvd(string):
    """
    Translates a DNA string to RVD.
    """
    translation = {
        'A': 'NI',
        'C': 'HD',
        'T': 'NG',
        'G': 'NN',
        'R': 'NN'  # Just assume G if purine is unspecified.
    }
    string = string.upper()
    rvd = []
    for c in string:
        if c is 'Y':
            # Apparently for restriction enzymes pyridians need to be more
            # specific than purines.
            raise ValueError(
                "Invalid base: 'Y'; pyrimidines must be specified."
            )
        elif c not in translation:
            raise ValueError("Invalid character: {}".format(c))
        else:
            rvd.append(translation[c])
    return ' '.join(rvd)


def rvd_to_tal(string):
    """
    Translates an RVD string into TAL.

    Very similar to a reverse of dna_to_rvd, but DNA->RVD2->TAL2 will return
    a normalized result rather than the original input.
    """
    translation = {
        'NI': 'A',
        'HD': 'C',
        'NG': 'T',
        'NN': 'G'
    }
    out = []
    string = string.upper()  # Convert input to uppercase;
    string = re.sub(r'[^A-Z]+', '', string)  # remove any separators.
    codes = map(''.join, zip(*[iter(string)] * 2))  # Two-character segments.
    for code in codes:
        if code not in translation:
            raise ValueError("Invalid RVD sequence: {}".format(code))
        else:
            out.append(translation[code])
    return ''.join(out)


def tal_to_codons(tal):
    """
    Takes a 15 or 16-base ATGC sequence and outputs an array of five
    codon sequences after doing validation.
    """
    if re.match(r'[^ACTG]]', tal):  # Content check.
        raise ValueError("FusX TALEN sequence must be in ACTG form.")
    codons = []
    for n in range(0, 12, 3):  # Chunk into four parts of 3.
        codons.append(tal[n:n + 3])
    codons.append(tal[12:])  # Grab the last 2, 3 or 4 bases.
    return codons


def get_plasmid_wells(sequence, receiver='pC'):
    """
    Takes a string of either RVD or DNA basepairs (15 or 16), does a
    bunch of input normalization and outputs a hash containing well
    positions for pfusx_[1..5], receiver, and backbone.

    No plate data is necessary at the moment; those are hard-coded in the
    template.
    """

    tal = rvd_to_tal(sequence)  # Normalize the sequence.

    codons = tal_to_codons(tal[0:-1])
    pLR_bp = tal[-1]  # Last base is the receiver.

    if len(codons) != 5:
        raise ValueError("Sequence must be an array of five codons.")

    # We only actually need well coordinates for these because the plate
    # names are hard-coded into the pFusX JSON template.
    well_locs = {}

    # We pull the FusX plasmid locations from the plate map, five in total.
    for i, codon in enumerate(codons):
        codon_index = i + 1
        plate_name = 'TALE{}'.format(codon_index)
        location = _fusx_plates.get_plate(plate_name).find_well(codon)
        if not location:
            raise ValueError(
                "Can't find well position for '{}' on plate {}.".
                format(codon, plate_name)
            )
        else:
            well_locs[plate_name] = location

    plate = _fusx_plates.get_plate('TALE5')
    well_locs['pLR'] = plate.find_well('pLR: {}'.format(pLR_bp))
    if not well_locs['pLR']:
        raise ValueError("Invalid pLR: {}".format(pLR_bp))

    valid_receivers = ['pT3TS', 'pC', 'pKT3']
    if receiver not in valid_receivers:
        raise ValueError(
            "Receiver must be one of: {}"
            .format(", ".join(valid_receivers))
        )

    rec_well = plate.find_well(receiver)
    if not rec_well:
        # No way to really test this bit without adding an invalid
        # receiver that doesn't exist in the plate mapping...
        raise ValueError(
            "Can't find receiver well for '{}'.".
            format(receiver)
        )
    well_locs['receiver'] = rec_well

    return well_locs


def _get_tal_transfers(sequence, well='A1', receiver='pC'):
    """
    Creates an array of transfer arguments for a TAL sequence.
    """

    output_well = "FusX Output:{}".format(well)
    plasmids = get_plasmid_wells(sequence, receiver)

    # TAL Plasmid transfers
    tals = []
    for n in range(1, 6):  # TALEN plasmids, 1 through 5
        tals.append(
            (
                "TALE{}:{}".format(n, plasmids['TALE{}'.format(n)]),
                output_well,
                3
            )
        )

    # pLR and Receiver transfers
    pLR = [('TALE5:{}'.format(plasmids['pLR']), output_well, 3)]
    receiver = [('TALE5:{}'.format(plasmids['receiver']), output_well, 3)]

    return tals + pLR + receiver


def _normalize_sequence(sequence):
    """
    Validate and normalize input sequences to RVD.
    """

    # Uppercase; no separators, A-Z only.
    sequence = sequence.upper()
    sequence = re.sub(r'[^A-Z]+', '', sequence)

    # Normalize to RVD input.
    if re.match(r'^[ATGCYR]*$', sequence):  # Match: DNA bases.
        sequence = re.sub('\s', '', dna_to_rvd(sequence))
    elif re.match(r'^[NIHDG]*$', sequence):  # Match: RVD bases.
        sequence = sequence
    else:
        raise ValueError("Input must be a sequence of RVD or DNA bases.")

    if len(sequence) not in [32, 30]:
        raise ValueError("Sequence must be 15 RNA or DNA bases.")

    return sequence


def compile(*sequences, output=None):
    """
    Takes a list of sequence arguments (RVD or DNA) and outputs a generated
    protocol to make plasmids targetting those sequences.
    """
    sequences = list(sequences)

    # Limit right now is the number of tips in the static deck map we're
    # using for this protocol.
    if len(sequences) > 15:
        raise ValueError(
            "FusX compiler only supports up to 15 sequences."
        )

    # Argument normalization.
    normalized = []
    for i, s in enumerate(sequences):
        try:
            normalized.append(_normalize_sequence(s))
        except ValueError as e:
            raise ValueError("Sequence #{}: {}".format(i + 1, e))

    # Make the transfers for every sequence.
    buffers = []
    tals = []
    enzymes = []

    well_map = {}
    for n, s in enumerate(normalized):
        n = n + 1
        if n > 12:
            well = 'B{}'.format(n - 12)
        else:
            well = 'A{}'.format(n)
        # We're going to do all the buffers at the start...
        buffers += [('Ingredients:A1', 'FusX Output:' + well, 10)]
        # TALs in the middle...
        tals += _get_tal_transfers(s, well=well)
        # Enzyme (BsmBI) at the end.
        enzymes += [("Ingredients:B1", 'FusX Output:' + well, 10)]
        # For printing an output map.
        well_map[well] = sequences[n - 1]  # Map to original input.

    # Nicely formatted well map for the description.
    output_map = []
    for well in sorted(well_map):
        output_map.append("{}: {}".format(well, well_map[well]))

    protocol = Protocol()
    protocol.set_info(
        name="FusX Transfer",
        created=str(datetime.date.today()),
        description="; ".join(output_map)
    )
    protocol.add_instrument('A', 'p10')
    protocol.add_instrument('B', 'p200')
    protocol.add_container('A1', 'tuberack.15-50ml', label='Ingredients')
    protocol.add_container('E1', 'microplate.96', label='Fusx Output')
    protocol.add_container('A2', 'point.trash')
    protocol.add_container('E3', 'microplate.96') # Cool deck.
    protocol.add_container('B2', 'tiprack.p10')
    protocol.add_container('B1', 'tiprack.p10')
    protocol.add_container('B3', 'tiprack.p10')
    protocol.add_container('C1', 'microplate.96', label='TALE1')
    protocol.add_container('D1', 'microplate.96', label='TALE2')
    protocol.add_container('C2', 'microplate.96', label='TALE3')
    protocol.add_container('D2', 'microplate.96', label='TALE4')
    protocol.add_container('C3', 'microplate.96', label='TALE5')

    # Take our three transfer groups and make them into a consolidated
    # transfer list.

    # Buffers
    group = []
    for start, end, volume in buffers:
        group.append((start, end, {'ul': volume}))
    protocol.transfer_group(*group, tool="p10")

    # TALS
    for start, end, volume in tals:
        protocol.transfer((start, end, {'ul': volume}))

    # Enzymes
    for start, end, volume in enzymes:
        protocol.transfer(start, end, ul=volume)

    compiled = protocol.export(JSONFormatter)

    if output:
        with open(output, 'w') as f:
            f.write(compiled)

    return compiled
