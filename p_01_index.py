from flask import Flask, flash, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from enum import Enum
from datetime import timedelta, datetime


# =============================================================================
# INDEX - RETURN BOOKS
# =============================================================================


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

            sql_query = """SELECT buecher.Titel, buecher.BuchID, buecher.ISBN, buecher.Kommentar, ausleihen.Ausleihdatum from buecher 
                    INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID 
                    INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID 
                    WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"""
            result = db.session.execute(text(sql_query), {"ID": user_id})
            rows = []
            if result:
                rows = [
                    dict(
                        Titel=r[0],
                        BuchID=r[1],
                        ISBN=r[2],
                        Kommentar=r[3],
                        Ausleihdatum=format_date(r[4]),
                    )
                    for r in result
                ]
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
                a_ID=ausleiher.BenutzerID,
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

            sql_query = """SELECT buecher.Titel, buecher.BuchID, buecher.ISBN, buecher.Kommentar, ausleihen.Ausleihdatum from buecher 
                    INNER JOIN ausleihen ON buecher.BuchID = ausleihen.BuchID 
                    INNER JOIN benutzer ON ausleihen.BenutzerID = benutzer.BenutzerID 
                    WHERE ausleihen.Rueckgabedatum IS NULL AND benutzer.BenutzerID = :ID"""
            result = db.session.execute(text(sql_query), {"ID": a_ID})
            rows = []
            if result:
                rows = [
                    dict(
                        Titel=r[0],
                        BuchID=r[1],
                        ISBN=r[2],
                        Kommentar=r[3],
                        Ausleihdatum=format_date(r[4]),
                    )
                    for r in result
                ]
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
