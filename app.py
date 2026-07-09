"""
Programming Contest Registration & Score Tracker
Backend: Python / Flask
Database: MySQL
BUP CSE 3102 DBMS Lab
"""



from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
import bcrypt
from datetime import datetime
from functools import wraps
import os
from uuid import uuid4
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'bup_cse3102_contest_secret_2024'

# ──────────────────────────────────────────────
# PROFILE IMAGE UPLOAD CONFIG
# ──────────────────────────────────────────────
PROFILE_UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads', 'profile')
app.config['PROFILE_UPLOAD_FOLDER'] = PROFILE_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)


def allowed_image_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


# ──────────────────────────────────────────────
# DB CONFIG
# ──────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'aziz28aziz28@22',   # use your real MySQL Workbench password
    'database': 'contest_tracker',
    'charset': 'utf8mb4'
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# ──────────────────────────────────────────────
# AUTH HELPERS
# ──────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ──────────────────────────────────────────────
# AUTH ROUTES
# ──────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE LOWER(email) = %s", (email,))
        user = cur.fetchone()

        cur.close()
        db.close()

        if user:
            stored_password = user['password'].strip()

            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                session.clear()
                session['user_id'] = user['user_id']
                session['name'] = user['name']
                session['role'] = user['role']
                session['email'] = user['email']

                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user['role'] == 'advisor':
                    return redirect(url_for('advisor_dashboard'))
                else:
                    return redirect(url_for('participant_dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        dept = request.form['department'].strip()
        pw = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt()).decode()

        try:
            db = get_db()
            cur = db.cursor()

            cur.execute("""
                INSERT INTO users (name, email, password, department, role)
                VALUES (%s, %s, %s, %s, 'participant')
            """, (name, email, pw, dept))

            db.commit()
            cur.close()
            db.close()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except mysql.connector.IntegrityError:
            flash('Email already registered.', 'danger')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    role = session['role']

    if role == 'admin':
        return redirect(url_for('admin_dashboard'))

    if role == 'advisor':
        return redirect(url_for('advisor_dashboard'))

    return redirect(url_for('participant_dashboard'))

# ══════════════════════════════════════════════
# ADMIN PORTAL
# ══════════════════════════════════════════════

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'participant'")
    participants = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS count FROM events")
    events = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS count FROM teams")
    teams = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS count FROM submissions WHERE is_correct = 1")
    solved = cur.fetchone()['count']

    cur.execute("""
        SELECT event_id, event_name, start_time, end_time, status
        FROM events
        ORDER BY start_time DESC
        LIMIT 5
    """)
    recent_events = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'admin/dashboard.html',
        participants=participants,
        events=events,
        teams=teams,
        solved=solved,
        recent_events=recent_events
    )

