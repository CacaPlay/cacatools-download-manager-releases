use rusqlite::params;
use tauri::{AppHandle, State};

use super::{
    diagnosis_allows_alternatives, duration_similarity, failure_diagnosis, is_spotify_url,
    job_uses_disabled_spotify, match_reasons, sanitize_media_error_for_display,
    search_media_internal, title_similarity, token_similarity, verify_direct_availability,
    verify_media_availability,
};
use crate::{spotify_disabled_error, LocalState, MediaRecoveryRequest, MediaRecoverySnapshot};

pub(crate) fn recover_media_source(
    request: MediaRecoveryRequest,
    app: AppHandle,
    state: State<'_, LocalState>,
) -> Result<MediaRecoverySnapshot, String> {
    let MediaRecoveryRequest {
        job_id,
        title,
        source_url,
        creator,
        duration_seconds,
        limit,
    } = request;
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    if job_uses_disabled_spotify(&connection, job_id)? {
        return Err(spotify_disabled_error());
    }
    let database_values = connection
        .query_row(
            "SELECT jobs.title,jobs.detail,
                    COALESCE(media_jobs.source_url,download_jobs.url,torrent_jobs.source,''),
                    CASE WHEN media_jobs.job_id IS NOT NULL THEN 1 ELSE 0 END,
                    CASE WHEN torrent_jobs.job_id IS NOT NULL THEN 1 ELSE 0 END,
                    COALESCE(media_jobs.error,download_jobs.error,torrent_jobs.error,jobs.detail,''),
                    media_jobs.expected_duration_seconds
             FROM jobs
             LEFT JOIN media_jobs ON media_jobs.job_id=jobs.id
             LEFT JOIN download_jobs ON download_jobs.job_id=jobs.id
             LEFT JOIN torrent_jobs ON torrent_jobs.job_id=jobs.id
             WHERE jobs.id=?1",
            params![job_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, i64>(3)? != 0,
                    row.get::<_, i64>(4)? != 0,
                    row.get::<_, String>(5)?,
                    row.get::<_, Option<f64>>(6)?,
                ))
            },
        )
        .map_err(|_| "La tarea ya no existe".to_string())?;
    drop(connection);

    let (
        stored_title,
        detail,
        stored_source,
        is_media,
        is_torrent,
        stored_error,
        expected_duration,
    ) = database_values;
    let detail = sanitize_media_error_for_display(&detail);
    let stored_error = sanitize_media_error_for_display(&stored_error);
    let effective_title = if title.trim().is_empty() {
        stored_title
    } else {
        title.trim().to_string()
    };
    let effective_source = source_url
        .filter(|value| !value.trim().is_empty())
        .unwrap_or(stored_source);
    if is_media && is_spotify_url(&effective_source) {
        return Err(spotify_disabled_error());
    }
    let source_kind = if is_media {
        "multimedia"
    } else if is_torrent {
        "torrent"
    } else {
        "HTTP"
    };
    let fallback_message = if stored_error.trim().is_empty() {
        detail
    } else {
        stored_error
    };
    let mut diagnosis = failure_diagnosis(&fallback_message, source_kind);
    let mut attempts = 0;

    if is_media && !effective_source.trim().is_empty() {
        // A successful metadata probe only proves that the public page still
        // exists. It does not prove that the signed media URL accepts the
        // current session. Do not turn a known 403/session failure into the
        // misleading "source available" result or an endless resume loop.
        if diagnosis.code == "authentication_required" {
            return Ok(MediaRecoverySnapshot {
                original_available: false,
                message: diagnosis.summary.clone(),
                alternatives: Vec::new(),
                diagnosis,
                verification_attempts: 0,
                recovery_mode: "session_required".into(),
                can_retry: false,
            });
        }
        let (available, verified, verification_attempts) =
            verify_media_availability(&effective_source, &app)?;
        diagnosis = verified;
        attempts = verification_attempts;
        if available {
            return Ok(MediaRecoverySnapshot {
                original_available: true,
                message: diagnosis.summary.clone(),
                alternatives: Vec::new(),
                diagnosis,
                verification_attempts: attempts,
                recovery_mode: "available".into(),
                can_retry: true,
            });
        }
    } else if !is_torrent && !effective_source.trim().is_empty() {
        let (available, verified, verification_attempts) =
            verify_direct_availability(&effective_source)?;
        diagnosis = verified;
        attempts = verification_attempts;
        return Ok(MediaRecoverySnapshot {
            original_available: available,
            message: diagnosis.summary.clone(),
            alternatives: Vec::new(),
            can_retry: diagnosis.retryable,
            recovery_mode: if available {
                "available".into()
            } else if diagnosis.likely_temporary {
                "temporary_error".into()
            } else {
                "direct_retry".into()
            },
            diagnosis,
            verification_attempts: attempts,
        });
    }

    if is_torrent || !diagnosis_allows_alternatives(&diagnosis) {
        return Ok(MediaRecoverySnapshot {
            original_available: false,
            message: diagnosis.summary.clone(),
            alternatives: Vec::new(),
            can_retry: diagnosis.retryable,
            recovery_mode: if is_torrent {
                "torrent_retry".into()
            } else {
                "temporary_error".into()
            },
            diagnosis,
            verification_attempts: attempts,
        });
    }

    let creator = creator.unwrap_or_default();
    let search_query = if creator.trim().is_empty() {
        effective_title.clone()
    } else {
        format!("{} {}", effective_title, creator.trim())
    };
    let mut alternatives = search_media_internal(&search_query, 30, &app)?;
    let expected_duration = duration_seconds.or(expected_duration);
    for alternative in &mut alternatives {
        let title_score = title_similarity(&effective_title, &alternative.title);
        let creator_score = if creator.trim().is_empty() {
            0.5
        } else {
            token_similarity(&creator, &alternative.creator)
        };
        let duration_score = duration_similarity(expected_duration, alternative.duration_seconds);
        alternative.similarity =
            (title_score * 0.72 + creator_score * 0.16 + duration_score * 0.12) * 100.0;
        alternative.match_reasons = match_reasons(title_score, creator_score, duration_score);
    }
    alternatives.retain(|item| item.source_url != effective_source);
    alternatives.retain(|item| item.similarity >= 32.0);
    alternatives.sort_by(|left, right| {
        right
            .similarity
            .partial_cmp(&left.similarity)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    alternatives.truncate(limit.unwrap_or(8).clamp(1, 15));
    let message = if alternatives.is_empty() {
        "La fuente original no está disponible y no encontramos coincidencias suficientemente cercanas".into()
    } else {
        format!(
            "La fuente original no está disponible. Se encontraron {} alternativas ordenadas por similitud",
            alternatives.len()
        )
    };
    Ok(MediaRecoverySnapshot {
        original_available: false,
        message,
        alternatives,
        can_retry: diagnosis.retryable,
        recovery_mode: "media_alternatives".into(),
        diagnosis,
        verification_attempts: attempts,
    })
}
