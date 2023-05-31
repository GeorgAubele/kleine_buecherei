from flask import Flask, flash, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from enum import Enum

# from sqlalchemy.sql import func
from sqlalchemy import text, or_

# import webview
from waitress import serve
from isbnlib import to_isbn13
import json


from datetime import date, timedelta
from my_tools import (
    date_to_str,
    str_to_date,
    ISBN_to_book,
    check_ISBN,
    liststring_to_list,
    list_to_liststring,
)


app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bib.db"
app.config["SQLALCHEMY_TRACK_MODIFIKATIONS"] = False
db = SQLAlchemy(app)


# global variables
my_book_list = []
heute = date_to_str(date.today())


class Medien(Enum):
    """Klasse der Medien für die Statistik"""

    Sachbuch = "Sachbuch"
    Roman_Jugendbuch = "Roman_Jugendbuch"
    Kinderbuch = "Kinderbuch"
    Zeitung_Zeitschrift = "Zeitung_Zeitschrift"
    Tonträger = "Tonträger"
    Film = "Film"
    Analoges_Spiel = "Analoges_Spiel"
    Digitales_Medium = "Digitales_Medium"
    Anderes_Nichtbuchmedium = "Anderes_Nichtbuchmedium"
    Virtuelles_Medium = "Virtuelles_Medium"


class Benutzer(db.Model):
    """Klasse der Benutzer der Bücherei"""

    BenutzerID = db.Column(db.Integer, primary_key=True)
    Vorname = db.Column(db.String(100), nullable=False)
    Nachname = db.Column(db.String(100), nullable=False)
    Strasse = db.Column(db.String(150), nullable=True)
    Hausnummer = db.Column(db.Integer, nullable=True)
    PLZ = db.Column(db.Integer, nullable=True)
    Ort = db.Column(db.String(100), nullable=True)
    Bezahlt_bis = db.Column(db.DateTime, default=date.today)


class Buecher(db.Model):
    """Klasse der Bücher in der Bücherei"""

    BuchID = db.Column(db.Integer, primary_key=True)
    ISBN = db.Column(db.Integer, nullable=False)
    Titel = db.Column(db.String(200), nullable=False)
    Autor = db.Column(db.String(100), nullable=True)
    Verlag = db.Column(db.String(100), nullable=True)
    Jahr = db.Column(db.Integer, nullable=True)
    Schlagworte = db.Column(db.String(300), nullable=True, default="Keine")
    Medium = db.Column(db.Enum(Medien), default="Roman_Jugendbuch")
    Anzahl = db.Column(db.Integer, default=1)
    Momentan_vorhanden = db.Column(db.Integer, default=1)


class Ausleihen(db.Model):
    """Klasse der Ausleihen in der Bücherei - Relation"""

    AusleiheID = db.Column(db.Integer, primary_key=True)
    BenutzerID = db.Column(db.Integer, nullable=False)
    BuchID = db.Column(db.Integer, nullable=False)
    Ausleihdatum = db.Column(db.DateTime, default=date.today)
    Rueckgabedatum = db.Column(db.DateTime, nullable=True)


with app.app_context():
    db.create_all()


# window = webview.create_window("Unsere Bibliothek", app, width=1100, height=950)


