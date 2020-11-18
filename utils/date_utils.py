import datetime

__author__ = "tigge"

FACTOR = 0.8

MAP = [
    {
        "type": "second",
        "limit": datetime.timedelta(0, 0, 0, 0, FACTOR, 0, 0),
        "factor": 1,
    },
    {
        "type": "minute",
        "limit": datetime.timedelta(0, 0, 0, 0, 0, FACTOR, 0),
        "factor": 60,
    },
    {"type": "hour", "limit": datetime.timedelta(FACTOR), "factor": 60 * 60},
    {
        "type": "day",
        "limit": datetime.timedelta(0, 0, 0, 0, 0, 0, FACTOR),
        "factor": 60 * 60 * 24,
    },
    {
        "type": "week",
        "limit": datetime.timedelta(30 * FACTOR),
        "factor": 60 * 60 * 24 * 7,
    },
    {
        "type": "month",
        "limit": datetime.timedelta(365 * FACTOR),
        "factor": 60 * 60 * 24 * 30,
    },
    {
        "type": "year",
        "limit": datetime.timedelta(25 * 365),
        "factor": 60 * 60 * 24 * 364,
    },
]


def format(date_old, date_new):
    diff = date_new - date_old

    for item in MAP:
        if diff < item["limit"]:
            count = int(round(diff.total_seconds() / item["factor"]))
            unit = item["type"] if count <= 1 else item["type"] + "s"

            return "{} {} ago".format(count, unit)
