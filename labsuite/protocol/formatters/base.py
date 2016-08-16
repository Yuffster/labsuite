# Copyright 2016 Michelle Steigerwalt

from labsuite.protocol import Protocol


class ProtocolFormatter():

    _protocol = None  # The protocol.

    def __init__(self, protocol=None):
        if protocol:
            self._protocol = protocol
        else:
            self._protocol = Protocol()

    def export(self):
        """
        Exports the content for this particular format based on the provided
        Protocol (passed in at initialization).
        """
        return ""

    def ingest(self, content):
        """
        Ingests the content for this particular format and returns a Protocol
        instance.
        """
        return self._protocol
