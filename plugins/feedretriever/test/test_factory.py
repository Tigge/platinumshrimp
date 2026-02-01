import unittest

from plugins.feedretriever.pollerfactory import PollerFactory

POLLER1_NAME = "name_1"
POLLER2_NAME = "name_2"
CATCH_ALL = "*"


@PollerFactory.register(POLLER1_NAME)
class Poller1:
    pass


@PollerFactory.register(CATCH_ALL)
class Poller2:
    pass


class FeedRetriverTest(unittest.TestCase):
    def test_basic_factory(self):
        poller = PollerFactory.create_poller(POLLER1_NAME)
        self.assertTrue(isinstance(poller, Poller1))
        self.assertFalse(isinstance(poller, Poller2))

    def test_factory_catch_all(self):
        poller = PollerFactory.create_poller(POLLER2_NAME)
        self.assertTrue(isinstance(poller, Poller2))
        self.assertFalse(isinstance(poller, Poller1))
