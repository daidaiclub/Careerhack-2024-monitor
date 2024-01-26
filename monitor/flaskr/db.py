import sqlite3

def get_db():
    db = sqlite3.connect('monitor.db')
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    try:
        with open('schema.sql') as f:
            db.executescript(f.read())
        db.commit()
    except sqlite3.OperationalError:
        pass