@app.route('/admin/events', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_events():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        event_name = request.form.get('event_name', '').strip()
        description = request.form.get('description', '').strip()
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        min_team_size = request.form.get('min_team_size', 1)
        max_team_size = request.form.get('max_team_size', 3)
        status = request.form.get('status', 'upcoming')

        if not event_name or not start_time or not end_time:
            flash('Event name, start time, and end time are required.', 'warning')
        else:
            cur.execute("""
                INSERT INTO events 
                (event_name, description, start_time, end_time, min_team_size, max_team_size, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_name,
                description,
                start_time,
                end_time,
                int(min_team_size),
                int(max_team_size),
                status
            ))

            db.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin_events'))

    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    sql = """
        SELECT *
        FROM events
        WHERE 1=1
    """
    params = []

    if q:
        sql += """
            AND (
                event_name LIKE %s OR
                description LIKE %s
            )
        """
        like_q = f"%{q}%"
        params.extend([like_q, like_q])

    if status_filter:
        sql += " AND status = %s"
        params.append(status_filter)

    sql += " ORDER BY start_time DESC"

    cur.execute(sql, tuple(params))
    events = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'admin/events.html',
        events=events,
        q=q,
        status_filter=status_filter
    )

@app.route('/admin/events/<int:event_id>/status', methods=['POST'])
@login_required
@role_required('admin')
def update_event_status(event_id):
    new_status = request.form.get('status', '').strip().lower()

    allowed_statuses = ['upcoming', 'ongoing', 'completed', 'cancelled']

    if new_status not in allowed_statuses:
        flash('Invalid event status.', 'danger')
        return redirect(url_for('admin_events'))

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        UPDATE events
        SET status = %s
        WHERE event_id = %s
    """, (new_status, event_id))

    db.commit()

    cur.close()
    db.close()

    flash('Event status updated successfully.', 'success')
    return redirect(url_for('admin_events'))


@app.route('/admin/problems', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_problems():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        event_id = request.form.get('event_id')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        difficulty = request.form.get('difficulty', 'easy')
        input_format = request.form.get('input_format', '').strip()
        output_format = request.form.get('output_format', '').strip()
        sample_input = request.form.get('sample_input', '').strip()
        sample_output = request.form.get('sample_output', '').strip()
        correct_output = request.form.get('correct_output', '').strip()
        base_score = request.form.get('base_score', 100)
        min_score = request.form.get('min_score', 20)
        decay_interval = request.form.get('decay_interval', 10)
        decay_amount = request.form.get('decay_amount', 5)

        if not event_id or not title or not correct_output:
            flash('Event, problem title, and correct output are required.', 'warning')
        else:
            cur.execute("""
                INSERT INTO problems
                (event_id, title, description, difficulty, input_format, output_format,
                 sample_input, sample_output, correct_output, base_score, min_score,
                 decay_interval, decay_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                int(event_id),
                title,
                description,
                difficulty,
                input_format,
                output_format,
                sample_input,
                sample_output,
                correct_output,
                int(base_score),
                int(min_score),
                int(decay_interval),
                int(decay_amount)
            ))

            db.commit()
            flash('Problem added successfully!', 'success')
            return redirect(url_for('admin_problems'))

    q = request.args.get('q', '').strip()
    event_filter = request.args.get('event_id', type=int)
    difficulty_filter = request.args.get('difficulty', '').strip()

    cur.execute("""
        SELECT event_id, event_name, status
        FROM events
        ORDER BY start_time DESC
    """)
    events = cur.fetchall()

    sql = """
        SELECT 
            p.*,
            e.event_name
        FROM problems p
        JOIN events e ON e.event_id = p.event_id
        WHERE 1=1
    """
    params = []

    if q:
        sql += """
            AND (
                p.title LIKE %s OR
                p.description LIKE %s OR
                p.correct_output LIKE %s
            )
        """
        like_q = f"%{q}%"
        params.extend([like_q, like_q, like_q])

    if event_filter:
        sql += " AND p.event_id = %s"
        params.append(event_filter)

    if difficulty_filter:
        sql += " AND p.difficulty = %s"
        params.append(difficulty_filter)

    sql += " ORDER BY p.problem_id DESC"

    cur.execute(sql, tuple(params))
    problems = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'admin/problems.html',
        events=events,
        problems=problems,
        q=q,
        event_filter=event_filter,
        difficulty_filter=difficulty_filter
    )

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    q = request.args.get('q', '').strip()
    role = request.args.get('role', '').strip()

    db = get_db()
    cur = db.cursor(dictionary=True)

    sql = """
        SELECT user_id, name, email, department, role, created_at
        FROM users
        WHERE 1=1
    """
    params = []

    if q:
        sql += """
            AND (
                name LIKE %s OR
                email LIKE %s OR
                department LIKE %s
            )
        """
        like_q = f"%{q}%"
        params.extend([like_q, like_q, like_q])

    if role:
        sql += " AND role = %s"
        params.append(role)

    sql += " ORDER BY user_id DESC"

    cur.execute(sql, tuple(params))
    users = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'admin/users.html',
        users=users,
        q=q,
        role=role
    )

@app.route('/admin/submissions')
@login_required
@role_required('admin')
def admin_submissions():
    q = request.args.get('q', '').strip()
    event_filter = request.args.get('event_id', type=int)
    result_filter = request.args.get('result', '').strip()

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT event_id, event_name
        FROM events
        ORDER BY start_time DESC
    """)
    events = cur.fetchall()

    sql = """
        SELECT
            s.sub_id,
            s.submitted_output,
            s.is_correct,
            s.score_awarded,
            s.submitted_at,
            u.name AS participant_name,
            u.email AS participant_email,
            t.team_name,
            e.event_name,
            p.title AS problem_title
        FROM submissions s
        JOIN users u ON u.user_id = s.user_id
        JOIN teams t ON t.team_id = s.team_id
        JOIN events e ON e.event_id = s.event_id
        JOIN problems p ON p.problem_id = s.problem_id
        WHERE 1=1
    """
    params = []

    if q:
        sql += """
            AND (
                u.name LIKE %s OR
                u.email LIKE %s OR
                t.team_name LIKE %s OR
                e.event_name LIKE %s OR
                p.title LIKE %s OR
                s.submitted_output LIKE %s
            )
        """
        like_q = f"%{q}%"
        params.extend([like_q, like_q, like_q, like_q, like_q, like_q])

    if event_filter:
        sql += " AND s.event_id = %s"
        params.append(event_filter)

    if result_filter == 'correct':
        sql += " AND s.is_correct = 1"
    elif result_filter == 'wrong':
        sql += " AND s.is_correct = 0"

    sql += " ORDER BY s.submitted_at DESC"

    cur.execute(sql, tuple(params))
    submissions = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'admin/submissions.html',
        submissions=submissions,
        events=events,
        q=q,
        event_filter=event_filter,
        result_filter=result_filter
    )


# ══════════════════════════════════════════════
# PARTICIPANT PORTAL
# ══════════════════════════════════════════════
@app.route('/participant')
@login_required
@role_required('participant')
def participant_dashboard():
    uid = session['user_id']

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS count FROM events")
    total_events = cur.fetchone()['count']

    cur.execute("""
        SELECT COUNT(DISTINCT t.event_id) AS count
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s
    """, (uid,))
    registered_events = cur.fetchone()['count']

    cur.execute("""
        SELECT COUNT(DISTINCT t.team_id) AS count
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s
    """, (uid,))
    my_teams_count = cur.fetchone()['count']

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM submissions s
        JOIN teams t ON t.team_id = s.team_id
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s
    """, (uid,))
    submissions_count = cur.fetchone()['count']

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM submissions s
        JOIN teams t ON t.team_id = s.team_id
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s AND s.is_correct = 1
    """, (uid,))
    correct_count = cur.fetchone()['count']

    cur.execute("""
        SELECT COALESCE(SUM(s.score_awarded), 0) AS total
        FROM submissions s
        JOIN teams t ON t.team_id = s.team_id
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s AND s.is_correct = 1
    """, (uid,))
    total_points = cur.fetchone()['total']

    cur.execute("""
        SELECT 
            e.*,
            (
                SELECT t2.team_id
                FROM teams t2
                JOIN team_members tm2 ON tm2.team_id = t2.team_id
                WHERE tm2.user_id = %s AND t2.event_id = e.event_id
                LIMIT 1
            ) AS my_team_id,
            (
                SELECT t2.team_name
                FROM teams t2
                JOIN team_members tm2 ON tm2.team_id = t2.team_id
                WHERE tm2.user_id = %s AND t2.event_id = e.event_id
                LIMIT 1
            ) AS my_team_name
        FROM events e
        ORDER BY e.start_time DESC
    """, (uid, uid))
    events = cur.fetchall()

    cur.execute("""
        SELECT 
            t.team_id,
            t.team_name,
            e.event_name,
            e.start_time,
            e.status
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        JOIN events e ON e.event_id = t.event_id
        WHERE tm.user_id = %s
        ORDER BY t.team_id DESC
        LIMIT 5
    """, (uid,))
    my_teams = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'participant/dashboard.html',
        total_events=total_events,
        registered_events=registered_events,
        my_teams_count=my_teams_count,
        submissions_count=submissions_count,
        correct_count=correct_count,
        total_points=total_points,
        events=events,
        my_teams=my_teams
    )

