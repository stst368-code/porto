"""SQLite schema and connection setup."""
import sqlite3

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS generations (
 id TEXT PRIMARY KEY, audio_hash TEXT, audio_path TEXT, yaml_path TEXT, source_root TEXT,
 title TEXT, cluster TEXT, version TEXT, model TEXT, dit TEXT, text_encoder TEXT,
 encoder_cfg REAL, encoder_seed TEXT, top_k INTEGER, sampler_cfg REAL, sampler_seed TEXT,
 sampler_steps INTEGER, sampler TEXT, scheduler TEXT,
 caption_chars INTEGER, caption_words INTEGER, caption_lines INTEGER, caption_avg_word_length REAL,
 lyrics_chars INTEGER, lyrics_words INTEGER, lyrics_lines INTEGER, lyrics_avg_word_length REAL,
 avg_lyric_line_words REAL, lyric_sections INTEGER, section_counts TEXT,
 quality_score INTEGER, quality_folder TEXT, published INTEGER DEFAULT 0, catalogue_id TEXT,
 scan_time TEXT, missing_audio INTEGER NOT NULL DEFAULT 0, missing_yaml INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS audio_metrics (
 generation_id TEXT PRIMARY KEY REFERENCES generations(id) ON DELETE CASCADE,
 analysis_path TEXT, analysis_hash TEXT, audio_source_hash TEXT, format TEXT,
 duration REAL, bpm REAL, rms_db REAL, peak_db REAL, onset_density REAL,
 frames INTEGER, beats INTEGER, events INTEGER, frame_hz REAL,
 energy_mean REAL, energy_std REAL, bass_mean REAL, bass_std REAL,
 brightness_mean REAL, brightness_std REAL, change_mean REAL, change_std REAL,
 raw_json_gz BLOB
);
CREATE TABLE IF NOT EXISTS ratings_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, generation_id TEXT NOT NULL, score INTEGER NOT NULL,
 folder TEXT NOT NULL, observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scan_errors (
 id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT, message TEXT, observed_at TEXT
);
CREATE TABLE IF NOT EXISTS analysis_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT, generation_count INTEGER, config_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_gen_title ON generations(title);
CREATE INDEX IF NOT EXISTS ix_gen_genre ON generations(cluster,version);
CREATE INDEX IF NOT EXISTS ix_gen_score ON generations(quality_score);
'''

def connect(path):
    db=sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    return db
