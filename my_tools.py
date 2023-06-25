from datetime import datetime, date

# from isbntools.app import *
from isbnlib import *


def str_to_date(string: str):
    """Wandelt einen String in der Form '30.12.1999' in ein datetime-Objekt um"""
    try:
        date_list = string.split(".")
        wanted_date = date(int(date_list[2]), int(date_list[1]), int(date_list[0]))
    except:
        return
    else:
        return wanted_date


def date_to_str(datum) -> str:
    """Wandelt ein Datum (oder allgemein eine Zeit) in einen String der Form '23.05.1976' um"""
    try:
        wanted_str = datum.strftime("%d.%m.%Y")
    except:
        return
    else:
        return wanted_str


def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
    return date_obj.strftime("%d.%m.%Y")


def liststring_to_list(string: str) -> list:
    """Wandelt eine Liste von Wörtern, mit Komma getrennt, in eine Liste um"""
    liste = string.split(", ")
    return liste


def list_to_liststring(liste: list) -> str:
    answer = "" + ", ".join(liste)
    return answer


def ISBN_to_book(ISBN: str, serv="goob") -> dict:
    """Takes a string, looks up the meta of the according book at Google Books
    and returns the meta as a dictionary. If no book is found, title and
    author start with three asteriscs."""
    book = {}
    try:
        # book = meta(ISBN, service="openl")
        book = meta(ISBN, service=serv)
        # default, goob, wiki, openl
    except:
        return {
            "ISBN-13": "*" + ISBN,
            "Title": "***Keine Buch gefunden***",
            "Authors": {"***Eintrag wird nicht übernommen***"},
        }
    else:
        return book


def check_ISBN(ISBN: str) -> bool:
    """checks if the ISBN is an integer of 10 or 13 digits"""
    if is_isbn10(ISBN) or is_isbn13(ISBN):
        return True
    return False


# {'ISBN-13': '9783426278765',
# 'Title': 'Schachgeschichten - Geniale Spieler, umkämpfte Partien, ungelöste Probleme',
# 'Authors': ['Frederic Friedel', 'Christian Hesse'],
# 'Publisher': '',
# 'Year': '2022',
# 'Language': 'de'}
