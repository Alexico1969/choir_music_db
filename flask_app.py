from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
import os
from werkzeug.utils import secure_filename
from database import init_db, get_db_connection, run_once
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import timedelta
from secret import code

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-fixed-secret-key-here'  # Use a fixed key instead of random

#run_once()

class User(UserMixin):
    def __init__(self, email):
        self.id = email
        self.email = email

    def get_id(self):
        return str(self.id)

def nocache(view):
    def no_cache_wrapper(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    no_cache_wrapper.__name__ = view.__name__
    return no_cache_wrapper

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id else None

# Add session persistence
@app.before_request
def make_session_permanent():
    if current_user.is_authenticated:
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=31)


app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'pdf', 'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database on startup
with app.app_context():
    init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/api/songs', methods=['GET'])
@app.route('/api/songs/<letter_range>', methods=['GET'])
def get_songs(letter_range=None):
    conn = get_db_connection()
    if letter_range:
        start, end = letter_range.split('-')
        # Only get songs where the first letter is in the range (case-insensitive)
        songs = conn.execute(
            '''SELECT * FROM songs
               WHERE UPPER(SUBSTR(title, 1, 1)) >= ? AND UPPER(SUBSTR(title, 1, 1)) <= ?
               ORDER BY title''',
            (start.upper(), end.upper())
        ).fetchall()
    else:
        songs = conn.execute('SELECT * FROM songs ORDER BY title').fetchall()
    conn.close()
    return jsonify([dict(song) for song in songs])

@app.route('/api/song/<int:song_id>')
def get_song(song_id):
    conn = get_db_connection()
    song = conn.execute('SELECT * FROM songs WHERE id = ?', (song_id,)).fetchone()
    conn.close()
    if song is None:
        return jsonify({'error': 'Song not found'}), 404
    return jsonify(dict(song))

@app.route('/add_song', methods=['GET', 'POST'])
def add_song():
    if 'auth_code' not in session or session['auth_code'] != code:
        flash('Please enter the correct code to access this page.')
        return redirect(url_for('verify_code', next=request.url))

    if request.method == 'GET':
        return render_template('add_song.html')

    # POST handling
    title = request.form['title']
    composer = request.form['composer']
    arrangement = request.form['arrangement']
    key_signature = request.form['key']
    difficulty = request.form['difficulty']
    description = request.form.get('description', '')

    # Handle file uploads
    pdf_filename = None
    audio_filename = None
    lyrics_filename = None

    if 'pdf_file' in request.files:
        pdf_file = request.files['pdf_file']
        if pdf_file and allowed_file(pdf_file.filename):
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'pdfs', pdf_filename))

    if 'audio_file' in request.files:
        audio_file = request.files['audio_file']
        if audio_file and allowed_file(audio_file.filename):
            audio_filename = secure_filename(audio_file.filename)
            audio_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'audio', audio_filename))

    if 'lyrics_file' in request.files:
        lyrics_file = request.files['lyrics_file']
        if lyrics_file and allowed_file(lyrics_file.filename):
            lyrics_filename = secure_filename(lyrics_file.filename)
            lyrics_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'lyrics', lyrics_filename))

    # Insert into database
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO songs (title, composer, arrangement, key_signature, difficulty, 
           description, pdf_filename, audio_filename) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (title, composer, arrangement, key_signature, difficulty, description, 
         pdf_filename, audio_filename)
    )
    conn.commit()
    conn.close()

    flash('Song added successfully!')
    return redirect(url_for('home'))


@app.route('/edit_song', methods=['GET'])
def edit_song():
    if 'auth_code' not in session or session['auth_code'] != code:
        flash('Please enter the correct code to edit songs.')
        return redirect(url_for('verify_code', next=request.url))

    conn = get_db_connection()
    songs = conn.execute('SELECT * FROM songs ORDER BY title').fetchall()
    conn.close()
    return render_template('edit_song.html', songs=songs)

@app.route('/dump')
def dump():
    conn = get_db_connection()
    songs = conn.execute('SELECT * FROM songs ORDER BY title').fetchall()
    conn.close()
    return render_template('dump.html', songs=songs)