@app.route('/participant/events')
@login_required
@role_required('participant')
def participant_events():
    uid = session['user_id']

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            e.*,
            (
                SELECT t2.team_id
                FROM teams t2
                JOIN team_members tm2 ON tm2.team_id = t2.team_id
                WHERE tm2.user_id = %s AND t2.event_id = e.event_id
                LIMIT 1
            ) AS my_team_id,
            (
                SELECT t2.team_name
                FROM teams t2
                JOIN team_members tm2 ON tm2.team_id = t2.team_id
                WHERE tm2.user_id = %s AND t2.event_id = e.event_id
                LIMIT 1
            ) AS my_team_name,
            (
                SELECT t2.team_id
                FROM teams t2
                JOIN team_members tm2 ON tm2.team_id = t2.team_id
                WHERE tm2.user_id = %s AND t2.event_id = e.event_id
                LIMIT 1
            ) AS registered_team_id,
            (
                SELECT t2.team_name
                FROM teams t2
                JOIN team_members tm2 ON tm2.team_id = t2.team_id
                WHERE tm2.user_id = %s AND t2.event_id = e.event_id
                LIMIT 1
            ) AS registered_team_name
        FROM events e
        ORDER BY e.start_time DESC
    """, (uid, uid, uid, uid))

    events = cur.fetchall()

    cur.close()
    db.close()

    return render_template('participant/events.html', events=events)

@app.route('/participant/event/<int:event_id>')
@login_required
@role_required('participant')
def event_detail(event_id):
    uid = session['user_id']

    db = get_db()
    cur = db.cursor(dictionary=True)

    # Get selected event
    cur.execute("""
        SELECT *
        FROM events
        WHERE event_id = %s
    """, (event_id,))
    event = cur.fetchone()

    if not event:
        cur.close()
        db.close()
        flash('Event not found.', 'danger')
        return redirect(url_for('participant_events'))

    # Get problems under this event
    cur.execute("""
        SELECT *
        FROM problems
        WHERE event_id = %s
        ORDER BY problem_id ASC
    """, (event_id,))
    problems = cur.fetchall()

    # Get participant team for this event
    cur.execute("""
        SELECT t.*
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s AND t.event_id = %s
        LIMIT 1
    """, (uid, event_id))
    my_team = cur.fetchone()

    team_members = []
    solved = []
    hints = []

    if my_team:
        # Get team members
        cur.execute("""
            SELECT u.user_id, u.name, u.email, u.department
            FROM team_members tm
            JOIN users u ON u.user_id = tm.user_id
            WHERE tm.team_id = %s
            ORDER BY u.name ASC
        """, (my_team['team_id'],))
        team_members = cur.fetchall()

        # Get solved problem IDs
        cur.execute("""
            SELECT DISTINCT problem_id
            FROM submissions
            WHERE team_id = %s AND is_correct = 1
        """, (my_team['team_id'],))
        solved = [row['problem_id'] for row in cur.fetchall()]

        # Get advisor hints
        cur.execute("""
            SELECT 
                h.*,
                p.title AS problem_title,
                u.name AS advisor_name
            FROM hints h
            JOIN problems p ON p.problem_id = h.problem_id
            JOIN users u ON u.user_id = h.advisor_id
            WHERE h.team_id = %s
            ORDER BY h.created_at DESC
        """, (my_team['team_id'],))
        hints = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'participant/event_detail.html',
        event=event,
        problems=problems,
        my_team=my_team,
        team_members=team_members,
        solved=solved,
        hints=hints
    )


@app.route('/participant/all-events')
@login_required
@role_required('participant')
def all_events():
    return redirect(url_for('participant_events'))


@app.route('/participant/team/create', methods=['GET', 'POST'])
@login_required
@role_required('participant')
def create_team():
    uid = session['user_id']

    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        team_name = request.form.get('team_name', '').strip()
        event_id = request.form.get('event_id')

        if not event_id:
            flash('Please select an event.', 'warning')
            cur.close()
            db.close()
            return redirect(url_for('create_team'))

        if not team_name:
            flash('Please enter a team name.', 'warning')
            cur.close()
            db.close()
            return redirect(url_for('create_team'))

        event_id = int(event_id)

        # Check if selected event exists and is open
        cur.execute("""
            SELECT *
            FROM events
            WHERE event_id = %s AND status IN ('upcoming', 'ongoing')
        """, (event_id,))
        event = cur.fetchone()

        if not event:
            flash('Selected event is not available for team creation.', 'danger')
            cur.close()
            db.close()
            return redirect(url_for('create_team'))

        # Check if user already has a team for this event
        cur.execute("""
            SELECT t.team_id
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.team_id
            WHERE tm.user_id = %s AND t.event_id = %s
        """, (uid, event_id))

        if cur.fetchone():
            flash('You are already in a team for this event.', 'warning')
            cur.close()
            db.close()
            return redirect(url_for('create_team'))

        try:
            # Insert team
            cur.execute("""
                INSERT INTO teams (team_name, event_id, leader_id)
                VALUES (%s, %s, %s)
            """, (team_name, event_id, uid))

            team_id = cur.lastrowid

            # Add current user as team member
            cur.execute("""
                INSERT INTO team_members (team_id, user_id)
                VALUES (%s, %s)
            """, (team_id, uid))

            # Register team for event
            cur.execute("""
                INSERT INTO event_registrations (event_id, team_id)
                VALUES (%s, %s)
            """, (event_id, team_id))

            db.commit()

            flash(f'Team "{team_name}" created successfully!', 'success')

            cur.close()
            db.close()

            return redirect(url_for('event_detail', event_id=event_id))

        except mysql.connector.IntegrityError:
            db.rollback()
            flash('This team name already exists for the selected event.', 'danger')

    # Show only upcoming/ongoing events in dropdown
    cur.execute("""
        SELECT event_id, event_name, start_time, end_time, status
        FROM events
        WHERE status IN ('upcoming', 'ongoing')
        ORDER BY start_time ASC
    """)
    events = cur.fetchall()

    cur.close()
    db.close()

    return render_template('participant/create_team.html', events=events)

@app.route('/participant/team/<int:team_id>/invite', methods=['POST'])
@login_required
@role_required('participant')
def invite_member(team_id):
    uid = session['user_id']
    email = request.form.get('email', '').strip().lower()

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM teams
        WHERE team_id = %s
    """, (team_id,))
    team = cur.fetchone()

    if not team:
        cur.close()
        db.close()
        flash('Team not found.', 'danger')
        return redirect(url_for('participant_dashboard'))

    if team['leader_id'] != uid:
        cur.close()
        db.close()
        flash('Only the team leader can add members.', 'danger')
        return redirect(url_for('event_detail', event_id=team['event_id']))

    cur.execute("""
        SELECT user_id, name, email, role
        FROM users
        WHERE LOWER(email) = %s AND role = 'participant'
    """, (email,))
    invitee = cur.fetchone()

    if not invitee:
        cur.close()
        db.close()
        flash('No registered participant found with this email.', 'warning')
        return redirect(url_for('event_detail', event_id=team['event_id']))

    cur.execute("""
        SELECT t.team_id
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s AND t.event_id = %s
        LIMIT 1
    """, (invitee['user_id'], team['event_id']))
    existing_team = cur.fetchone()

    if existing_team:
        cur.close()
        db.close()
        flash('This participant is already in a team for this event.', 'warning')
        return redirect(url_for('event_detail', event_id=team['event_id']))

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM team_members
        WHERE team_id = %s
    """, (team_id,))
    current_size = cur.fetchone()['count']

    cur.execute("""
        SELECT max_team_size
        FROM events
        WHERE event_id = %s
    """, (team['event_id'],))
    event = cur.fetchone()

    if current_size >= event['max_team_size']:
        cur.close()
        db.close()
        flash('Team is already full.', 'warning')
        return redirect(url_for('event_detail', event_id=team['event_id']))

    cur.execute("""
        INSERT IGNORE INTO team_members (team_id, user_id)
        VALUES (%s, %s)
    """, (team_id, invitee['user_id']))

    db.commit()

    cur.close()
    db.close()

    flash('Member added successfully!', 'success')
    return redirect(url_for('event_detail', event_id=team['event_id']))


@app.route('/participant/submit/<int:problem_id>', methods=['POST'])
@login_required
@role_required('participant')
def submit_solution(problem_id):
    uid = session['user_id']
    submitted_output = request.form.get('output', '').strip()

    db = get_db()
    cur = db.cursor(dictionary=True)

    # Get problem
    cur.execute("""
        SELECT *
        FROM problems
        WHERE problem_id = %s
    """, (problem_id,))
    problem = cur.fetchone()

    if not problem:
        cur.close()
        db.close()
        flash('Problem not found.', 'danger')
        return redirect(url_for('participant_dashboard'))

    event_id = problem['event_id']

    if not submitted_output:
        cur.close()
        db.close()
        flash('Please enter your output before submitting.', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))

    # Get event
    cur.execute("""
        SELECT *
        FROM events
        WHERE event_id = %s
    """, (event_id,))
    event = cur.fetchone()

    if not event:
        cur.close()
        db.close()
        flash('Event not found.', 'danger')
        return redirect(url_for('participant_events'))

    # Only ongoing event can accept submission
    if event['status'] != 'ongoing':
        cur.close()
        db.close()
        flash('Submission is only allowed when event is ongoing.', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))

    # Get participant team
    cur.execute("""
        SELECT t.*
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s AND t.event_id = %s
        LIMIT 1
    """, (uid, event_id,))
    team = cur.fetchone()

    if not team:
        cur.close()
        db.close()
        flash('You must create or join a team before submitting.', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))

    # Prevent solving same problem twice
    cur.execute("""
        SELECT sub_id
        FROM submissions
        WHERE problem_id = %s
          AND team_id = %s
          AND is_correct = 1
        LIMIT 1
    """, (problem_id, team['team_id']))
    already_solved = cur.fetchone()

    if already_solved:
        cur.close()
        db.close()
        flash('Your team already solved this problem.', 'info')
        return redirect(url_for('event_detail', event_id=event_id))

    # Compare answer
    correct_output = problem['correct_output'].strip()
    is_correct = submitted_output == correct_output

    # Score calculation
    now = datetime.now()
    elapsed_minutes = max(0, (now - event['start_time']).total_seconds() / 60)

    base_score = int(problem['base_score'])
    min_score = int(problem['min_score'])
    decay_interval = int(problem['decay_interval'])
    decay_amount = int(problem['decay_amount'])

    intervals_passed = int(elapsed_minutes // decay_interval)
    score = max(min_score, base_score - (intervals_passed * decay_amount))

    if not is_correct:
        score = 0

    # Save submission
    cur.execute("""
        INSERT INTO submissions
        (problem_id, user_id, team_id, event_id, submitted_output, is_correct, score_awarded)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        problem_id,
        uid,
        team['team_id'],
        event_id,
        submitted_output,
        is_correct,
        score
    ))

    db.commit()

    cur.close()
    db.close()

    if is_correct:
        flash(f'Correct! You earned {score} points.', 'success')
    else:
        flash('Wrong answer. Try again.', 'danger')

    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/participant/scores')
