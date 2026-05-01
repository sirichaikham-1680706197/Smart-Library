"""
Admin Blueprint — Dashboard, CRUD for books/games/movies, borrow request management.
"""
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def get_db():
    if 'db' not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึง', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def dashboard():
    db = get_db()
    stats = {
        'users': db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c'],
        'books': db.execute('SELECT COUNT(*) as c FROM books').fetchone()['c'],
        'games': db.execute('SELECT COUNT(*) as c FROM games').fetchone()['c'],
        'movies': db.execute('SELECT COUNT(*) as c FROM movies').fetchone()['c'],
        'pending_borrows': db.execute("SELECT COUNT(*) as c FROM borrow_requests WHERE status='pending'").fetchone()['c'],
        'game_bookings': db.execute("SELECT COUNT(*) as c FROM game_bookings WHERE status='confirmed'").fetchone()['c'],
        'movie_bookings': db.execute("SELECT COUNT(*) as c FROM movie_bookings WHERE status='confirmed'").fetchone()['c'],
    }
    recent_borrows = db.execute('''
        SELECT br.*, u.username, b.title FROM borrow_requests br
        JOIN users u ON u.id=br.user_id JOIN books b ON b.id=br.book_id
        ORDER BY br.created_at DESC LIMIT 5
    ''').fetchall()
    recent_game = db.execute('''
        SELECT gb.*, u.username, g.name as game_name, t.name as table_name
        FROM game_bookings gb JOIN users u ON u.id=gb.user_id
        JOIN games g ON g.id=gb.game_id JOIN tables t ON t.id=gb.table_id
        ORDER BY gb.created_at DESC LIMIT 5
    ''').fetchall()
    recent_movie = db.execute('''
        SELECT mb.*, u.username, m.title as movie_title, r.name as room_name
        FROM movie_bookings mb JOIN users u ON u.id=mb.user_id
        JOIN movies m ON m.id=mb.movie_id JOIN rooms r ON r.id=mb.room_id
        ORDER BY mb.created_at DESC LIMIT 5
    ''').fetchall()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_borrows=recent_borrows, recent_game=recent_game,
                           recent_movie=recent_movie)


# ── Borrow Requests ───────────────────────────────────────
@admin_bp.route('/borrows')
@admin_required
def borrow_requests():
    db = get_db()
    status_filter = request.args.get('status', '')
    query = '''SELECT br.*, u.username, b.title, b.copies FROM borrow_requests br
               JOIN users u ON u.id=br.user_id JOIN books b ON b.id=br.book_id'''
    params = []
    if status_filter:
        query += ' WHERE br.status=?'
        params.append(status_filter)
    query += ' ORDER BY br.created_at DESC'
    requests_list = db.execute(query, params).fetchall()
    return render_template('admin/borrow_requests.html', requests=requests_list, status_filter=status_filter)


@admin_bp.route('/borrows/<int:req_id>/approve', methods=['POST'])
@admin_required
def approve_borrow(req_id):
    db = get_db()
    req = db.execute('SELECT * FROM borrow_requests WHERE id=?', (req_id,)).fetchone()
    if not req:
        flash('ไม่พบคำขอ', 'danger')
        return redirect(url_for('admin.borrow_requests'))
    book = db.execute('SELECT * FROM books WHERE id=?', (req['book_id'],)).fetchone()
    if book['copies'] <= 0:
        flash('หนังสือหมด ไม่สามารถอนุมัติได้', 'danger')
        return redirect(url_for('admin.borrow_requests'))
    db.execute("UPDATE borrow_requests SET status='approved', updated_at=CURRENT_TIMESTAMP WHERE id=?", (req_id,))
    db.execute("UPDATE books SET copies=copies-1 WHERE id=?", (req['book_id'],))
    db.commit()
    flash('อนุมัติการยืมเรียบร้อย', 'success')
    return redirect(url_for('admin.borrow_requests'))


@admin_bp.route('/borrows/<int:req_id>/reject', methods=['POST'])
@admin_required
def reject_borrow(req_id):
    db = get_db()
    db.execute("UPDATE borrow_requests SET status='rejected', updated_at=CURRENT_TIMESTAMP WHERE id=?", (req_id,))
    db.commit()
    flash('ปฏิเสธการยืมเรียบร้อย', 'info')
    return redirect(url_for('admin.borrow_requests'))


# ── Manage Books ───────────────────────────────────────────
@admin_bp.route('/books')
@admin_required
def manage_books():
    db = get_db()
    books = db.execute('SELECT * FROM books ORDER BY created_at DESC').fetchall()
    return render_template('admin/manage_books.html', books=books)


