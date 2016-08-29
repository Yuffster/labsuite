import unittest
from labsuite.protocol import Protocol
from labsuite.util import exceptions as x


class ContextHandlerTest(unittest.TestCase):

    def setUp(self):
        self.protocol = Protocol()

    def assertVolume(self, well, volume):
        result = self.protocol._context_handler.get_volume(well)
        self.assertEqual(volume, result)

    def test_transfer(self):
        """ Maintain well volumes during transfers. """
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_container('C1', 'tiprack.p200')
        self.protocol.add_instrument('A', 'p200')
        self.protocol.calibrate('A1', x=1, y=2, z=3)
        self.assertVolume('A1:A2', 0)
        self.protocol.transfer('A1:A1', 'A1:A2', ul=100)
        self.assertVolume('A1:A2', 100)
        self.protocol.transfer('A1:A2', 'A1:A3', ul=20)
        self.assertVolume('A1:A3', 20)
        self.assertVolume('A1:A2', 80)
        
        run = self.protocol.run()
        next(run)  # Yield to set progress.
        self.assertVolume('A1:A2', 0)
        next(run)  # transfer('A1:A1', 'A1:A2', ul=100)
        self.assertVolume('A1:A2', 100)
        next(run)  # transfer('A1:A2', 'A1:A3', ul=20)
        self.assertVolume('A1:A3', 20)
        self.assertVolume('A1:A2', 80)

    def test_distribute(self):
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_container('C1', 'tiprack.p200')
        self.protocol.add_instrument('A', 'p200')
        self.protocol.distribute(
            'A1:A1',
            ('A1:B1', {'ul': 50}),
            ('A1:C1', {'ul': 30}),
            ('A1:D1', {'ul': 40})
        )
        # Final volumes.
        self.assertVolume('A1:A1', -120)
        self.assertVolume('A1:B1', 50)
        self.assertVolume('A1:C1', 30)
        self.assertVolume('A1:D1', 40)
        
        # Try during a run.
        run = self.protocol.run()
        next(run)  # Yield to set progress.
        self.assertVolume('A1:A2', 0)
        next(run)  # Our command.

        # Final volumes
        self.assertVolume('A1:A1', -120)
        self.assertVolume('A1:B1', 50)
        self.assertVolume('A1:C1', 30)
        self.assertVolume('A1:D1', 40)

    def test_consolidate(self):
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_instrument('A', 'p200')
        self.protocol.consolidate(
            'A1:A1',
            ('A1:B1', {'ul': 50}),
            ('A1:C1', {'ul': 30}),
            ('A1:D1', {'ul': 40})
        )
        self.assertVolume('A1:A1', 120)
        self.assertVolume('A1:B1', -50)
        self.assertVolume('A1:C1', -30)
        self.assertVolume('A1:D1', -40)

    def test_transfer_group(self):
        self.protocol.add_container('A1', 'microplate.96')
        self.protocol.add_container('C1', 'tiprack.p200')
        self.protocol.add_instrument('A', 'p200')
        self.protocol.transfer_group(
            ('A1:A1', 'A1:B1', {'ul': 50}),
            ('A1:A1', 'A1:C1', {'ul': 50}),
            ('A1:A1', 'A1:D1', {'ul': 30}),
            tool='p200'
        )
        self.assertVolume('A1:A1', -130)
        self.assertVolume('A1:B1', 50)
        self.assertVolume('A1:C1', 50)
        self.assertVolume('A1:D1', 30)

    def test_find_instrument_by_volume(self):
        """ Find instrument by volume. """
        self.protocol.add_instrument('A', 'p10')
        i = self.protocol._context_handler.get_instrument(volume=6)
        self.assertEqual(i.supports_volume(6), True)
        j = self.protocol._context_handler.get_instrument(volume=50)
        self.assertEqual(j, None)
        self.protocol.add_instrument('B', 'p200')
        k = self.protocol._context_handler.get_instrument(volume=50)
        self.assertEqual(k.name, 'p200')

    def test_tip_coordinates(self):
        """ Return tip coordinates. """
        context = self.protocol._context_handler
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_instrument('B', 'p10')
        self.protocol.add_container('B1', 'tiprack.p200')
        self.protocol.calibrate('B1', axis="A", x=100, y=150, top=60)
        self.protocol.add_container('A1', 'tiprack.p10')
        self.protocol.calibrate('A1', axis="B", x=200, y=250, top=160)

        p200 = context.get_instrument(axis='A')
        p10 = context.get_instrument(axis='B')

        c1 = context.get_next_tip_coordinates(p200)
        self.assertEqual(c1, {'x': 100, 'y': 150, 'top': 60, 'bottom': 0})
        c2 = context.get_next_tip_coordinates(p200)  # Next tip.
        self.assertEqual(c2, {'x': 100, 'y': 159, 'top': 60, 'bottom': 0})

        c3 = context.get_next_tip_coordinates(p10)
        self.assertEqual(c3, {'x': 200, 'y': 250, 'top': 160, 'bottom': 0})
        c4 = context.get_next_tip_coordinates(p10)  # Next tip.
        self.assertEqual(c4, {'x': 200, 'y': 259, 'top': 160, 'bottom': 0})

    def test_tiprack_switch(self):
        """ Return second tiprack when first is used up. """
        context = self.protocol._context_handler
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_container('B1', 'tiprack.p200')
        self.protocol.calibrate('B1', axis="A", x=100, y=150, top=60)
        self.protocol.add_container('A1', 'tiprack.p200')
        self.protocol.calibrate('A1', axis="A", x=200, y=250, top=160)
        p200 = context.get_instrument(axis='A')
        rack = context.find_container(name='tiprack.p200', has_tips=True)
        self.assertEqual([(0, 0)], rack.address)
        rack.set_tips_used(95)  # We've used all but one tip from this rack.
        c1 = context.get_next_tip_coordinates(p200)  # Last tip.
        h12 = [(0, 0), (7, 11)]
        self.assertEqual(c1, context.get_coordinates(h12, axis="A"))
        rack = context.find_container(name='tiprack.p200', has_tips=True)
        self.assertEqual([(1, 0)], rack.address)

    def test_multichannel_search(self):
        """ Find a multichannel pipette. """
        context = self.protocol._context_handler
        self.protocol.add_instrument('A', 'p200')
        self.protocol.add_instrument('B', 'p20.12')
        i1 = context.get_instrument(axis='B')
        i2 = context.get_instrument(volume=20, channels=12)
        self.assertEqual(i1, i2)
        i3 = context.get_instrument(volume=200, channels=12)
        self.assertEqual(i3, None)

    def test_multichannel_tip_allocation(self):
        context = self.protocol._context_handler
        self.protocol.add_instrument('A', 'p20.12')
        self.protocol.add_instrument('B', 'p20.8')
        self.protocol.add_container('A1', 'tiprack.p20')
        a = context.get_instrument(axis='A')
        b = context.get_instrument(axis='B')
        self.protocol.calibrate('A1', axis="A")
        self.protocol.calibrate('A1', axis="B")
        # Get a row first.
        context.get_next_tip_coordinates(a)
        with self.assertRaises(x.TipMissing):
            context.get_next_tip_coordinates(b)
        # Get a col first.
        context = self.protocol.initialize_context()
        context.get_next_tip_coordinates(b)
        with self.assertRaises(x.TipMissing):
            context.get_next_tip_coordinates(a)
        # Add another tiprack, get both!
        self.protocol.add_container('A2', 'tiprack.p20')
        self.protocol.calibrate('A2', axis="A")
        self.protocol.calibrate('A2', axis="B")
        context = self.protocol.initialize_context()
        context.get_next_tip_coordinates(a)
        context.get_next_tip_coordinates(b)
        # Exhaust the supply.
        context = self.protocol.initialize_context()
        for _ in range(8):
            context.get_next_tip_coordinates(a)
        for _ in range(12):
            context.get_next_tip_coordinates(b)
        with self.assertRaises(x.TipMissing):
            context.get_next_tip_coordinates(a)
        with self.assertRaises(x.TipMissing):
            context.get_next_tip_coordinates(b)

    def test_multichannel_transfer_cols(self):
        """ Test multichannel transfer (cols). """
        self.protocol.add_instrument('A', 'p20.12')
        self.protocol.add_instrument('B', 'p20.8')
        self.protocol.add_container('A1', 'microplate')
        p = self.protocol._context_handler.find_container(name="microplate")
        self.protocol.transfer('A1:A1', 'A1:B1', ul=10, tool='p20.12')
        self.assertEqual(p.col('A').get_volume(), [-10 for n in range(12)])
        self.assertEqual(p.col('B').get_volume(), [ 10 for n in range(12)])

    def test_multichannel_transfer_rows(self):
        """ Test multichannel transfer (rows). """
        self.protocol.add_instrument('A', 'p20.12')
        self.protocol.add_instrument('B', 'p20.8')
        self.protocol.add_container('A1', 'microplate')
        p = self.protocol._context_handler.find_container(name="microplate")
        self.protocol.transfer('A1:A1', 'A1:A2', ul=15, tool='p20.8')
        self.assertEqual(p.row(0).get_volume(), [-15 for n in range(8)])
        self.assertEqual(p.row(1).get_volume(), [ 15 for n in range(8)])

