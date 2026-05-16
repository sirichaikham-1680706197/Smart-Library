"""
Books Blueprint
Handles book listing, search, detail view, and borrow requests.
"""

import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g

books_bp = Blueprint('books', __name__, url_prefix='/books')


def get_db():
    if 'db' not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def login_required_redirect():
    """Check login and redirect if needed."""
    if 'user_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('auth.login'))
    return None


# ── Routes ─────────────────────────────────────────────────

@books_bp.route('/')
def list_books():
    """List all books with search and category filter."""
    db = get_db()
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = 'SELECT * FROM books WHERE 1=1'
    params = []

    if search:
        query += ' AND (title LIKE ? OR author LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    if category:
        query += ' AND category = ?'
        params.append(category)

    query += ' ORDER BY created_at DESC'
    books = db.execute(query, params).fetchall()

    # Get unique categories for filter
    categories = db.execute('SELECT DISTINCT category FROM books ORDER BY category').fetchall()

    return render_template('books/list.html', books=books, categories=categories,
                           search=search, selected_category=category)


@books_bp.route('/<int:book_id>')
def detail(book_id):
    """Book detail view."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if not book:
        flash('ไม่พบหนังสือที่ต้องการ', 'danger')
        return redirect(url_for('books.list_books'))

    # Check if user has pending borrow request
    has_pending = False
    if 'user_id' in session:
        pending = db.execute(
            'SELECT id FROM borrow_requests WHERE user_id = ? AND book_id = ? AND status = ?',
            (session['user_id'], book_id, 'pending')
        ).fetchone()
        has_pending = pending is not None

    review_summary = db.execute(
        'SELECT COUNT(*) as count, COALESCE(ROUND(AVG(rating), 1), 0) as avg_rating FROM reviews WHERE item_type = ? AND item_id = ?',
        ('book', book_id)
    ).fetchone()
    reviews = db.execute(
        'SELECT r.*, u.username FROM reviews r JOIN users u ON u.id = r.user_id WHERE r.item_type = ? AND r.item_id = ? ORDER BY r.created_at DESC',
        ('book', book_id)
    ).fetchall()
    existing_review = None
    if 'user_id' in session:
        existing_review = db.execute(
            'SELECT * FROM reviews WHERE user_id = ? AND item_type = ? AND item_id = ?',
            (session['user_id'], 'book', book_id)
        ).fetchone()

    return render_template('books/detail.html', book=book, has_pending=has_pending,
                           reviews=reviews, review_summary=review_summary,
                           existing_review=existing_review)


@books_bp.route('/<int:book_id>/review', methods=['POST'])
def add_review(book_id):
    if 'user_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('auth.login'))

    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if not book:
        flash('ไม่พบหนังสือที่ต้องการ', 'danger')
        return redirect(url_for('books.list_books'))

    rating = request.form.get('rating', type=int, default=5)
    rating = max(1, min(10, rating))
    comment = request.form.get('comment', '').strip()

    existing = db.execute(
        'SELECT id FROM reviews WHERE user_id = ? AND item_type = ? AND item_id = ?',
        (session['user_id'], 'book', book_id)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE reviews SET rating = ?, comment = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?',
            (rating, comment, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO reviews (user_id, item_type, item_id, rating, comment) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], 'book', book_id, rating, comment)
        )

    db.commit()
    flash('บันทึกรีวิวเรียบร้อย', 'success')
    return redirect(url_for('books.detail', book_id=book_id))


@books_bp.route('/<int:book_id>/borrow', methods=['POST'])
def borrow(book_id):
    """Create a borrow request for a book."""
    redirect_response = login_required_redirect()
    if redirect_response:
        return redirect_response

    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if not book:
        flash('ไม่พบหนังสือที่ต้องการ', 'danger')
        return redirect(url_for('books.list_books'))

    if book['copies'] <= 0:
        flash('หนังสือเล่มนี้ไม่มีให้ยืมแล้ว', 'warning')
        return redirect(url_for('books.detail', book_id=book_id))

    # Check for existing pending/approved request
    existing = db.execute(
        'SELECT id FROM borrow_requests WHERE user_id = ? AND book_id = ? AND status IN (?, ?)',
        (session['user_id'], book_id, 'pending', 'approved')
    ).fetchone()

    if existing:
        flash('คุณมีคำขอยืมหนังสือเล่มนี้อยู่แล้ว', 'warning')
        return redirect(url_for('books.detail', book_id=book_id))

    # Get borrow_days from form (default 7 days)
    borrow_days = int(request.form.get('borrow_days', 7))
    
    # Validate borrow_days
    if borrow_days not in [7, 14, 21, 30]:
        borrow_days = 7
    
    # Calculate due_date
    due_date = datetime.now() + timedelta(days=borrow_days)
    due_date_str = due_date.strftime('%Y-%m-%d %H:%M:%S')

    # Create borrow request
    db.execute(
        'INSERT INTO borrow_requests (user_id, book_id, status, borrow_days, due_date) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], book_id, 'pending', borrow_days, due_date_str)
    )
    db.commit()

    flash('ส่งคำขอยืมหนังสือเรียบร้อย! รอ Admin อนุมัติ', 'success')
    return redirect(url_for('books.detail', book_id=book_id))


@books_bp.route('/<int:borrow_id>/request-return', methods=['POST'])
def request_return(borrow_id):
    """User requests to return a borrowed book."""
    redirect_response = login_required_redirect()
    if redirect_response:
        return redirect_response

    db = get_db()
    borrow = db.execute(
        'SELECT * FROM borrow_requests WHERE id = ? AND user_id = ?',
        (borrow_id, session['user_id'])
    ).fetchone()

    if not borrow:
        flash('ไม่พบการยืมหนังสือนี้', 'danger')
        return redirect(url_for('my_bookings'))

    if borrow['status'] not in ['approved', 'borrowed']:
        flash('ไม่สามารถขอคืนหนังสือในสถานะนี้ได้', 'warning')
        return redirect(url_for('my_bookings'))

    # Update status to return_pending and set return_requested
    db.execute(
        'UPDATE borrow_requests SET status = ?, return_requested = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        ('return_pending', borrow_id)
    )
    db.commit()

    flash('ส่งคำขอคืนหนังสือเรียบร้อย! รอ Admin อนุมัติ', 'success')
    return redirect(url_for('my_bookings'))