@app.route("/", methods=["GET", "POST"])
def start_page():
    """Das ist die Startseite - gleichzeitig die Rückgabeseite"""
    if request.method == "POST":
        if "btn_search_last_name" in request.form:
            last_name = request.form["search_last_name"]
            search_result = db.session.execute(
                text("SELECT * FROM Benutzer WHERE Nachname LIKE :s"),
                {"s": "%" + last_name + "%"},
            ).fetchall()
            flash("Benutzer erfolgreich gesucht.")
            return render_template("index.html", users=search_result)

        elif "btn_user_search_id" in request.form:
            search_id = request.form["user_ID"]
            search_result = (
                db.session.query(Benutzer).filter_by(BenutzerID=search_id).all()
            )
            # print(search_result)
            flash("Benutzer erfolgreich gesucht.")
            return render_template("index.html", users=search_result)

        elif "btn_result" in request.form:
            user_id = request.form["btn_result"]
            ausleiher = db.session.get(Benutzer, user_id)
            session["a_ID"] = user_id
            session["a_v"] = ausleiher.Vorname
            session["a_n"] = ausleiher.Nachname
            date_today = date.today()
            date_next_day = date_today + timedelta(days=1)

            sql_query = """SELECT buecher.Titel, buecher.BuchID from buecher 
                    INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID 
                    INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID 
                    WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"""
            result = db.session.execute(text(sql_query), {"ID": user_id})
            rows = []
            if result:
                rows = [dict(Titel=r[0], BuchID=r[1]) for r in result]
            sql_query2 = """SELECT buecher.Titel from buecher 
                    INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID 
                    INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID 
                    WHERE ausleihen.Rueckgabedatum BETWEEN :DAT AND :DAT_NEXT_DAY 
                    AND benutzer.BenutzerID = :ID"""
            result2 = db.session.execute(
                text(sql_query2),
                {"ID": user_id, "DAT": date_today, "DAT_NEXT_DAY": date_next_day},
            )
            backs = []
            if result2:
                backs = [dict(Titel=r[0]) for r in result2]
            return render_template(
                "index.html",
                a_v=ausleiher.Vorname,
                a_n=ausleiher.Nachname,
                rows=rows,
                backs=backs,
            )

        elif "btn_back_ID" in request.form:
            back_ID = request.form["btn_back_ID"]
            a_ID = session.get("a_ID")
            a_v = session.get("a_v")
            a_n = session.get("a_n")
            date_today = date.today()
            date_next_day = date_today + timedelta(days=1)

            sql_query0 = """SELECT ausleihen.AusleiheID from buecher 
                    INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID 
                    INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID 
                    WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID AND buecher.BuchID = :BID"""
            result0 = db.session.execute(
                text(sql_query0), {"ID": a_ID, "BID": back_ID}
            ).fetchone()

            backing_ID = dict(AusleiheID=result0[0])

            rueckgabe = db.session.get(Ausleihen, backing_ID)
            rueckgabe.Rueckgabedatum = date_today
            lend_book = db.session.get(Buecher, back_ID)
            lend_book.Momentan_vorhanden += 1
            db.session.commit()

            sql_query = """SELECT buecher.Titel, buecher.BuchID from buecher 
                    INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID 
                    INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID 
                    WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"""
            result = db.session.execute(text(sql_query), {"ID": a_ID})
            rows = []
            if result:
                rows = [dict(Titel=r[0], BuchID=r[1]) for r in result]
            sql_query2 = """SELECT buecher.Titel from buecher 
                    INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID 
                    INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID 
                    WHERE ausleihen.Rueckgabedatum BETWEEN :DAT AND :DAT_NEXT_DAY 
                    AND benutzer.BenutzerID = :ID"""
            result2 = db.session.execute(
                text(sql_query2),
                {"ID": a_ID, "DAT": date_today, "DAT_NEXT_DAY": date_next_day},
            )
            backs = []
            if result2:
                backs = [dict(Titel=r[0]) for r in result2]

            return render_template(
                "index.html",
                a_v=a_v,
                a_n=a_n,
                rows=rows,
                backs=backs,
            )

    return render_template("index.html")