@admin_bp.route('/books/add', methods=['POST'])
@admin_required
def add_book():
    db = get_db()
    db.execute('INSERT INTO books (title,author,category,description,cover_image,copies) VALUES (?,?,?,?,?,?)',
               (request.form['title'], request.form['author'], request.form['category'],
                request.form.get('description',''), request.form.get('cover_image',''), int(request.form.get('copies',1))))
    db.commit()
    flash('เพิ่มหนังสือสำเร็จ', 'success')
    return redirect(url_for('admin.manage_books'))


@admin_bp.route('/books/<int:bid>/edit', methods=['POST'])
@admin_required
def edit_book(bid):
    db = get_db()
    db.execute('UPDATE books SET title=?,author=?,category=?,description=?,cover_image=?,copies=? WHERE id=?',
               (request.form['title'], request.form['author'], request.form['category'],
                request.form.get('description',''), request.form.get('cover_image',''),
                int(request.form.get('copies',1)), bid))
    db.commit()
    flash('แก้ไขหนังสือสำเร็จ', 'success')
    return redirect(url_for('admin.manage_books'))


@admin_bp.route('/books/<int:bid>/delete', methods=['POST'])
@admin_required
def delete_book(bid):
    db = get_db()
    db.execute('DELETE FROM books WHERE id=?', (bid,))
    db.commit()
    flash('ลบหนังสือสำเร็จ', 'success')
    return redirect(url_for('admin.manage_books'))


# ── Manage Games ───────────────────────────────────────────
@admin_bp.route('/games')
@admin_required
def manage_games():
    db = get_db()
    games = db.execute('SELECT * FROM games ORDER BY created_at DESC').fetchall()
    return render_template('admin/manage_games.html', games=games)


@admin_bp.route('/games/add', methods=['POST'])
@admin_required
def add_game():
    db = get_db()
    db.execute('INSERT INTO games (name,category,description,image,min_players,max_players) VALUES (?,?,?,?,?,?)',
               (request.form['name'], request.form['category'], request.form.get('description',''),
                request.form.get('image','🎮'), int(request.form.get('min_players',2)), int(request.form.get('max_players',4))))
    db.commit()
    flash('เพิ่มเกมสำเร็จ', 'success')
    return redirect(url_for('admin.manage_games'))


@admin_bp.route('/games/<int:gid>/edit', methods=['POST'])
@admin_required
def edit_game(gid):
    db = get_db()
    db.execute('UPDATE games SET name=?,category=?,description=?,image=?,min_players=?,max_players=? WHERE id=?',
               (request.form['name'], request.form['category'], request.form.get('description',''),
                request.form.get('image','🎮'), int(request.form.get('min_players',2)),
                int(request.form.get('max_players',4)), gid))
    db.commit()
    flash('แก้ไขเกมสำเร็จ', 'success')
    return redirect(url_for('admin.manage_games'))


@admin_bp.route('/games/<int:gid>/delete', methods=['POST'])
@admin_required
def delete_game(gid):
    db = get_db()
    db.execute('DELETE FROM games WHERE id=?', (gid,))
    db.commit()
    flash('ลบเกมสำเร็จ', 'success')
    return redirect(url_for('admin.manage_games'))


# ── Manage Movies ──────────────────────────────────────────
@admin_bp.route('/movies')
@admin_required
def manage_movies():
    db = get_db()
    movies = db.execute('SELECT * FROM movies ORDER BY created_at DESC').fetchall()
    return render_template('admin/manage_movies.html', movies=movies)


@admin_bp.route('/movies/add', methods=['POST'])
@admin_required
def add_movie():
    db = get_db()
    db.execute('INSERT INTO movies (title,genre,description,poster_image,duration_minutes,rating) VALUES (?,?,?,?,?,?)',
               (request.form['title'], request.form['genre'], request.form.get('description',''),
                request.form.get('poster_image','🎬'), int(request.form.get('duration_minutes',120)),
                float(request.form.get('rating',0))))
    db.commit()
    flash('เพิ่มหนังสำเร็จ', 'success')
    return redirect(url_for('admin.manage_movies'))


@admin_bp.route('/movies/<int:mid>/edit', methods=['POST'])
@admin_required
def edit_movie(mid):
    db = get_db()
    db.execute('UPDATE movies SET title=?,genre=?,description=?,poster_image=?,duration_minutes=?,rating=? WHERE id=?',
               (request.form['title'], request.form['genre'], request.form.get('description',''),
                request.form.get('poster_image','🎬'), int(request.form.get('duration_minutes',120)),
                float(request.form.get('rating',0)), mid))
    db.commit()
    flash('แก้ไขหนังสำเร็จ', 'success')
    return redirect(url_for('admin.manage_movies'))


@admin_bp.route('/movies/<int:mid>/delete', methods=['POST'])
@admin_required
def delete_movie(mid):
    db = get_db()
    db.execute('DELETE FROM movies WHERE id=?', (mid,))
    db.commit()
    flash('ลบหนังสำเร็จ', 'success')
    return redirect(url_for('admin.manage_movies'))
