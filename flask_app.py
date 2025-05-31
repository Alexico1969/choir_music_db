from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from database import init_db, get_db_connection
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from secret import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_DISCOVERY_URL
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-fixed-secret-key-here'  # Use a fixed key instead of random

# Move OAuth config right after app creation
oauth = OAuth(app)
google = oauth.register(
    name='google',
    server_metadata_url=GOOGLE_DISCOVERY_URL,
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account'  # Force Google account selection
    }
)

class User(UserMixin):
    def __init__(self, email):
        self.id = email
        self.email = email

    def get_id(self):
        return str(self.id)

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

@app.route('/api/songs/<letter_range>')
def get_songs_in_range(letter_range):
    """API endpoint to get songs by letter range"""
    start, end = letter_range.split('-')
    conn = get_db_connection()
    songs = conn.execute(
        'SELECT * FROM songs WHERE title >= ? AND title < ? ORDER BY title',
        (start, chr(ord(end) + 1))
    ).fetchall()
    conn.close()
    return jsonify([dict(song) for song in songs])

@app.route('/api/song/<int:song_id>')
def get_song(song_id):
    """API endpoint to get detailed song information"""
    conn = get_db_connection()
    song = conn.execute('SELECT * FROM songs WHERE id = ?', (song_id,)).fetchone()
    conn.close()
    
    if song is None:
        return jsonify({'error': 'Song not found'}), 404
    return jsonify(dict(song))

@app.route('/add_song', methods=['GET', 'POST'])
@login_required
def add_song():
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

@app.route('/edit_song', methods=['GET', 'POST'])
@login_required
def edit_song():
    print("Accessing /edit_song, current_user:", current_user.is_authenticated)
    if request.method == 'GET':
        song_id = request.args.get('id')
        if song_id:
            conn = get_db_connection()
            song = conn.execute('SELECT * FROM songs WHERE id = ?', (song_id,)).fetchone()
            conn.close()
            return render_template('edit_song.html', song=song)
        return render_template('edit_song.html')
    
    # POST handling
    song_id = request.form['song_id']
    title = request.form['title']
    composer = request.form['composer']
    arrangement = request.form['arrangement']
    key_signature = request.form['key']
    difficulty = request.form['difficulty']
    description = request.form.get('description', '')
    
    # Handle file uploads (similar to add_song)
    pdf_filename = request.form.get('current_pdf')
    audio_filename = request.form.get('current_audio')
    
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
    
    # Update database
    conn = get_db_connection()
    conn.execute(
        '''UPDATE songs SET title=?, composer=?, arrangement=?, key_signature=?, 
           difficulty=?, description=?, pdf_filename=?, audio_filename=? 
           WHERE id=?''',
        (title, composer, arrangement, key_signature, difficulty, description, 
         pdf_filename, audio_filename, song_id)
    )
    conn.commit()
    conn.close()
    
    flash('Song updated successfully!')
    return redirect(url_for('home'))

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

@app.route('/login')
def login():
    #session.clear()  # Clear any existing session
    next_url = request.args.get('next', url_for('home'))
    session['next_url'] = next_url
    redirect_uri = url_for('authorize', _external=True)  # Ensure this matches Google Cloud Console
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    try:
        # Attempt to retrieve the token
        token = google.authorize_access_token()
        if not token:
            raise ValueError("No token received from Google")
        session['debug_token'] = token  # Store token in session for debugging
        print(f"Token received: {token}")  # Debug: Check if token is received

        # Attempt to parse the user info
        # You MUST extract the nonce used during redirect
        # It’s embedded in the _state_google_* key
        nonce = token.get('userinfo', {}).get('nonce') or None
        if not nonce:
            # fallback: try to find nonce manually
            for key in session:
                if key.startswith('_state_google_') and 'nonce' in session[key]['data']:
                    nonce = session[key]['data']['nonce']
                    break

        user_info = google.parse_id_token(token, nonce=nonce)
        
        if not user_info:
            raise ValueError("No user info received from Google")
        session['debug_user_info'] = user_info  # Store user info in session for debugging
        print(f"User info: {user_info}")  # Debug: Check user info

        # Extract the email
        user_email = user_info.get('email')
        if not user_email:
            raise ValueError("No email provided by Google")

        # Create and log in the user
        user = User(user_email)
        login_user(user, remember=True)
        session['user_email'] = user_email
        session.permanent = True

        # Debug logging
        session['debug_login'] = {
            'user_email': user_email,
            'authenticated': current_user.is_authenticated,
            'session_data': dict(session)
        }
        print(f"Login successful for: {user_email}")
        print(f"Session data: {dict(session)}")
        print(f"User authenticated: {current_user.is_authenticated}")

        # Redirect to the next URL
        next_url = session.pop('next_url', url_for('home'))

        print("IS AUTH:", current_user.is_authenticated)
        print("USER ID:", current_user.get_id())
        print("SESSION:", dict(session))
        return redirect(next_url)

    except Exception as e:
        # Log the error for debugging
        session['debug_error'] = str(e)  # Store error in session for debugging
        print(f"Authorization failed: {str(e)}")
        flash('Login failed. Please try again.')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    logout_user()
    session.clear()  # Clear entire session
    flash('You have been logged out.')
    return redirect(url_for('home'))

@app.route('/debug')
def debug():
    return {
        'authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if current_user.is_authenticated else None,
        'session': dict(session),
        'debug_token': session.get('debug_token'),
        'debug_user_info': session.get('debug_user_info'),
        'debug_login': session.get('debug_login'),
        'debug_error': session.get('debug_error')
    }

if __name__ == '__main__':
    # Create upload directories if they don't exist
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'pdfs'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
    
    app.run(debug=True)