@login_required
@role_required('participant')
def my_scores():
    uid = session['user_id']

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            s.*,
            p.title AS problem_title,
            e.event_name,
            t.team_name
        FROM submissions s
        JOIN problems p ON p.problem_id = s.problem_id
        JOIN events e ON e.event_id = s.event_id
        JOIN teams t ON t.team_id = s.team_id
        WHERE s.user_id = %s
        ORDER BY s.submitted_at DESC
    """, (uid,))

    submissions = cur.fetchall()

    cur.close()
    db.close()

    return render_template('participant/my_scores.html', submissions=submissions)

@app.route('/participant/profile')
@login_required
@role_required('participant')
def participant_profile():
    uid = session['user_id']

    db = get_db()
    cur = db.cursor(dictionary=True)

    # Get participant basic information
    cur.execute("""
        SELECT user_id, name, email, department, role, created_at, profile_image
        FROM users
        WHERE user_id = %s
    """, (uid,))
    user = cur.fetchone()

    # Count registered events
    cur.execute("""
        SELECT COUNT(DISTINCT t.event_id) AS count
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s
    """, (uid,))
    registered_events = cur.fetchone()['count']

    # Count teams
    cur.execute("""
        SELECT COUNT(DISTINCT t.team_id) AS count
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        WHERE tm.user_id = %s
    """, (uid,))
    total_teams = cur.fetchone()['count']

    # Count total submissions by this participant
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM submissions
        WHERE user_id = %s
    """, (uid,))
    total_submissions = cur.fetchone()['count']

    # Count correct submissions by this participant
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM submissions
        WHERE user_id = %s AND is_correct = 1
    """, (uid,))
    correct_submissions = cur.fetchone()['count']

    # Count wrong submissions
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM submissions
        WHERE user_id = %s AND is_correct = 0
    """, (uid,))
    wrong_submissions = cur.fetchone()['count']

    # Total points earned by this participant
    cur.execute("""
        SELECT COALESCE(SUM(score_awarded), 0) AS total
        FROM submissions
        WHERE user_id = %s AND is_correct = 1
    """, (uid,))
    total_points = cur.fetchone()['total']

    # Participant teams list
    cur.execute("""
        SELECT 
            t.team_id,
            t.team_name,
            e.event_name,
            e.status,
            e.start_time,
            e.end_time
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id
        JOIN events e ON e.event_id = t.event_id
        WHERE tm.user_id = %s
        ORDER BY t.team_id DESC
    """, (uid,))
    my_teams = cur.fetchall()

    # Recent submissions
    cur.execute("""
        SELECT 
            s.sub_id,
            s.submitted_output,
            s.is_correct,
            s.score_awarded,
            s.submitted_at,
            p.title AS problem_title,
            e.event_name,
            t.team_name
        FROM submissions s
        JOIN problems p ON p.problem_id = s.problem_id
        JOIN events e ON e.event_id = s.event_id
        JOIN teams t ON t.team_id = s.team_id
        WHERE s.user_id = %s
        ORDER BY s.submitted_at DESC
        LIMIT 10
    """, (uid,))
    recent_submissions = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'participant/profile.html',
        user=user,
        registered_events=registered_events,
        total_teams=total_teams,
        total_submissions=total_submissions,
        correct_submissions=correct_submissions,
        wrong_submissions=wrong_submissions,
        total_points=total_points,
        my_teams=my_teams,
        recent_submissions=recent_submissions
    )


