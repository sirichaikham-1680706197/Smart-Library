"""
Database initialization script.
Creates all tables and seeds sample data.
"""

import sqlite3
import os
import bcrypt
from config import Config


def get_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn):
    """Create all database tables."""
    cursor = conn.cursor()

    # ── Users ──────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Books ──────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            cover_image TEXT,
            copies INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Borrow Requests ───────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS borrow_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # ── Games ──────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            image TEXT,
            min_players INTEGER NOT NULL DEFAULT 2,
            max_players INTEGER NOT NULL DEFAULT 4,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Tables ─────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 4,
            status TEXT NOT NULL DEFAULT 'available',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Game Bookings ──────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            table_id INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (game_id) REFERENCES games(id),
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    ''')

    # ── Movies ─────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            genre TEXT NOT NULL,
            description TEXT,
            poster_image TEXT,
            duration_minutes INTEGER NOT NULL DEFAULT 120,
            rating REAL DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Rooms ──────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            room_type TEXT NOT NULL DEFAULT 'movie',
            capacity INTEGER NOT NULL DEFAULT 10,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Movie Bookings ─────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movie_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (movie_id) REFERENCES movies(id),
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    ''')

    # ── Watch History ──────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            watched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            rating INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (movie_id) REFERENCES movies(id)
        )
    ''')

    conn.commit()
    print("✅ All tables created successfully.")


def seed_data(conn):
    """Insert sample data into the database."""
    cursor = conn.cursor()

    # ── Admin & User Accounts ──────────────────────────────
    admin_pw = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_pw = bcrypt.hashpw('user123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cursor.executemany('''
        INSERT OR IGNORE INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)
    ''', [
        ('admin', 'admin@library.com', admin_pw, 'admin'),
        ('john', 'john@example.com', user_pw, 'user'),
        ('jane', 'jane@example.com', user_pw, 'user'),
    ])

    # ── Books ──────────────────────────────────────────────
    books = [
        ('The Great Gatsby', 'F. Scott Fitzgerald', 'Fiction',
         'A story of decadence, idealism, and excess set in the Jazz Age.',
         'https://covers.openlibrary.org/b/id/8432047-L.jpg', 5),
        ('Clean Code', 'Robert C. Martin', 'Technology',
         'A handbook of agile software craftsmanship.',
         'https://covers.openlibrary.org/b/id/8552651-L.jpg', 3),
        ('Sapiens', 'Yuval Noah Harari', 'History',
         'A brief history of humankind exploring how Homo sapiens came to dominate the world.',
         'https://covers.openlibrary.org/b/id/8409647-L.jpg', 4),
        ('The Pragmatic Programmer', 'David Thomas & Andrew Hunt', 'Technology',
         'Your journey to mastery in software development.',
         'https://covers.openlibrary.org/b/id/12662871-L.jpg', 2),
        ('Dune', 'Frank Herbert', 'Science Fiction',
         'An epic science fiction novel set in a distant future.',
         'https://covers.openlibrary.org/b/id/12711547-L.jpg', 6),
        ('1984', 'George Orwell', 'Fiction',
         'A dystopian social science fiction novel about totalitarianism.',
         'https://covers.openlibrary.org/b/id/12648655-L.jpg', 4),
        ('The Art of War', 'Sun Tzu', 'Philosophy',
         'An ancient Chinese military treatise on strategy and tactics.',
         'https://covers.openlibrary.org/b/id/8231994-L.jpg', 3),
        ('Design Patterns', 'Gang of Four', 'Technology',
         'Elements of reusable object-oriented software design.',
         'https://covers.openlibrary.org/b/id/6484360-L.jpg', 2),
        ('To Kill a Mockingbird', 'Harper Lee', 'Fiction',
         'A novel about racial injustice in the American South.',
         'https://covers.openlibrary.org/b/id/8228691-L.jpg', 5),
        ('Atomic Habits', 'James Clear', 'Self-Help',
         'An easy and proven way to build good habits and break bad ones.',
         'https://covers.openlibrary.org/b/id/10958382-L.jpg', 7),
        ('Python Crash Course', 'Eric Matthes', 'Technology',
         'A hands-on, project-based introduction to programming.',
         'https://covers.openlibrary.org/b/id/12889159-L.jpg', 4),
        ('The Hobbit', 'J.R.R. Tolkien', 'Fantasy',
         'A fantasy novel about the quest of Bilbo Baggins.',
         'https://covers.openlibrary.org/b/id/6979861-L.jpg', 3),
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO books (title, author, category, description, cover_image, copies)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', books)

    # ── Games ──────────────────────────────────────────────
    games = [
        ('Chess', 'Strategy', 'The classic game of strategy and tactics.', '♟️', 2, 2),
        ('Monopoly', 'Board Game', 'The fast-dealing property trading game.', '🏠', 2, 6),
        ('Catan', 'Strategy', 'Trade, build, and settle the island of Catan.', '🏝️', 3, 4),
        ('Scrabble', 'Word Game', 'Form words with letter tiles on a game board.', '🔤', 2, 4),
        ('Risk', 'Strategy', 'A strategy board game of diplomacy and conquest.', '🗺️', 2, 6),
        ('Uno', 'Card Game', 'The classic card game of matching colors and numbers.', '🃏', 2, 10),
        ('Jenga', 'Dexterity', 'Remove blocks from a tower without toppling it.', '🧱', 2, 8),
        ('Ticket to Ride', 'Strategy', 'Build train routes across the country.', '🚂', 2, 5),
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO games (name, category, description, image, min_players, max_players)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', games)

    # ── Tables ─────────────────────────────────────────────
    tables = [
        ('Table A1', 4, 'available'),
        ('Table A2', 4, 'available'),
        ('Table B1', 6, 'available'),
        ('Table B2', 6, 'available'),
        ('Table C1', 8, 'available'),
        ('VIP Table', 10, 'available'),
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO tables (name, capacity, status) VALUES (?, ?, ?)
    ''', tables)

    # ── Movies ─────────────────────────────────────────────
    movies = [
        ('Inception', 'Sci-Fi',
         'A thief who steals corporate secrets through dream-sharing technology.',
         '🎬', 148, 8.8),
        ('The Dark Knight', 'Action',
         'Batman faces the Joker, a criminal mastermind who wants to plunge Gotham into anarchy.',
         '🦇', 152, 9.0),
        ('Interstellar', 'Sci-Fi',
         'A team of explorers travel through a wormhole in space to find a new home for humanity.',
         '🚀', 169, 8.7),
        ('The Shawshank Redemption', 'Drama',
         'Two imprisoned men bond over a number of years.',
         '🏛️', 142, 9.3),
        ('Pulp Fiction', 'Crime',
         'The lives of two mob hitmen, a boxer, and others intertwine in tales of violence.',
         '💊', 154, 8.9),
        ('Spirited Away', 'Animation',
         'A young girl enters a world of spirits and must find her way back.',
         '🏯', 125, 8.6),
        ('The Matrix', 'Sci-Fi',
         'A computer programmer discovers the world is a simulation.',
         '💻', 136, 8.7),
        ('Parasite', 'Thriller',
         'A poor family schemes to become employed by a wealthy family.',
         '🎭', 132, 8.5),
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO movies (title, genre, description, poster_image, duration_minutes, rating)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', movies)

    # ── Rooms ──────────────────────────────────────────────
    rooms = [
        ('Theater 1', 'movie', 20),
        ('Theater 2', 'movie', 15),
        ('Theater 3', 'movie', 30),
        ('Study Room A', 'study', 6),
        ('Study Room B', 'study', 8),
        ('VIP Theater', 'movie', 10),
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO rooms (name, room_type, capacity) VALUES (?, ?, ?)
    ''', rooms)

    conn.commit()
    print("✅ Sample data seeded successfully.")
    print("   Admin: admin / admin123")
    print("   User:  john / user123")


def init_db():
    """Initialize the database: create tables and seed data."""
    # Remove existing database for fresh start
    if os.path.exists(Config.DATABASE):
        os.remove(Config.DATABASE)
        print("🗑️  Old database removed.")

    conn = get_db()
    create_tables(conn)
    seed_data(conn)
    conn.close()
    print("\n🎉 Database initialized successfully!")


if __name__ == '__main__':
    init_db()
