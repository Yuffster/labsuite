# Copyright 2016 Michelle Steigerwalt
# License: Apache 2.0

import json
import copy
from collections import OrderedDict
from labsuite.protocol.formatters import ProtocolFormatter
from labsuite.protocol import Protocol
from labsuite.labware.grid import humanize_position


class JSONFormatter(ProtocolFormatter):

    def export(self):
        info = OrderedDict()
        i = self._protocol.info
        order = ['name', 'author', 'description', 'version', 'version_hash',
                 'created', 'updated']
        for key in order:
            v = i.pop(key, None)
            if v is not None:
                info[key] = v
        instruments = OrderedDict()
        for axis, name in sorted(self._protocol.instruments.items()):
            label = "{}_{}".format(name, axis.lower())
            instruments[label] = OrderedDict([
                ('axis', axis),
                ('name', name)
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
        out['deck'] = modules
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
        for t in command.pop('transfers'):
            transfers.append(self._translate_any_command(t))
        o = OrderedDict([
            ('command', command.pop('command')),
            ('tool', command.pop('tool'))
        ])
        for k, v in sorted(command.items()):
            o[k] = v
        o['transfers'] = transfers
        return o

    def convert(self, content):
        """
        Takes a JSON string and returns a protocol.
        """
        return self._protocol


class JSONLoader():

    _protocol = None

    def __init__(self, json_str):
        data = json.loads(json_str)
        self._protocol = Protocol()
        self._load_info(data['info'])
        self._load_deck(data['deck'])
        self._load_instruments(data['instruments'])
        self._load_instructions(data['instructions'])

    def _load_info(self, info):
        self._protocol.set_info(**info)

    def _load_instruments(self, instruments):
        for k, inst in instruments.items():
            self._protocol.add_instrument(inst['axis'], inst['name'])

    def _load_deck(self, deck):
        for slot, mod in deck.items():
            self._protocol.add_container(
                slot, mod['name'], label=mod.get('label', None)
            )

    def _load_instructions(self, instructions):
        for i in copy.deepcopy(instructions):
            command = i.pop('command')
            meth = getattr(self, '_load_{}_command'.format(command), None)
            if meth is None:
                raise KeyError("Can't unpack command: {}".format(command))
            meth(i)

    def _load_transfer_command(self, inst):
        volume = inst.pop('volume', None)
        inst['ul'] = volume
        start = inst.pop('start')
        end = inst.pop('end')
        self._protocol.transfer(start, end, **inst)

    def _load_transfer_group_command(self, inst):
        transfers = []
        for t in inst.pop('transfers'):
            start = t.pop('start')
            end = t.pop('end')
            t['ul'] = t.pop('volume')
            transfers.append((start, end, t))
        self._protocol.transfer_group(*transfers, tool=inst['tool'])

    @property
    def protocol(self):
        return self._protocol
