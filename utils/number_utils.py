def format(number):
    if number > 1000000:
        return "{:.1f}M".format(number / 1000000)
    if number > 1000:
        return "{:.1f}k".format(number / 1000)
    else:
        return "{:.0f}".format(number)