@app.route('/participant/profile/photo', methods=['POST'])
@login_required
@role_required('participant')
def upload_profile_photo():
    uid = session['user_id']

    if 'profile_photo' not in request.files:
        flash('No image file selected.', 'warning')
        return redirect(url_for('participant_profile'))

    file = request.files['profile_photo']

    if file.filename == '':
        flash('Please choose an image file.', 'warning')
        return redirect(url_for('participant_profile'))

    if not allowed_image_file(file.filename):
        flash('Only PNG, JPG, JPEG, and WEBP images are allowed.', 'danger')
        return redirect(url_for('participant_profile'))

    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit('.', 1)[1].lower()

    new_filename = f"user_{uid}_{uuid4().hex}.{extension}"
    save_path = os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], new_filename)

    file.save(save_path)

    image_db_path = f"uploads/profile/{new_filename}"

    db = get_db()
    cur = db.cursor(dictionary=True)

    # Get old image to remove it from folder
    cur.execute("""
        SELECT profile_image
        FROM users
        WHERE user_id = %s
    """, (uid,))
    old_user = cur.fetchone()

    # Update database with new image path
    cur.execute("""
        UPDATE users
        SET profile_image = %s
        WHERE user_id = %s
    """, (image_db_path, uid))

    db.commit()

    cur.close()
    db.close()

    # Delete old image if available
    if old_user and old_user.get('profile_image'):
        old_image_path = os.path.join(app.static_folder, old_user['profile_image'])
        if os.path.exists(old_image_path):
            try:
                os.remove(old_image_path)
            except OSError:
                pass

    flash('Profile picture updated successfully.', 'success')
    return redirect(url_for('participant_profile'))
