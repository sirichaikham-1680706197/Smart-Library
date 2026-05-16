"""
Movies Blueprint — movie listing, room booking, watch history, recommendations.
"""
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g

movies_bp = Blueprint('movies', __name__, url_prefix='/movies')


def get_db():
    if 'db' not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@movies_bp.route('/')
def list_movies():
    db = get_db()
    search = request.args.get('search', '').strip()
    genre = request.args.get('genre', '').strip()
    query = 'SELECT * FROM movies WHERE 1=1'
    params = []
    if search:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    if genre:
        query += ' AND genre = ?'
        params.append(genre)
    query += ' ORDER BY rating DESC'
    movies = db.execute(query, params).fetchall()
    genres = db.execute('SELECT DISTINCT genre FROM movies ORDER BY genre').fetchall()
    recommendations = []
    if 'user_id' in session:
        recommendations = _get_recommendations(db, session['user_id'])
    return render_template('movies/list.html', movies=movies, genres=genres,
                           search=search, selected_genre=genre, recommendations=recommendations)


@movies_bp.route('/<int:movie_id>')
def detail(movie_id):
    db = get_db()
    movie = db.execute('SELECT * FROM movies WHERE id = ?', (movie_id,)).fetchone()
    if not movie:
        flash('ไม่พบภาพยนตร์ที่ต้องการ', 'danger')
        return redirect(url_for('movies.list_movies'))

    review_summary = db.execute(
        'SELECT COUNT(*) as count, COALESCE(ROUND(AVG(rating), 1), 0) as avg_rating FROM reviews WHERE item_type = ? AND item_id = ?',
        ('movie', movie_id)
    ).fetchone()
    reviews = db.execute(
        'SELECT r.*, u.username FROM reviews r JOIN users u ON u.id = r.user_id WHERE r.item_type = ? AND r.item_id = ? ORDER BY r.created_at DESC',
        ('movie', movie_id)
    ).fetchall()
    existing_review = None
    if 'user_id' in session:
        existing_review = db.execute(
            'SELECT * FROM reviews WHERE user_id = ? AND item_type = ? AND item_id = ?',
            (session['user_id'], 'movie', movie_id)
        ).fetchone()

    return render_template('movies/detail.html', movie=movie, reviews=reviews,
                           review_summary=review_summary, existing_review=existing_review)


@movies_bp.route('/<int:movie_id>/review', methods=['POST'])
def add_review(movie_id):
    if 'user_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('auth.login'))

    db = get_db()
    movie = db.execute('SELECT * FROM movies WHERE id = ?', (movie_id,)).fetchone()
    if not movie:
        flash('ไม่พบภาพยนตร์ที่ต้องการ', 'danger')
        return redirect(url_for('movies.list_movies'))

    rating = request.form.get('rating', type=int, default=5)
    rating = max(1, min(10, rating))
    comment = request.form.get('comment', '').strip()

    existing = db.execute(
        'SELECT id FROM reviews WHERE user_id = ? AND item_type = ? AND item_id = ?',
        (session['user_id'], 'movie', movie_id)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE reviews SET rating = ?, comment = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?',
            (rating, comment, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO reviews (user_id, item_type, item_id, rating, comment) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], 'movie', movie_id, rating, comment)
        )

    db.commit()
    flash('บันทึกรีวิวเรียบร้อย', 'success')
    return redirect(url_for('movies.detail', movie_id=movie_id))


