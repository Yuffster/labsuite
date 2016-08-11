# Copyright 2016 Michelle Steigerwalt
# License: Apache 2.0

import unittest
import json
from string import Template
from labsuite.protocol.formatters import JSONFormatter
from labsuite.protocol import Protocol


class ProtocolFormatterTest(unittest.TestCase):

    def setUp(self):
        self.protocol = Protocol()

    def testJSON(self):
        self.protocol.set_info(
            name="Test Protocol",
            description="A protocol to test JSON output.",
            author="Michelle Steigerwalt"
        )
        self.protocol.add_instrument('A', 'p10')
        self.protocol.add_container('A1', 'microplate.96', label="Ingredients")
        self.protocol.add_container('B1', 'microplate.96')
        self.protocol.transfer('A1:A1', 'B1:B1', ul=10, tool='p10')
        self.protocol.transfer_group(
            ('A3:A3', 'B3:B3', {'ul': 3}),
            ('A4:A4', 'B4:B4'),
            ('A1:A5', 'B5:C1'),
            tool='p10'
        )
        i = self.protocol.info
        result = self.protocol.export(JSONFormatter)
        expected = Template("""
        {
            "info": {
                "name": "Test Protocol",
                "author": "Michelle Steigerwalt",
                "description": "A protocol to test JSON output.",
                "created": "$created",
                "updated": "$updated"
            },
            "instruments": {
                "p10_a": {
                    "axis": "A",
                    "type": "p10"
                }
            },
            "modules": {
                "A1": "microplate.96",
                "B1": "microplate.96"
            },
            "instructions": [
                {
                    "command": "transfer",
                    "start": "A1:A1",
                    "end": "B1:B1",
                    "volume": 10,
                    "tool": "p10",
                    "blowout": true,
                    "touchtip": true
                },
                {
                    "command": "transfer_group",
                    "transfers": [
                        {
                            "start": "A3:A3",
                            "end": "B3:B3",
                            "volume": 3,
                            "blowout": true,
                            "touchtip": true
                        },
                        {
                            "start": "A4:A4",
                            "end": "B4:B4",
                            "blowout": true,
                            "touchtip": true
                        },
                        {
                            "start": "A1:A5",
                            "end": "B5:C1",
                            "blowout": true,
                            "touchtip": true
                        }
                    ]
                }
            ]
        }
        """).substitute(created=i['created'], updated=i['updated'])
        self.assertEqual(json.loads(expected), json.loads(result))