# ══════════════════════════════════════════════
# LEADERBOARD
# ══════════════════════════════════════════════

@app.route('/leaderboard')
@app.route('/leaderboard/<int:event_id>')
@login_required
def leaderboard(event_id=None):
    db = get_db()
    cur = db.cursor(dictionary=True)

    # If event_id comes from dropdown query parameter
    selected_event_id = event_id or request.args.get('event_id', type=int)

    # Get all events for dropdown
    cur.execute("""
        SELECT event_id, event_name, status, start_time, end_time
        FROM events
        ORDER BY start_time DESC
    """)
    events = cur.fetchall()

    # If no event exists yet
    if not events:
        cur.close()
        db.close()

        return render_template(
            'leaderboard.html',
            events=[],
            event=None,
            board=[],
            total_problems=0,
            total_teams=0,
            top_score=0
        )

    # If no event selected, choose latest event
    if not selected_event_id:
        selected_event_id = events[0]['event_id']

    # Get selected event
    cur.execute("""
        SELECT event_id, event_name, description, status, start_time, end_time
        FROM events
        WHERE event_id = %s
    """, (selected_event_id,))
    event = cur.fetchone()

    if not event:
        cur.close()
        db.close()
        flash('Event not found for leaderboard.', 'warning')
        return redirect(url_for('leaderboard'))

    # Count total problems in selected event
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM problems
        WHERE event_id = %s
    """, (selected_event_id,))
    total_problems = cur.fetchone()['count']

    # Premium leaderboard query
    cur.execute("""
        SELECT
            t.team_id,
            t.team_name,
            leader.name AS leader_name,
            leader.email AS leader_email,

            COALESCE(member_stats.member_count, 0) AS member_count,

            COALESCE(score_stats.solved, 0) AS solved,
            COALESCE(score_stats.total_score, 0) AS total_score,
            COALESCE(score_stats.total_submissions, 0) AS total_submissions,
            COALESCE(score_stats.wrong_attempts, 0) AS wrong_attempts,

            score_stats.first_solve_time,
            score_stats.last_solve_time

        FROM teams t

        JOIN users leader
            ON leader.user_id = t.leader_id

        LEFT JOIN (
            SELECT
                team_id,
                COUNT(*) AS member_count
            FROM team_members
            GROUP BY team_id
        ) AS member_stats
            ON member_stats.team_id = t.team_id

        LEFT JOIN (
            SELECT
                team_id,
                COUNT(*) AS total_submissions,

                COUNT(DISTINCT CASE
                    WHEN is_correct = 1 THEN problem_id
                END) AS solved,

                COALESCE(SUM(CASE
                    WHEN is_correct = 1 THEN score_awarded
                    ELSE 0
                END), 0) AS total_score,

                SUM(CASE
                    WHEN is_correct = 0 THEN 1
                    ELSE 0
                END) AS wrong_attempts,

                MIN(CASE
                    WHEN is_correct = 1 THEN submitted_at
                END) AS first_solve_time,

                MAX(CASE
                    WHEN is_correct = 1 THEN submitted_at
                END) AS last_solve_time

            FROM submissions
            WHERE event_id = %s
            GROUP BY team_id
        ) AS score_stats
            ON score_stats.team_id = t.team_id

        WHERE t.event_id = %s

        ORDER BY
            COALESCE(score_stats.total_score, 0) DESC,
            COALESCE(score_stats.solved, 0) DESC,
            score_stats.first_solve_time IS NULL ASC,
            score_stats.first_solve_time ASC,
            COALESCE(score_stats.wrong_attempts, 0) ASC,
            t.team_name ASC
    """, (selected_event_id, selected_event_id))

    board = cur.fetchall()

    cur.close()
    db.close()

    total_teams = len(board)
    top_score = board[0]['total_score'] if board else 0

    return render_template(
        'leaderboard.html',
        events=events,
        event=event,
        board=board,
        total_problems=total_problems,
        total_teams=total_teams,
        top_score=top_score
    )
if __name__ == '__main__':
    app.run(debug=True, port=5000)
