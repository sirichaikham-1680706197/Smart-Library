"""
Smart Digital Library with Game & Movie Booking System
Main application factory.
"""
import sqlite3
from flask import Flask, render_template, g, session
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Database helper ────────────────────────────────────
    def get_db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    # ── Context processor ──────────────────────────────────
    @app.context_processor
    def inject_user():
        return {
            'current_user': {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'role': session.get('role'),
                'is_authenticated': 'user_id' in session,
                'is_admin': session.get('role') == 'admin',
            }
        }

    # ── Register Blueprints ───────────────────────────────
    from blueprints.auth import auth_bp
    from blueprints.books import books_bp
    from blueprints.games import games_bp
    from blueprints.movies import movies_bp
    from blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(movies_bp)
    app.register_blueprint(admin_bp)

    # ── Main routes ────────────────────────────────────────
    @app.route('/')
    def index():
        db = get_db()
        stats = {
            'books': db.execute('SELECT COUNT(*) as c FROM books').fetchone()['c'],
            'games': db.execute('SELECT COUNT(*) as c FROM games').fetchone()['c'],
            'movies': db.execute('SELECT COUNT(*) as c FROM movies').fetchone()['c'],
        }
        featured_books = db.execute('SELECT * FROM books ORDER BY created_at DESC LIMIT 4').fetchall()
        featured_movies = db.execute('SELECT * FROM movies ORDER BY rating DESC LIMIT 4').fetchall()
        return render_template('index.html', stats=stats, featured_books=featured_books,
                               featured_movies=featured_movies)

    # Alias for url_for('main.index')
    app.add_url_rule('/', endpoint='main.index')

    # ── My Bookings route ──────────────────────────────────
    @app.route('/my-bookings')
    def my_bookings():
        if 'user_id' not in session:
            from flask import flash, redirect, url_for
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        db = get_db()
        uid = session['user_id']
        borrows = db.execute('''
            SELECT br.*, b.title, b.author FROM borrow_requests br
            JOIN books b ON b.id=br.book_id WHERE br.user_id=?
            ORDER BY br.created_at DESC
        ''', (uid,)).fetchall()
        game_bks = db.execute('''
            SELECT gb.*, g.name as game_name, g.image as game_image, t.name as table_name
            FROM game_bookings gb JOIN games g ON g.id=gb.game_id
            JOIN tables t ON t.id=gb.table_id WHERE gb.user_id=?
            ORDER BY gb.created_at DESC
        ''', (uid,)).fetchall()
        movie_bks = db.execute('''
            SELECT mb.*, m.title as movie_title, m.poster_image as movie_image, r.name as room_name, m.duration_minutes
            FROM movie_bookings mb JOIN movies m ON m.id=mb.movie_id
            JOIN rooms r ON r.id=mb.room_id WHERE mb.user_id=?
            ORDER BY mb.created_at DESC
        ''', (uid,)).fetchall()
        watch_hist = db.execute('''
            SELECT wh.*, m.title, m.genre FROM watch_history wh
            JOIN movies m ON m.id=wh.movie_id WHERE wh.user_id=?
            ORDER BY wh.watched_at DESC
        ''', (uid,)).fetchall()
        return render_template('user/my_bookings.html', borrows=borrows,
                               game_bookings=game_bks, movie_bookings=movie_bks,
                               watch_history=watch_hist)

    # Add endpoint alias for my_bookings
    app.add_url_rule('/my-bookings', endpoint='my_bookings')

    # ── Error handlers ─────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html', error_code=404, error_msg='ไม่พบหน้าที่ต้องการ'), 404

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
