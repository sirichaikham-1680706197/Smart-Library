"""
Games Blueprint
Handles game listing, table display, and booking with overlap detection.
"""

import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g

games_bp = Blueprint('games', __name__, url_prefix='/games')


def get_db():
    if 'db' not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


# ── Routes ─────────────────────────────────────────────────

@games_bp.route('/')
def list_games():
    """List all games and tables."""
    db = get_db()
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = 'SELECT * FROM games WHERE 1=1'
    params = []

    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    if category:
        query += ' AND category = ?'
        params.append(category)

    query += ' ORDER BY created_at DESC'
    games = db.execute(query, params).fetchall()

    tables = db.execute('SELECT * FROM tables ORDER BY name').fetchall()
    categories = db.execute('SELECT DISTINCT category FROM games ORDER BY category').fetchall()

    return render_template('games/list.html', games=games, tables=tables,
                           categories=categories, search=search, selected_category=category)


@games_bp.route('/book', methods=['GET', 'POST'])
def book_table():
    """Book a table for a game session."""
    if 'user_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('auth.login'))

    db = get_db()

    if request.method == 'POST':
        game_id = request.form.get('game_id', type=int)
        table_id = request.form.get('table_id', type=int)
        start_time_str = request.form.get('start_time', '')
        duration = request.form.get('duration', type=int, default=60)

        # Validation
        if not game_id or not table_id or not start_time_str:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
            return redirect(url_for('games.book_table'))

        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('รูปแบบเวลาไม่ถูกต้อง', 'danger')
            return redirect(url_for('games.book_table'))

        end_time = start_time + timedelta(minutes=duration)

        # Check for booking conflicts on the same table
        # Overlap condition: NOT (end <= existing_start OR start >= existing_end)
        conflict = db.execute('''
            SELECT id FROM game_bookings
            WHERE table_id = ?
              AND status != 'cancelled'
              AND NOT (? <= start_time OR ? >= end_time)
        ''', (table_id, end_time.strftime('%Y-%m-%d %H:%M:%S'),
              start_time.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()

        if conflict:
            flash('ช่วงเวลานี้มีการจองโต๊ะนี้อยู่แล้ว กรุณาเลือกเวลาอื่น', 'danger')
            return redirect(url_for('games.book_table'))

        # Prevent booking in the past
        if start_time < datetime.now():
            flash('ไม่สามารถจองเวลาในอดีตได้', 'danger')
            return redirect(url_for('games.book_table'))

        # Create booking
        db.execute('''
            INSERT INTO game_bookings (user_id, game_id, table_id, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], game_id, table_id,
              start_time.strftime('%Y-%m-%d %H:%M:%S'),
              end_time.strftime('%Y-%m-%d %H:%M:%S'),
              'confirmed'))
        db.commit()

        flash('จองโต๊ะเกมสำเร็จ!', 'success')
        return redirect(url_for('games.list_games'))

    # GET: show booking form
    games = db.execute('SELECT * FROM games ORDER BY name').fetchall()
    tables = db.execute('SELECT * FROM tables WHERE status = ? ORDER BY name', ('available',)).fetchall()

    # Pre-select game if provided in URL
    selected_game_id = request.args.get('game_id', type=int)

    return render_template('games/booking.html', games=games, tables=tables,
                           selected_game_id=selected_game_id)
