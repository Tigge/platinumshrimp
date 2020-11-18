import re

TRAILING_PUNCTUATION = [".", ",", ":", ";", ".)", '"', "'"]
WRAPPING_PUNCTUATION = [
    ("(", ")"),
    ("<", ">"),
    ("[", "]"),
    ("&lt;", "&gt;"),
    ('"', '"'),
    ("'", "'"),
]

word_split_re = re.compile(r"(\s+)")
simple_url_re = re.compile(r"^https?://\[?\w", re.IGNORECASE)
simple_url_2_re = re.compile(
    r"^www\.|^(?!http)\w[^@]+\.(com|nu|se|co\.uk|net|org)($|/.*)$", re.IGNORECASE
)


def find_urls(text):
    urls = []
    for i, word in enumerate(word_split_re.split(text)):
        if "." in word or "@" in word or ":" in word:
            for punctuation in TRAILING_PUNCTUATION:
                if word.endswith(punctuation):
                    word = word[: -len(punctuation)]
            for opening, closing in WRAPPING_PUNCTUATION:
                if word.startswith(opening):
                    word = word[len(opening) :]
                # Remove parentheses at the end only if they're balanced.
                if (
                    word.endswith(closing)
                    and word.count(closing) == word.count(opening) + 1
                ):
                    word = word[: -len(closing)]
            # Get the url:
            if simple_url_re.match(word):
                urls.append(word)
            elif simple_url_2_re.match(word):
                urls.append("http://%s" % word)

    return urls