@app.route("/book_search.html", methods=["GET", "POST"])
def book_search():
    """Funktion der Seite"""
    if request.method == "POST":
        if "btn_book_search" in request.form:
            search_title = request.form["search_title"]
            search_result = Buecher.query.filter(
                Buecher.Titel.ilike(f"%{search_title}%")
            ).all()

            if not search_result:
                flash("Keine Bücher gefunden.")
                return render_template("book_search.html")

            flash("Bücher erfolgreich gesucht.")
            return render_template("book_search.html", books=search_result)

        if "btn_tags_search" in request.form:
            search_tags = liststring_to_list(request.form["tags"])
            search_result = Buecher.query.filter(
                or_(*[Buecher.Schlagworte.ilike(f"%{tag}%") for tag in search_tags])
            ).all()

            if not search_result:
                flash("Keine Bücher gefunden.")
                return render_template("book_search.html")

            flash("Bücher erfolgreich gesucht.")
            return render_template("book_search.html", books=search_result)

    return render_template("book_search.html")


@app.route("/book_import.html", methods=["GET", "POST"])
def book_import():
    """Funktion der Seite"""

    if request.method == "POST":
        if "btn_search_goob" in request.form:
            my_book_list.clear()
            tmp_txt = request.form["ISBNs"]
            ISBNs = tmp_txt.split()
            result_txt = ""
            for item in ISBNs:
                book = ISBN_to_book(item, "goob")
                result_txt += (
                    "ISBN:\t  "
                    + book["ISBN-13"]
                    + "\n"
                    + "Titel:\t  "
                    + book["Title"]
                    + "\n "
                    + "Autoren:\t  "
                    + ", ".join(book["Authors"])
                    + "\n \n"
                )
                my_book_list.append(book)
            # print(my_book_list)
            return render_template(
                "book_import.html", result_txt=result_txt, ISBNs=tmp_txt
            )

        if "btn_search_openl" in request.form:
            my_book_list.clear()
            tmp_txt = request.form["ISBNs"]
            ISBNs = tmp_txt.split()
            result_txt = ""
            for item in ISBNs:
                book = ISBN_to_book(item, "openl")
                result_txt += (
                    "ISBN:\t  "
                    + book["ISBN-13"]
                    + "\n"
                    + "Titel:\t  "
                    + book["Title"]
                    + "\n "
                    + "Autoren:\t  "
                    + ", ".join(book["Authors"])
                    + "\n \n"
                )
                my_book_list.append(book)
            # print(my_book_list)
            return render_template(
                "book_import.html", result_txt=result_txt, ISBNs=tmp_txt
            )

        if "btn_search_wiki" in request.form:
            my_book_list.clear()
            tmp_txt = request.form["ISBNs"]
            ISBNs = tmp_txt.split()
            result_txt = ""
            for item in ISBNs:
                book = ISBN_to_book(item, "wiki")
                result_txt += (
                    "ISBN:\t  "
                    + book["ISBN-13"]
                    + "\n"
                    + "Titel:\t  "
                    + book["Title"]
                    + "\n "
                    + "Autoren:\t  "
                    + ", ".join(book["Authors"])
                    + "\n \n"
                )
                my_book_list.append(book)
            # print(my_book_list)
            return render_template(
                "book_import.html", result_txt=result_txt, ISBNs=tmp_txt
            )

        if "btn_delete_list" in request.form:
            my_book_list.clear()
            return render_template("book_import.html")

        if "btn_import_books" in request.form:
            list_of_ISBNs = [
                num[0]
                for num in db.session.execute(
                    text("SELECT ISBN FROM Buecher")
                ).fetchall()
            ]
            for book in my_book_list:
                if book["ISBN-13"][0] == "*":
                    continue
                elif int(book["ISBN-13"]) in list_of_ISBNs:
                    exist_book = (
                        db.session.query(Buecher)
                        .filter_by(ISBN=book["ISBN-13"])
                        .first()
                    )
                    exist_book.Anzahl += 1
                    exist_book.Momentan_vorhanden += 1
                    db.session.commit()
                else:
                    new_book = Buecher(
                        ISBN=book["ISBN-13"],
                        Titel=book["Title"],
                        Autor=", ".join(book["Authors"]),
                        Verlag=book["Publisher"],
                        Jahr=book["Year"],
                    )
                    with app.app_context():
                        db.session.add(new_book)
                        db.session.commit()
            flash("Bücher erfolgreich importiert.")
            return render_template("book_import.html")

    return render_template("book_import.html")


