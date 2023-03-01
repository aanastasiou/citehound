"""
Various utility functions reired throughout the system.

:author: Athanasios Anastasiou
:date: Mar 2023
"""

import re


def affiliation_standardisation(an_affiliation):
    """
    Accepts an affiliation string and standardises it according to discovered patterns

    :param an_affiliion: The affiliation string associated (usually) with an author.
    :type an_affiliation: str

    :returns: A string with certain empirical corrections.
    :rtype: str
    """
    # First of all, apply all these transformations, the string is
    # assumed to have already been transformed to lower case
    replacements = [(re.compile(r"center"), "centre"),  # REPLACE: Center or center for centre
                    (re.compile(r" ucl "), " university college london "),  # REPLACE: UCL for University College London
                    (re.compile(r" ucl,"), " university college london,"),
                    (re.compile(r"\(ucl\)"), "university college london,"),
                    (re.compile(r"usa"), "united states"),  # REPLACE: USA for United States (GRID)
                    (re.compile(r"united states of america"), "united states"),
                    (re.compile(r"england"), "united kingdom"),  # REPLACE: USA for United States (GRID)
                    (re.compile(r"new united kingdom"), "new england"),  # REPLACE: USA for United States (GRID)
                    (re.compile(r"uk"), "united kingdom"),  # REPLACE: UK for United Kingdom
                    (re.compile(r"the netherlands"), "netherlands"),
                    (re.compile(r"republic of ireland"), "ireland"),
                    (re.compile(r"\(.+?\)"), ""),
                    # REPLACE: Anything inside a parentheses, ESPECIALLY if it is the author's initials, with null
                    (re.compile(r"^[0-9]\] "), ""),
                    # REPLACE: An author enumeration that is incomplete at the start of the string with null
                    (re.compile(r"\[[0-9]+\]"), ","),
                    # REPLACE: An author enumeration anywhere in the string by a coma so that it
                    # is actually split, with COMA
                    (re.compile(r"^. "), ""),  # REPLACE: Starts with any character followed by a space, with null
                    (re.compile(r"(\s)\s+"), " "),
                    # REPLACE: Occasions where there are long sequences of whitespaces (more than 2 at least)
                    # sub by 1 space
                    (re.compile(r"( ; )|( ;)"), ";"),  # REPLACE:Semicolons with strange spacings
                    (re.compile(r"( , )|( ,)"), ","),  # REPLACE:Comas with strange spacings with a coma
                    ]
    rep_string = an_affiliation
    rep_string = rep_string.lower()
    for aReplacement in replacements:
        rep_string = aReplacement[0].sub(aReplacement[1], rep_string)
    return rep_string


def affiliation_tokenisation(an_affiliation):
    """
    Accepts an affiliation string and returns a list of tokens according to some rule
    :param an_affiliation:
    :return:
    """
    pass
