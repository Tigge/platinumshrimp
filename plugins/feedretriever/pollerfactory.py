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
        # Look for a specific poller that matches a substring of the URL
        for key, exec_class in cls.registry.items():
            if key != "*" and key in url:
                logging.info(f"Creating poller for {url} matched {key}")
                return exec_class(*args, **kwargs)

        # Fallback to catch-all
        logging.info("Creating poller for " + url + " using catch-all")
        exec_class = cls.registry["*"]
        poller = exec_class(*args, **kwargs)
        return poller
