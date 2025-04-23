from abc import ABCMeta, abstractmethod

import logging


class PollerBase(metaclass=ABCMeta):
    def __init__(self, feed, on_created, on_entry, on_error):
        pass

    @abstractmethod
    def force_update(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def reset_latest(self):
        pass


# This factory allows for costimized pollers so that e.g. different parsers can be used.
#
# Register new pollers by adding @FeedpollerFactory.register(url) above your poller
# class definition.
#
# Fetch/create a poller by calling the create_poller method with the given url.
# We use a "*" as a catch-all for RSS feeds.
class PollerFactory:
    registry = {}

    @classmethod
    def register(cls, url):
        def inner_wrapper(wrapped_class: PollerBase):
            cls.registry[url] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def create_poller(cls, url, *args, **kwargs):
        if url not in cls.registry:
            url = "*"
        logging.info("Creating poller for " + url)
        exec_class = cls.registry[url]
        poller = exec_class(*args, **kwargs)
        return poller