@app.route("/book_management.html", methods=["GET", "POST"])
def book_management():
    """Funktion der Seite"""
    if request.method == "POST":
        if "btn_book_search" in request.form:
            search_title = request.form["search_title"]
            search_result = Buecher.query.filter(
                Buecher.Titel.ilike(f"%{search_title}%")
            ).all()

            if not search_result:
                flash("Keine Bücher gefunden.")
                return render_template("book_management.html")

            flash("Buch erfolgreich gesucht.")
            return render_template("book_management.html", books=search_result)

        if "btn_tags_search" in request.form:
            search_tags = liststring_to_list(request.form["search_tags"])
            search_result = Buecher.query.filter(
                or_(*[Buecher.Schlagworte.ilike(f"%{tag}%") for tag in search_tags])
            ).all()

            if not search_result:
                flash("Keine Bücher gefunden.")
                return render_template("book_management.html")

            flash("Bücher erfolgreich gesucht.")
            return render_template("book_management.html", books=search_result)

        if "btn_book_picked" in request.form:
            search_ID = request.form["btn_book_picked"]
            search_result = db.session.get(Buecher, search_ID)
            flash("Buch erfolgreich ausgewählt.")
            return render_template("book_management.html", picked_book=search_result)

        if "btn_book_change" in request.form:
            search_ID = request.form["btn_book_change"]
            chg_book = db.session.get(Buecher, search_ID)
            chg_book.ISBN = request.form["ISBN"]
            chg_book.Titel = request.form["title"]
            chg_book.Autor = request.form["author"]
            chg_book.Schlagworte = request.form["tags"]
            chg_book.Medium = request.form["medium"]
            chg_book.Verlag = request.form["publisher"]
            chg_book.Jahr = request.form["year"]
            chg_book.Anzahl = request.form["number"]
            chg_book.Momentan_vorhanden = request.form["available"]
            db.session.add(chg_book)
            db.session.commit()
            flash("Buch erfolgreich geändert")
            return render_template("book_management.html")

        elif "btn_book_delete" in request.form:
            search_ID = request.form["btn_book_delete"]
            book_to_delete = db.session.get(Buecher, search_ID)
            # with app.app_context():
            db.session.delete(book_to_delete)
            db.session.commit()
            flash("Buch erfolgreich gelöscht")
            return render_template("book_management.html")

        if "btn_book_new" in request.form:
            book_ISBN = request.form["ISBN"]
            list_of_ISBNs = [
                num[0]
                for num in db.session.execute(
                    text("SELECT ISBN FROM Buecher")
                ).fetchall()
            ]
            if book_ISBN in list_of_ISBNs:
                exist_book = db.session.query(Buecher).filter_by(ISBN=book_ISBN).first()
                exist_book.Anzahl += 1
                exist_book.Momentan_vorhanden += 1
                db.session.commit()
                flash("Buch bereits vorganden, Anzahl um 1 erhöht.")
            else:
                number = request.form["number"]
                avail = request.form["available"]
                if number == "":
                    number = "1"
                if avail == "":
                    avail = 1
                new_book = Buecher(
                    ISBN=request.form["ISBN"],
                    Titel=request.form["title"],
                    Autor=request.form["author"],
                    Schlagworte=request.form["tags"],
                    Medium=request.form["medium"],
                    Verlag=request.form["publisher"],
                    Jahr=request.form["year"],
                    Anzahl=number,
                    Momentan_vorhanden=avail,
                )
                db.session.add(new_book)
                db.session.commit()
                flash("Buch erfolgreich angelegt.")
                return render_template("book_management.html")

        if "btn_duplicate_search" in request.form:
            return render_template("book_management.html")

        # if "btn_duplicate_search" in request.form:
        #     ISBN_list = db.session.execute("SELECT ISBN FROM Buecher").fetchall()
        #     duplicates = [number for number in ISBN_list if ISBN_list.count(number) > 1]
        #     unique_duplicates = list(set(duplicates))

        #     return render_template("book_management.html")

    return render_template("book_management.html")


