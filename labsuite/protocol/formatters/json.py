# Copyright 2016 Michelle Steigerwalt

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

        modules = []
        for slot, name in sorted(self._protocol._containers.items()):
            c = OrderedDict([('name', name)])
            label = self._protocol.get_container_label(slot)
            if label:
                c['label'] = label
            if slot:
                c['slot'] = humanize_position(slot)
            modules.append(c)

        instructions = []
        for command in self._protocol.commands:
            command = self._export_command(command)
            instructions.append(command)

        out = OrderedDict()
        out['info'] = info
        out['instruments'] = instruments
        out['containers'] = modules
        out['instructions'] = instructions
        return json.dumps(out, indent=4)

    def _export_command(self, command):
        command = copy.deepcopy(command)
        name = command['command']
        method = getattr(self, "_export_{}_command".format(name), None)
        d = self._export_any_command(command)
        if method:
            return method(d)
        else:
            return d

    def _export_any_command(self, command):
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
        transfers = command.pop('transfers', None)
        for k, v in command.items():
            d[k] = v
        if transfers:
            ts = []
            for t in transfers:
                ts.append(self._export_any_command(t))
            d['transfers'] = ts
        return d

    def _export_mix_command(self, command):
        command['repetitions'] = command.pop('reps')
        return command

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
        self._load_containers(data['containers'])
        self._load_instruments(data['instruments'])
        self._load_instructions(data['instructions'])

    def _load_info(self, info):
        self._protocol.set_info(**info)

    def _load_instruments(self, instruments):
        for k, inst in instruments.items():
            self._protocol.add_instrument(inst['axis'], inst['name'])

    def _load_containers(self, deck):
        for container in deck:
            name = container.get('name', None)
            label = container.get('label', None)
            slot = container.get('slot', None)
            self._protocol.add_container(
                slot, name, label=label
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

    def _load_mix_command(self, inst):
        volume = inst.pop('volume', None)
        inst['ul'] = volume
        start = inst.pop('start')
        self._protocol.mix(start, **inst)

    def _load_transfer_group_command(self, inst):
        transfers = []
        for t in inst.pop('transfers'):
            start = t.pop('start')
            end = t.pop('end')
            t['ul'] = t.pop('volume')
            transfers.append((start, end, t))
        self._protocol.transfer_group(*transfers, tool=inst['tool'])

    def _load_consolidate_command(self, inst):
        transfers = []
        for t in inst.pop('transfers'):
            start = t.pop('start')
            t['ul'] = t.pop('volume')
            transfers.append((start, t))
        self._protocol.consolidate(inst['end'], *transfers, tool=inst['tool'])

    def _load_distribute_command(self, inst):
        transfers = []
        for t in inst.pop('transfers'):
            start = t.pop('end')
            t['ul'] = t.pop('volume')
            transfers.append((start, t))
        self._protocol.distribute(inst['start'], *transfers, tool=inst['tool'])

    @property
    def protocol(self):
        return self._protocol
