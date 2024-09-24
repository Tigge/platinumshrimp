import re
import html


# The regular string.split() only takes a max number of splits,
# but it won't unpack if there aren't enough values.
# This function ensures that we always get the wanted
# number of returned values, even if the string doesn't include
# as many splits values as we want, simply by filling in extra
# empty strings at the end.
#
# Some examples:
# split("a b c d", " ", 3) = ["a", "b", "c d"]
# split("a b c" , " ", 3)  = ["a", "b", "c"]
# split("a b", " ", 3)     = ["a", "b", ""]
def split(s, sep, count):
    return (s + ((count - 1 - s.count(sep)) * sep)).split(sep, count - 1)


# Sanitize a string by removing all new lines and extra spaces
def sanitize_string(s):
    return " ".join(s.split()).strip()


# Unescape HTML/XML entities
def unescape_entities(text):
    def replace_entity(match):
        try:
            if match.group(1) in html.entities.name2codepoint:
                return chr(html.entities.name2codepoint[match.group(1)])
            elif match.group(1).lower().startswith("#x"):
                return chr(int(match.group(1)[2:], 16))
            elif match.group(1).startswith("#"):
                return chr(int(match.group(1)[1:]))
        except (ValueError, KeyError):
            pass  # Fall through to default return
        return match.group(0)

    return re.sub(r"&([#a-zA-Z0-9]+);", replace_entity, text)
