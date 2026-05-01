"""
Books Blueprint
Handles book listing, search, detail view, and borrow requests.
"""

import sqlite3
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

    return render_template('books/detail.html', book=book, has_pending=has_pending)


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

    # Check for existing pending request
    existing = db.execute(
        'SELECT id FROM borrow_requests WHERE user_id = ? AND book_id = ? AND status = ?',
        (session['user_id'], book_id, 'pending')
    ).fetchone()

    if existing:
        flash('คุณมีคำขอยืมหนังสือเล่มนี้อยู่แล้ว', 'warning')
        return redirect(url_for('books.detail', book_id=book_id))

    # Create borrow request
    db.execute(
        'INSERT INTO borrow_requests (user_id, book_id, status) VALUES (?, ?, ?)',
        (session['user_id'], book_id, 'pending')
    )
    db.commit()

    flash('ส่งคำขอยืมหนังสือเรียบร้อย! รอ Admin อนุมัติ', 'success')
    return redirect(url_for('books.detail', book_id=book_id))
