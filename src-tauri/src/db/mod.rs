use super::*;

pub(crate) const SQLITE_BUSY_TIMEOUT_MS: u64 = 750;

pub(crate) fn configure_connection(connection: &Connection) -> rusqlite::Result<()> {
    connection.busy_timeout(Duration::from_millis(SQLITE_BUSY_TIMEOUT_MS))?;
    Ok(())
}

pub(crate) fn migrate(connection: &Connection) -> rusqlite::Result<()> {
    configure_connection(connection)?;
    connection.execute_batch(
        "
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            progress REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'queued',
            cancel_cleanup INTEGER NOT NULL DEFAULT 1,
            priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal','low')),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS download_jobs (
            job_id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            destination TEXT NOT NULL,
            temp_path TEXT NOT NULL,
            total_bytes INTEGER,
            downloaded_bytes INTEGER NOT NULL DEFAULT 0,
            resumable INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            http_engine_attempts INTEGER NOT NULL DEFAULT 0,
            remote_size INTEGER,
            strong_etag TEXT,
            last_modified TEXT,
            representation_fingerprint TEXT NOT NULL DEFAULT '',
            ownership_generation INTEGER NOT NULL DEFAULT 0,
            ownership_token TEXT NOT NULL DEFAULT '',
            finalization_state TEXT NOT NULL DEFAULT 'none',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS torrent_jobs (
            job_id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            destination_dir TEXT NOT NULL,
            total_bytes INTEGER,
            downloaded_bytes INTEGER NOT NULL DEFAULT 0,
            speed_bps REAL NOT NULL DEFAULT 0,
            eta_seconds INTEGER,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS recent_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'Archivos',
            kind TEXT NOT NULL DEFAULT 'doc',
            opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS download_speed_limits (
            job_id INTEGER PRIMARY KEY,
            bytes_per_second INTEGER NOT NULL DEFAULT 0 CHECK(bytes_per_second >= 0),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS playlist_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            format TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            current_position INTEGER NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal','low')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            source_id TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            creator TEXT NOT NULL DEFAULT '',
            thumbnail TEXT NOT NULL DEFAULT '',
            duration_label TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            progress REAL NOT NULL DEFAULT 0,
            job_id INTEGER,
            output_path TEXT,
            FOREIGN KEY(batch_id) REFERENCES playlist_batches(id) ON DELETE CASCADE,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS media_jobs (
            job_id INTEGER PRIMARY KEY,
            source_url TEXT NOT NULL,
            format_selector TEXT NOT NULL,
            output_mode TEXT NOT NULL,
            destination_dir TEXT NOT NULL,
            output_path TEXT,
            thumbnail TEXT NOT NULL DEFAULT '',
            expected_duration_seconds REAL,
            playlist_batch_id INTEGER,
            playlist_item_id INTEGER,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY(playlist_batch_id) REFERENCES playlist_batches(id) ON DELETE CASCADE,
            FOREIGN KEY(playlist_item_id) REFERENCES playlist_items(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS saved_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS download_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            action TEXT NOT NULL,
            run_at TEXT NOT NULL,
            repeat_daily INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS progress_v2_jobs (
            job_id INTEGER PRIMARY KEY,
            schema_version INTEGER NOT NULL DEFAULT 1,
            attempt INTEGER NOT NULL DEFAULT 0,
            phase TEXT NOT NULL,
            stage TEXT,
            downloaded_bytes INTEGER NOT NULL DEFAULT 0,
            transfer_total INTEGER,
            total_kind TEXT NOT NULL DEFAULT 'unknown',
            progress_kind TEXT NOT NULL DEFAULT 'unavailable',
            final_size INTEGER,
            updated_at_ms INTEGER NOT NULL DEFAULT 0,
            resume_reused_bytes INTEGER NOT NULL DEFAULT 0,
            session_transferred_bytes INTEGER NOT NULL DEFAULT 0,
            snapshot_json TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS progress_v2_batches (
            batch_id INTEGER PRIMARY KEY,
            schema_version INTEGER NOT NULL DEFAULT 1,
            updated_at_ms INTEGER NOT NULL DEFAULT 0,
            snapshot_json TEXT NOT NULL,
            FOREIGN KEY(batch_id) REFERENCES playlist_batches(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_download_schedules_due ON download_schedules(enabled,run_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_status_updated ON jobs(status,updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_download_jobs_url ON download_jobs(url);
        CREATE INDEX IF NOT EXISTS idx_download_speed_limits_updated ON download_speed_limits(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_recent_files_opened ON recent_files(opened_at DESC);
        CREATE INDEX IF NOT EXISTS idx_playlist_batches_status_updated ON playlist_batches(status,updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_playlist_items_batch_status_position ON playlist_items(batch_id,status,position);
        CREATE INDEX IF NOT EXISTS idx_playlist_items_job ON playlist_items(job_id);
        CREATE INDEX IF NOT EXISTS idx_media_jobs_playlist_batch ON media_jobs(playlist_batch_id,job_id);
        CREATE INDEX IF NOT EXISTS idx_progress_v2_jobs_updated ON progress_v2_jobs(updated_at_ms DESC);
        UPDATE jobs SET status='queued', detail='Recuperada tras reiniciar la aplicación' WHERE status='running';
        UPDATE playlist_items SET status='queued' WHERE status='running';
        UPDATE playlist_batches SET status='queued' WHERE status='running';
        "
    )?;
    for statement in [
        "ALTER TABLE playlist_items ADD COLUMN source_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN title TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN creator TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN thumbnail TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN duration_label TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN job_id INTEGER",
        "ALTER TABLE playlist_items ADD COLUMN output_path TEXT",
        "ALTER TABLE playlist_items ADD COLUMN metadata_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN spotify_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN selected_source_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN resolution_state TEXT NOT NULL DEFAULT 'metadata_imported'",
        "ALTER TABLE playlist_items ADD COLUMN match_score REAL NOT NULL DEFAULT 0",
        "ALTER TABLE playlist_items ADD COLUMN provider_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE playlist_items ADD COLUMN last_error TEXT",
        "ALTER TABLE playlist_items ADD COLUMN automatic_retries INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE media_jobs ADD COLUMN thumbnail TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN requested_filename TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN expected_duration_seconds REAL",
        "ALTER TABLE media_jobs ADD COLUMN metadata_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN download_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN provider_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN resolution_state TEXT NOT NULL DEFAULT 'download_queued'",
        "ALTER TABLE media_jobs ADD COLUMN match_score REAL NOT NULL DEFAULT 0",
        "ALTER TABLE download_jobs ADD COLUMN speed_bps REAL NOT NULL DEFAULT 0",
        "ALTER TABLE download_jobs ADD COLUMN eta_seconds INTEGER",
        "ALTER TABLE download_jobs ADD COLUMN http_engine_attempts INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE download_jobs ADD COLUMN referrer TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE download_jobs ADD COLUMN remote_size INTEGER",
        "ALTER TABLE download_jobs ADD COLUMN strong_etag TEXT",
        "ALTER TABLE download_jobs ADD COLUMN last_modified TEXT",
        "ALTER TABLE download_jobs ADD COLUMN representation_fingerprint TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE download_jobs ADD COLUMN ownership_generation INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE download_jobs ADD COLUMN ownership_token TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE download_jobs ADD COLUMN finalization_state TEXT NOT NULL DEFAULT 'none'",
        "ALTER TABLE media_jobs ADD COLUMN downloaded_bytes INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE media_jobs ADD COLUMN total_bytes INTEGER",
        "ALTER TABLE media_jobs ADD COLUMN total_bytes_estimated INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE media_jobs ADD COLUMN speed_bps REAL NOT NULL DEFAULT 0",
        "ALTER TABLE media_jobs ADD COLUMN eta_seconds INTEGER",
        "ALTER TABLE media_jobs ADD COLUMN isrc TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN album TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN album_artist TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN release_date TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE media_jobs ADD COLUMN track_number INTEGER",
        "ALTER TABLE media_jobs ADD COLUMN disc_number INTEGER",
        "ALTER TABLE media_jobs ADD COLUMN explicit INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE media_jobs ADD COLUMN artist TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE jobs ADD COLUMN cancel_cleanup INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE jobs ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal','low'))",
        "ALTER TABLE playlist_batches ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal','low'))",
    ] {
        let _ = connection.execute(statement, []);
    }
    Ok(())
}