@app.route('/api/song/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    try:
        conn = get_db_connection()
        
        # Get song info for file deletion
        song = conn.execute('SELECT pdf_filename, audio_filename FROM songs WHERE id = ?', 
                          (song_id,)).fetchone()
        
        if song:
            # Delete files if they exist
            if song['pdf_filename']:
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'pdfs', song['pdf_filename'])
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            
            if song['audio_filename']:
                audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', song['audio_filename'])
                if os.path.exists(audio_path):
                    os.remove(audio_path)
        
        # Delete from database
        conn.execute('DELETE FROM songs WHERE id = ?', (song_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Song deleted successfully'}), 200
    except Exception as e:
        print(f"Error deleting song: {e}")
        return jsonify({'error': 'Failed to delete song'}), 500

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.')
    response = redirect(url_for('home'))
    response.set_cookie('session', '', expires=0)
    return response


@app.route('/debug')
def debug():
    return {
        'authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if current_user.is_authenticated else None,
        'session': dict(session),
    }

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        entered_code = request.form['code']
        if entered_code == code:
            session['auth_code'] = code
            next_url = request.args.get('next') or url_for('home')
            return redirect(next_url)
        else:
            flash('Incorrect code. Please try again.')
            return redirect(url_for('verify_code', next=request.args.get('next')))

    return render_template('verify_code.html')

@app.route('/reset')
def reset_permissions():
    # Clear the auth_code from the session
    session.pop('auth_code', None)
    flash('Permissions have been reset. You will need to re-enter the access code to add or edit songs.')
    return redirect(url_for('home'))

@app.route('/edit_song/<int:song_id>', methods=['POST'])
def update_song(song_id):
    if 'auth_code' not in session or session['auth_code'] != code:
        flash('Please enter the correct code to edit this song.')
        return redirect(url_for('verify_code', next=request.url))

    title = request.form['title']
    composer = request.form['composer']
    arrangement = request.form['arrangement']
    key_signature = request.form['key']
    difficulty = request.form['difficulty']
    description = request.form['description']

    # Handle file uploads
    pdf_filename = None
    audio_filename = None
    lyrics_filename = None

    if 'pdf_file' in request.files:
        pdf_file = request.files['pdf_file']
        if pdf_file and allowed_file(pdf_file.filename):
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'pdfs', pdf_filename))

    if 'audio_file' in request.files:
        audio_file = request.files['audio_file']
        if audio_file and allowed_file(audio_file.filename):
            audio_filename = secure_filename(audio_file.filename)
            audio_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'audio', audio_filename))

    if 'lyrics_file' in request.files:
        lyrics_file = request.files['lyrics_file']
        if lyrics_file and allowed_file(lyrics_file.filename):
            lyrics_filename = secure_filename(lyrics_file.filename)
            lyrics_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'lyrics', lyrics_filename))

    conn = get_db_connection()
    # Get the current song info
    song = conn.execute('SELECT * FROM songs WHERE id = ?', (song_id,)).fetchone()

    # Use the old filename if no new file was uploaded
    if not pdf_filename:
        pdf_filename = song['pdf_filename']
    if not audio_filename:
        audio_filename = song['audio_filename']
    if not lyrics_filename:
        lyrics_filename = song['lyrics_filename']

    # Now update, using the correct filename
    conn.execute(
        '''UPDATE songs
           SET title = ?, composer = ?, arrangement = ?, key_signature = ?, difficulty = ?, description = ?, pdf_filename = ?, audio_filename = ?, lyrics_filename = ?
           WHERE id = ?''',
        (title, composer, arrangement, key_signature, difficulty, description, pdf_filename, audio_filename, lyrics_filename, song_id)
    )
    conn.commit()
    conn.close()

    flash('Song updated successfully!')
    return redirect(url_for('edit_song'))

@app.route('/event', methods=['GET'])
def event():
    if 'auth_code' not in session or session['auth_code'] != code:
        flash('Please enter the correct code to edit this song.')
        return redirect(url_for('verify_code', next=request.url))
    conn = get_db_connection()
    songs = conn.execute('SELECT * FROM songs ORDER BY title').fetchall()
    selected_songs = conn.execute('SELECT * FROM songs WHERE difficulty IS NOT NULL ORDER BY CAST(difficulty AS INTEGER)').fetchall()
    conn.close()
    return render_template('event.html', songs=songs, selected_songs=selected_songs)

@app.route('/select_songs', methods=['POST'])
def select_songs():
    if 'auth_code' not in session or session['auth_code'] != code:
        flash('Please enter the correct code to edit this song.')
        return redirect(url_for('verify_code', next=request.url))
    song_ids = request.json.get('song_ids', [])
    conn = get_db_connection()
    for song_id in song_ids:
        # Get current description
        song = conn.execute('SELECT description FROM songs WHERE id = ?', (song_id,)).fetchone()
        desc = song['description'] if song and song['description'] else ''
        # Add 'S-' if not already present
        if not desc.startswith('S-'):
            desc = 'S-' + desc
        conn.execute('UPDATE songs SET description = ? WHERE id = ?', (desc, song_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/save_setlist', methods=['POST'])
def save_setlist():
    song_ids = request.json.get('song_ids', [])
    conn = get_db_connection()
    # Reset difficulty for all songs
    conn.execute('UPDATE songs SET difficulty = NULL')
    # Set difficulty for songs in setlist
    for idx, song_id in enumerate(song_ids, start=1):
        conn.execute('UPDATE songs SET difficulty = ? WHERE id = ?', (idx, song_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/live')
def live():
    import os
    selected_songs = []
    conn = get_db_connection()
    for song in conn.execute(
        'SELECT * FROM songs WHERE difficulty IS NOT NULL ORDER BY CAST(difficulty AS INTEGER)'
    ).fetchall():
        lyrics = None
        if song['lyrics_filename']:
            lyrics_path = os.path.join('static', 'uploads', 'lyrics', song['lyrics_filename'])
            print(f"Trying to read: {lyrics_path}")  # Debug
            try:
                with open(lyrics_path, encoding='utf-8') as f:
                    lyrics = f.read().strip() or None
                print(f"Lyrics for {song['title']}: {lyrics[:30]}...")  # Debug
            except Exception as e:
                print(f"Error reading {lyrics_path}: {e}")
                lyrics = None
        song_dict = dict(song)
        song_dict['lyrics'] = lyrics
        selected_songs.append(song_dict)
    conn.close()
    return render_template('live.html', selected_songs=selected_songs)

if __name__ == '__main__':
    # Create upload directories if they don't exist
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'pdfs'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'lyrics'), exist_ok=True)
    
    app.run(debug=True)

