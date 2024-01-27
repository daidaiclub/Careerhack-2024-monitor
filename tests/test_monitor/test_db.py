import sqlite3
from flaskr import db

def test_get_db():
    # Connect to the database
    conn = db.get_db()

    # Check if the connection object is of type sqlite3.Connection
    assert isinstance(conn, sqlite3.Connection)

    # Check if the database row factory is set to sqlite3.Row
    assert conn.row_factory == sqlite3.Row

    # Close the database connection
    conn.close()

def test_init_db():
    # Initialize the database
    db.init_db()

    # Connect to the database
    conn = db.get_db()

    # Check if the connection object is of type sqlite3.Connection
    assert isinstance(conn, sqlite3.Connection)

    # Check if the database row factory is set to sqlite3.Row
    assert conn.row_factory == sqlite3.Row

    # Close the database connection
    conn.close()