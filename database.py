import sqlite3
import os

DATABASE = 'instance/choir_music.db'

def run_once():
    # run ALTER TABLE songs ADD COLUMN lyrics_filename TEXT; once
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE songs ADD COLUMN lyrics_filename TEXT;')
        conn.commit()
    except sqlite3.OperationalError:
        # If the column already exists, ignore the error
        pass
    finally:
        conn.close()

    


def get_db_connection():
    """Get a database connection with row factory for dict-like access"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    # Create instance directory if it doesn't exist
    os.makedirs('instance', exist_ok=True)
    
    conn = get_db_connection()
    
    # Create songs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            composer TEXT,
            arrangement TEXT,
            key_signature TEXT,
            difficulty TEXT,
            description TEXT,
            pdf_filename TEXT,
            audio_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for better performance
    conn.execute('CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_songs_composer ON songs(composer)')
    
    # Insert sample data if table is empty
    count = conn.execute('SELECT COUNT(*) FROM songs').fetchone()[0]
    if count == 0:
        sample_songs = [
            ('Amazing Grace', 'Traditional', 'SATB', 'G Major', 'Easy', 'Traditional hymn'),
            ('Ave Maria', 'Traditional', 'Chant, Mode I', 'C Major', 'Medium', 'Hail Mary'),
            ('Eat This Bread', 'Jacques Berthier', 'With refrain', 'F Major', 'Easy', 'Communion hymn by Jacques Berthier'),
            ('In the Breaking of the Bread', 'Traditional', '4 verses', 'D Major', 'Medium', 'Communion hymn'),
            ('Lead Me, Lord', 'John D. Becker', 'SATB', 'Bb Major', 'Medium', 'Contemporary hymn by John D. Becker'),
            ('Salve Regina', 'Traditional', 'Chant, Mode I', 'G Major', 'Hard', 'Hail Mary, Mother and Queen'),
            ('Sing of the Lord\'s Goodness', 'Ernest Sands', 'Praise hymn', 'C Major', 'Easy', 'Praise hymn by Ernest Sands')
        ]
        
        conn.executemany(
            'INSERT INTO songs (title, composer, arrangement, key_signature, difficulty, description) VALUES (?, ?, ?, ?, ?, ?)',
            sample_songs
        )
    
    conn.commit()
    conn.close()

def insert_song(title, composer, arrangement, key_signature, difficulty, description, pdf_filename, audio_filename, lyrics_filename):
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO songs (title, composer, arrangement, key_signature, difficulty, 
           description, pdf_filename, audio_filename, lyrics_filename) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (title, composer, arrangement, key_signature, difficulty, description, 
         pdf_filename, audio_filename, lyrics_filename)
    )
    conn.commit()
    conn.close()

def update_song(song_id, title, composer, arrangement, key_signature, difficulty, description, pdf_filename, audio_filename, lyrics_filename):
    conn = get_db_connection()
    conn.execute(
        '''UPDATE songs
           SET title = ?, composer = ?, arrangement = ?, key_signature = ?, difficulty = ?, description = ?, pdf_filename = ?, audio_filename = ?, lyrics_filename = ?
           WHERE id = ?''',
        (title, composer, arrangement, key_signature, difficulty, description, pdf_filename, audio_filename, lyrics_filename, song_id)
    )
    conn.commit()
    conn.close()
