# Copyright 2016 Michelle Steigerwalt
# License: Apache 2.0

import json
import copy
from collections import OrderedDict
from labsuite.protocol.formatters import ProtocolFormatter
from labsuite.labware.grid import humanize_position


class JSONFormatter(ProtocolFormatter):

    def export(self):
        info = OrderedDict()
        i = self._protocol.info
        order = ['name', 'author', 'description', 'created', 'updated']
        for key in order:
            v = i.pop(key, None)
            if v is not None:
                info[key] = v
        instruments = OrderedDict()
        for axis, name in sorted(self._protocol.instruments.items()):
            label = "{}_{}".format(name, axis.lower())
            instruments[label] = OrderedDict([
                ('axis', axis),
                ('type', name)
            ])
        modules = OrderedDict()
        for slot, name in sorted(self._protocol._containers.items()):
            c = OrderedDict([('name', name)])
            modules[humanize_position(slot)] = c
            label = self._protocol.get_container_label(slot)
            if label:
                c['label'] = label
        instructions = []
        for command in self._protocol.commands:
            command = self._translate_command(command)
            instructions.append(command)
        out = OrderedDict()
        out['info'] = info
        out['instruments'] = instruments
        out['modules'] = modules
        out['instructions'] = instructions
        return json.dumps(out, indent=4)

    def _translate_command(self, command):
        command = copy.deepcopy(command)
        name = command['command']
        method = getattr(self, "_translate_{}".format(name), None)
        d = self._translate_any_command(command)
        if method:
            return method(d)
        else:
            return d

    def _translate_any_command(self, command):
        if 'start' in command:
            s = self._protocol.humanize_address(command['start'])
            command['start'] = s
        if 'end' in command:
            e = self._protocol.humanize_address(command['end'])
            command['end'] = e
        d = OrderedDict()
        order = ['command', 'start', 'end', 'volume', 'tool']
        for key in order:
            v = command.pop(key, None)
            if v is not None:
                d[key] = v
        for k, v in command.items():
            d[k] = v
        return d

    def _translate_transfer_group(self, command):
        transfers = []
        for t in command['transfers']:
            transfers.append(self._translate_any_command(t))
        return OrderedDict([
            ('command', command['command']),
            ('transfers', transfers)
        ])

    def convert(self, content):
        """
        Takes a JSON string and returns a protocol.
        """
        return self._protocol
