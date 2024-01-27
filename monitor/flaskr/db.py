""" Database connection and initialization """

import sqlite3

def get_db():
    """
    Connects to the 'monitor.db' SQLite database and returns the connection object.

    Returns:
        sqlite3.Connection: The connection object to the database.
    """
    db = sqlite3.connect('monitor.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """
    Initialize the database by executing the SQL schema script.

    This function opens the 'schema.sql' file, reads its contents, and executes
    the SQL statements in the database connection. It then commits the changes
    to the database.

    If an 'OperationalError' occurs during the execution of the SQL statements,
    it is caught and ignored.

    :return: None
    """
    db = get_db()
    try:
        with open('schema.sql', encoding='utf-8') as f:
            db.executescript(f.read())
        db.commit()
    except sqlite3.OperationalError:
        pass