@movies_bp.route('/book', methods=['GET', 'POST'])
def book_room():
    if 'user_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('auth.login'))
    db = get_db()
    if request.method == 'POST':
        movie_id = request.form.get('movie_id', type=int)
        room_id = request.form.get('room_id', type=int)
        start_time_str = request.form.get('start_time', '')
        if not movie_id or not room_id or not start_time_str:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
            return redirect(url_for('movies.book_room'))
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('รูปแบบเวลาไม่ถูกต้อง', 'danger')
            return redirect(url_for('movies.book_room'))
        movie = db.execute('SELECT * FROM movies WHERE id = ?', (movie_id,)).fetchone()
        if not movie:
            flash('ไม่พบภาพยนตร์', 'danger')
            return redirect(url_for('movies.book_room'))
        end_time = start_time + timedelta(minutes=movie['duration_minutes'] + 15)

        # Validate time range
        if end_time <= start_time:
            flash('เวลาสิ้นสุดต้องมากกว่าเวลาเริ่มต้น', 'danger')
            return redirect(url_for('movies.book_room'))

        if start_time < datetime.now():
            flash('ไม่สามารถจองเวลาในอดีตได้', 'danger')
            return redirect(url_for('movies.book_room'))
        # Check for booking conflicts in the same room
        # Overlap condition: NOT (end <= existing_start OR start >= existing_end)
        # This covers all overlap cases: partial overlap, start collision, end collision, complete overlap
        conflict = db.execute('''
            SELECT id FROM movie_bookings
            WHERE room_id = ? AND status IN ('pending', 'confirmed')
              AND NOT (? <= start_time OR ? >= end_time)
        ''', (room_id, end_time.strftime('%Y-%m-%d %H:%M:%S'),
              start_time.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()

        if conflict:
            flash('ช่วงเวลานี้ห้องนี้ถูกจองแล้ว กรุณาเลือกเวลาใหม่', 'danger')
            return redirect(url_for('movies.book_room'))
        db.execute('''
            INSERT INTO movie_bookings (user_id,movie_id,room_id,start_time,end_time,status)
            VALUES (?,?,?,?,?,?)
        ''', (session['user_id'], movie_id, room_id,
              start_time.strftime('%Y-%m-%d %H:%M:%S'),
              end_time.strftime('%Y-%m-%d %H:%M:%S'), 'confirmed'))
        db.execute('INSERT INTO watch_history (user_id,movie_id) VALUES (?,?)',
                    (session['user_id'], movie_id))
        db.commit()
        flash(f'จองดูหนัง "{movie["title"]}" สำเร็จ!', 'success')
        return redirect(url_for('movies.list_movies'))
    movies = db.execute('SELECT * FROM movies ORDER BY title').fetchall()
    rooms = db.execute('SELECT * FROM rooms ORDER BY name').fetchall()
    selected_movie_id = request.args.get('movie_id', type=int)
    return render_template('movies/booking.html', movies=movies, rooms=rooms,
                           selected_movie_id=selected_movie_id)


@movies_bp.route('/<int:movie_id>/rate', methods=['POST'])
def rate_movie(movie_id):
    if 'user_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('auth.login'))
    rating = request.form.get('rating', type=int, default=5)
    rating = max(1, min(10, rating))
    db = get_db()
    existing = db.execute(
        'SELECT id FROM watch_history WHERE user_id=? AND movie_id=? AND rating>0',
        (session['user_id'], movie_id)).fetchone()
    if existing:
        db.execute('UPDATE watch_history SET rating=? WHERE id=?', (rating, existing['id']))
    else:
        db.execute('INSERT INTO watch_history (user_id,movie_id,rating) VALUES (?,?,?)',
                    (session['user_id'], movie_id, rating))
    db.commit()
    flash('ให้คะแนนเรียบร้อย!', 'success')
    return redirect(url_for('movies.list_movies'))


def _get_recommendations(db, user_id):
    watched_genres = db.execute('''
        SELECT m.genre, COUNT(*) as cnt FROM watch_history wh
        JOIN movies m ON m.id=wh.movie_id WHERE wh.user_id=?
        GROUP BY m.genre ORDER BY cnt DESC LIMIT 3
    ''', (user_id,)).fetchall()
    if not watched_genres:
        return []
    genre_list = [g['genre'] for g in watched_genres]
    ph = ','.join(['?' for _ in genre_list])
    return db.execute(f'''
        SELECT * FROM movies WHERE genre IN ({ph})
          AND id NOT IN (SELECT movie_id FROM watch_history WHERE user_id=?)
        ORDER BY rating DESC LIMIT 4
    ''', genre_list + [user_id]).fetchall()
