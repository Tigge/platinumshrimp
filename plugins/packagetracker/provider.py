import datetime


class Package:
    class Event:
        def __init__(self):
            self.datetime = datetime.datetime(1970, 1, 1)
            self.description = ""

    def __init__(self, package_id):
        self.id = package_id
        self.last = None
        self.consignor = None
        self.consignee = None
        self.last_updated = datetime.datetime(1970, 1, 1)

    @classmethod
    def get_type(cls):
        return "Undefined"

    def on_event(self, event):
        pass

    def update(self):
        pass
