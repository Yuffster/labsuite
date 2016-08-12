# Copyright 2016 Michelle Steigerwalt
# License: Apache 2.0

import unittest
import json
from string import Template
from labsuite.protocol.formatters.json import JSONFormatter, JSONLoader
from labsuite.protocol import Protocol


class ProtocolFormatterTest(unittest.TestCase):

    json = Template("""
    {
        "info": {
            "name": "Test Protocol",
            "author": "Michelle Steigerwalt",
            "description": "A protocol to test JSON output.",
            "created": "Thu Aug 11 20:19:55 2016",
            "updated": "$updated"
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
    """)

    def setUp(self):
        self.protocol = Protocol()

    def testJSON(self):
        self.protocol.set_info(
            name="Test Protocol",
            description="A protocol to test JSON output.",
            author="Michelle Steigerwalt",
            created="Thu Aug 11 20:19:55 2016"
        )
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
        i = self.protocol.info
        result = self.protocol.export(JSONFormatter)
        expected = self.json.substitute(updated=i['updated'])
        self.assertEqual(json.loads(expected), json.loads(result))

    def testInvalidJSON(self):
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96', label="Ingredients")
        self.protocol.add_container('B1', 'microplate.96')
        self.protocol.transfer('A1:A1', 'B1:B1', ul=10, tool='p10')
        with self.assertRaises(KeyError):
            self.protocol.export(JSONFormatter, validate_run=True)

    def testLoadJSON(self):
        start = self.json.substitute(updated="")
        f = JSONLoader(self.json.substitute(updated=""))
        dump = f.protocol.export(JSONFormatter)
        result = json.loads(dump)
        expected = json.loads(start)
        expected['info']['created'] = ""
        expected['info']['updated'] = ""
        result['info']['created'] = ""
        result['info']['updated'] = ""
        self.assertEqual(expected, result)  # ✨  OMG isomorphic! ✨