@app.route("/lending.html", methods=["GET", "POST"])
def lending():
    """Funktion der Seite"""
    if request.method == "POST":
        if "btn_search_last_name" in request.form:
            last_name = request.form["search_last_name"]
            search_result = db.session.execute(
                text("SELECT * FROM Benutzer WHERE Nachname LIKE :s"),
                {"s": "%" + last_name + "%"},
            ).fetchall()
            flash("Benutzer erfolgreich gesucht.")
            return render_template("lending.html", users=search_result)

        elif "btn_user_search_id" in request.form:
            search_id = request.form["user_ID"]
            search_result = (
                db.session.query(Benutzer).filter_by(BenutzerID=search_id).all()
            )
            # print(search_result)
            flash("Benutzer erfolgreich gesucht.")
            return render_template("lending.html", users=search_result)

        elif "btn_result" in request.form:
            user_id = request.form["btn_result"]
            ausleiher = db.session.get(Benutzer, user_id)
            session["a_ID"] = user_id
            session["a_v"] = ausleiher.Vorname
            session["a_n"] = ausleiher.Nachname
            sql_query = "SELECT buecher.Titel from buecher INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"
            result = db.session.execute(text(sql_query), {"ID": user_id})
            rows = []
            if result:
                rows = [dict(Titel=r[0]) for r in result]
            return render_template(
                "lending.html", a_v=ausleiher.Vorname, a_n=ausleiher.Nachname, rows=rows
            )

        elif "ISBN_search" in request.form:
            a_ID = session.get("a_ID")
            a_v = session.get("a_v")
            a_n = session.get("a_n")
            book_ISBN = request.form["ISBN"]
            if check_ISBN(book_ISBN):
                if len(book_ISBN) == 10:
                    book_ISBN = to_isbn13(book_ISBN)
            searched_book = db.session.query(Buecher).filter_by(ISBN=book_ISBN).first()
            sql_query = "SELECT buecher.Titel from buecher INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"
            result = db.session.execute(text(sql_query), {"ID": a_ID})
            rows = []
            if result:
                rows = [dict(Titel=r[0]) for r in result]

            return render_template(
                "lending.html", a_v=a_v, a_n=a_n, rows=rows, searched_book=searched_book
            )

        elif "title_search" in request.form:
            a_ID = session.get("a_ID")
            a_v = session.get("a_v")
            a_n = session.get("a_n")
            book_title = request.form["Titel"]
            searched_books = db.session.execute(
                text("SELECT * FROM Buecher WHERE Titel LIKE :s"),
                {"s": "%" + book_title + "%"},
            ).fetchall()

            # if check_ISBN(book_ISBN):
            #     if len(book_ISBN) == 10:
            #         book_ISBN = to_isbn13(book_ISBN)
            # searched_book = db.session.query(Buecher).filter_by(ISBN=book_ISBN).first()
            sql_query = "SELECT buecher.Titel from buecher INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"
            result = db.session.execute(text(sql_query), {"ID": a_ID})
            rows = []
            if result:
                rows = [dict(Titel=r[0]) for r in result]

            return render_template(
                "lending.html",
                a_v=a_v,
                a_n=a_n,
                rows=rows,
                searched_books=searched_books,
            )

        elif "wanted_ID" in request.form:
            a_v = session.get("a_v")
            a_n = session.get("a_n")
            a_ID = session.get("a_ID")
            book_ID = request.form["wanted_ID"]

            neue_ausleihe = Ausleihen(BenutzerID=a_ID, BuchID=book_ID)

            with app.app_context():
                db.session.add(neue_ausleihe)
                db.session.commit()

            lend_book = db.session.get(Buecher, book_ID)
            lend_book.Momentan_vorhanden -= 1
            db.session.commit()

            sql_query = "SELECT buecher.Titel from buecher INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"
            result = db.session.execute(text(sql_query), {"ID": a_ID})
            rows = []
            if result:
                rows = [dict(Titel=r[0]) for r in result]

            return render_template("lending.html", a_v=a_v, a_n=a_n, rows=rows)

    return render_template("lending.html")


