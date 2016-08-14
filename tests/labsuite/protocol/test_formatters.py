# Copyright 2016 Michelle Steigerwalt
# License: Apache 2.0

import unittest
import json
from string import Template
from labsuite.protocol.formatters.json import JSONFormatter, JSONLoader
from labsuite.protocol import Protocol
from labsuite.util.exceptions import *


class ProtocolFormatterTest(unittest.TestCase):

    json = """
    {
        "info": {
            "name": "Test Protocol",
            "author": "Michelle Steigerwalt",
            "description": "A protocol to test JSON output.",
            "created": "Thu Aug 11 20:19:55 2016",
            "updated": ""
        },
        "instruments": {
            "p10_a": {
                "axis": "A",
                "name": "p10"
            }
        },
        "deck": {
            "A1": {
                "name": "microplate.96",
                "label": "Ingredients"
            },
            "B1": {
                "name": "microplate.96",
                "label": "Output"
            }
        },
        "instructions": [
            {
                "command": "transfer",
                "start": "Ingredients:A1",
                "end": "Output:B1",
                "volume": 10,
                "tool": "p10",
                "blowout": true,
                "touchtip": true
            },
            {
                "command": "transfer_group",
                "tool": "p10",
                "transfers": [
                    {
                        "start": "Ingredients:A3",
                        "end": "Output:B3",
                        "volume": 3,
                        "blowout": true,
                        "touchtip": true
                    },
                    {
                        "start": "Ingredients:A4",
                        "end": "Output:B4",
                        "volume": 10,
                        "blowout": true,
                        "touchtip": true
                    },
                    {
                        "start": "Ingredients:A5",
                        "end": "Output:C1",
                        "volume": 10,
                        "blowout": true,
                        "touchtip": true
                    }
                ]
            }
        ]
    }
    """

    def setUp(self):
        self.protocol = Protocol()
        self.stub_info = {
            'name': "Test Protocol",
            'description': "A protocol to test JSON output.",
            'author': "Michelle Steigerwalt",
            'created': "Thu Aug 11 20:19:55 2016"
        }
        # Same definitions as the protocol JSON above.
        self.protocol.set_info(**self.stub_info)
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96', label="Ingredients")
        self.protocol.add_container('B1', 'microplate.96', label="Output")
        self.protocol.transfer('A1:A1', 'B1:B1', ul=10, tool='p10')
        self.protocol.transfer_group(
            ('A1:A3', 'B1:B3', {'ul': 3}),
            ('INGREDIENTS:A4', 'B1:B4'),
            ('A1:A5', 'B1:C1'),
            tool='p10',
            ul=10
        )

    def test_json_export(self):
        result = json.loads(self.protocol.export(JSONFormatter))
        expected = json.loads(self.json)
        self.assertEqual(self.protocol.version, '0.0.1')
        for k, v in self.stub_info.items():
            self.assertEqual(v, result['info'][k])
        self.assertEqual(result["info"]["version"], self.protocol.version)
        self.assertEqual(result["info"]["version_hash"], self.protocol.hash)
        expected['info'] = ""
        result['info'] = ""
        self.assertEqual(expected, result)

    def test_invalid_json(self):
        with self.assertRaises(MissingContainer):
            # This fails because there's no tiprack or trash.
            self.protocol.export(JSONFormatter, validate_run=True)

    def test_load_json(self):
        start = self.json
        f = JSONLoader(self.json)
        dump = f.protocol.export(JSONFormatter)
        result = json.loads(dump)
        expected = json.loads(start)
        expected['info'] = ""
        result['info'] = ""
        self.assertEqual(expected, result)  # ✨  OMG isomorphic! ✨

    def test_equal_hashing(self):
        p = JSONLoader(self.json).protocol
        # Hashes of all protocol run-related data within the JSON and manually
        # defined protcol are equal.
        self.assertEqual(self.protocol, p)
        # Make a modification of the original protocol.
        p.add_instrument('B', 'p20')
        # Hashes are different.
        self.assertNotEqual(self.protocol, p)