@app.route("/user_management.html", methods=["GET", "POST"])
def user_management():
    """Funktion der Seite"""
    if request.method == "POST":
        if "new_btn" in request.form:
            new_user = Benutzer(
                Vorname=request.form["first_name"],
                Nachname=request.form["last_name"],
                Strasse=request.form["street"],
                Hausnummer=request.form["hausnummer"],
                PLZ=request.form["PLZ"],
                Ort=request.form["ort"],
                Bezahlt_bis=str_to_date(request.form["paid"]),
            )
            flash("Benutzer erfolgreich angelegt.")
            with app.app_context():
                db.session.add(new_user)
                db.session.commit()
            return render_template("user_management.html", heute=heute)

        elif "btn_search_last_name" in request.form:
            last_name = request.form["search_last_name"]
            search_result = db.session.execute(
                text("SELECT * FROM Benutzer WHERE Nachname LIKE :s"),
                {"s": "%" + last_name + "%"},
            ).fetchall()
            flash("Benutzer erfolgreich gesucht.")
            return render_template(
                "user_management.html", users=search_result, heute=heute
            )

        elif "btn_user_search_id" in request.form:
            search_id = request.form["user_ID"]
            search_result = (
                db.session.query(Benutzer).filter_by(BenutzerID=search_id).all()
            )
            # print(search_result)
            flash("Benutzer erfolgreich gesucht.")
            return render_template(
                "user_management.html", users=search_result, heute=heute
            )

        elif "btn_result" in request.form:
            sel_id = request.form["btn_result"]
            selected_user = db.session.get(Benutzer, sel_id)
            datum = date_to_str(selected_user.Bezahlt_bis)
            flash("Benutzer ausgewählt.")
            return render_template(
                "user_management.html",
                selected_user=selected_user,
                datum=datum,
                heute=heute,
            )

        elif "btn_manage" in request.form:
            sel_id = sel_id = request.form["btn_manage"]
            managed_user = db.session.get(Benutzer, sel_id)
            managed_user.Vorname = request.form["manage_first_name"]
            managed_user.Nachname = request.form["manage_last_name"]
            managed_user.Strasse = request.form["manage_street"]
            managed_user.Hausnummer = request.form["manage_hausnummer"]
            managed_user.PLZ = request.form["manage_PLZ"]
            managed_user.Ort = request.form["manage_ort"]
            managed_user.Bezahlt_bis = str_to_date(request.form["manage_paid"])
            db.session.add(managed_user)
            db.session.commit()
            flash("Benutzer erfolgreich geändert.")
            return render_template("user_management.html", heute=heute)

        elif "btn_delete" in request.form:
            sel_id = request.form["btn_delete"]
            user_to_delete = db.session.get(Benutzer, sel_id)
            # print(user_to_delete)
            # with app.app_context():
            db.session.delete(user_to_delete)
            db.session.commit()
            flash("Benutzer erfolgreich gelöscht")
            return render_template("user_management.html", heute=heute)
        else:
            return render_template("user_management.html", heute=heute)

    return render_template("user_management.html", heute=heute)


@app.route("/report.html")
def report():
    """Funktion der Seite"""
    ergebnis1 = (
        db.session.query(Buecher.Medium, db.func.count(Buecher.BuchID))
        .group_by(Buecher.Medium)
        .all()
    )
    return render_template("report.html", ergebnis1=ergebnis1)


if __name__ == "__main__":
    # app.run(debug=True)
    serve(app, host="127.0.0.1", port=8080)
    # webview.start()
