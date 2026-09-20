#![allow(clippy::invisible_characters)]

use super::{
    finalize_http_job, http_v1_observation, human_bytes, request_download_response_with_range,
    response_content_range, response_is_unexpected_html, BandwidthLimiter,
};
use crate::progress::adapter::{
    shadow_http_observe, shadow_http_response_headers, shadow_http_start_stream,
    shadow_mark_http_cancelled, shadow_mark_http_completed, shadow_mark_http_finalizing,
    shadow_mark_http_paused, shadow_mark_http_post_processing,
};
use crate::{configure_connection, TransferRateSampler, DOWNLOAD_PROGRESS_UPDATE_INTERVAL_MS};
use reqwest::blocking::Client;
use reqwest::StatusCode;
use rusqlite::{params, Connection};
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

pub(super) const HTTP_SEGMENT_MAX: usize = 8;
const HTTP_SEGMENT_MIN_TOTAL: u64 = 16 * 1024 * 1024;
const HTTP_SEGMENT_TARGET: u64 = 8 * 1024 * 1024;
const HTTP_SEGMENT_RETRIES: u8 = 4;

#[derive(Clone)]
struct HttpSegment {
    index: usize,
    start: u64,
    end: u64,
    path: PathBuf,
}

pub(super) enum SegmentedDownloadResult {
    Completed,
    PausedOrCancelled,
}

pub(super) fn http_segment_path(temp_path: &Path, index: usize) -> PathBuf {
    PathBuf::from(format!("{}.segment-{index:03}.part", temp_path.display()))
}

pub(super) fn remove_http_segment_artifacts(db_path: &Path, id: i64) {
    let Ok(connection) = Connection::open(db_path) else {
        return;
    };
    let Ok(temp_path) = connection.query_row(
        "SELECT temp_path FROM download_jobs WHERE job_id=?1",
        params![id],
        |row| row.get::<_, String>(0),
    ) else {
        return;
    };
    let temp_path = PathBuf::from(temp_path);
    for index in 0..HTTP_SEGMENT_MAX {
        let _ = fs::remove_file(http_segment_path(&temp_path, index));
    }
}

fn download_job_status(connection: &Connection, id: i64) -> Result<String, String> {
    connection
        .query_row("SELECT status FROM jobs WHERE id=?1", params![id], |row| {
            row.get(0)
        })
        .map_err(|error| error.to_string())
}

fn download_one_http_segment(
    db_path: &Path,
    id: i64,
    client: &Client,
    url: &str,
    referrer: Option<&str>,
    segment: &HttpSegment,
    bandwidth_limiter: Option<&Arc<BandwidthLimiter>>,
) -> Result<(), String> {
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    configure_connection(&connection).map_err(|error| error.to_string())?;
    let expected = segment.end - segment.start + 1;
    let mut downloaded = segment
        .path
        .metadata()
        .map(|value| value.len())
        .unwrap_or(0);
    if downloaded > expected {
        let _ = fs::remove_file(&segment.path);
        downloaded = 0;
    }
    if downloaded == expected {
        return Ok(());
    }

    for attempt in 0..=HTTP_SEGMENT_RETRIES {
        match download_job_status(&connection, id)?.as_str() {
            "paused" | "cancelled" => return Ok(()),
            _ => {}
        }
        let range_start = segment.start + downloaded;
        let range = format!("bytes={range_start}-{}", segment.end);
        let mut response =
            request_download_response_with_range(client, url, Some(range), referrer)?;
        if response.status() != StatusCode::PARTIAL_CONTENT {
            return Err(format!(
                "El servidor no respetó el rango del segmento {} ({})",
                segment.index + 1,
                response.status()
            ));
        }
        if response_is_unexpected_html(&response, &segment.path) {
            return Err("El servidor devolvió una página web en vez del archivo solicitado".into());
        }
        let facts = response_content_range(&response).ok_or_else(|| {
            format!(
                "El segmento {} no incluyó una cabecera Content-Range válida",
                segment.index + 1
            )
        })?;
        if facts.start != range_start || facts.end > segment.end {
            return Err(format!(
                "El servidor devolvió un rango inesperado para el segmento {}",
                segment.index + 1
            ));
        }
        if let Some(total) = facts.total {
            if total < segment.end + 1 {
                return Err("El tamaño remoto cambió durante la descarga".into());
            }
        }
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&segment.path)
            .map_err(|error| format!("No se pudo abrir el segmento temporal: {error}"))?;
        let mut buffer = vec![0_u8; 256 * 1024];
        let mut stream_error = None;
        loop {
            match download_job_status(&connection, id)?.as_str() {
                "paused" | "cancelled" => return Ok(()),
                _ => {}
            }
            let read_budget = bandwidth_limiter
                .map(|limiter| limiter.read_grant(buffer.len()))
                .unwrap_or(buffer.len());
            match response.read(&mut buffer[..read_budget]) {
                Ok(0) => break,
                Ok(count) => {
                    if let Some(limiter) = bandwidth_limiter {
                        let should_continue = limiter.throttle_bytes(count, || {
                            Ok(matches!(
                                download_job_status(&connection, id)?.as_str(),
                                "paused" | "cancelled"
                            ))
                        })?;
                        if !should_continue {
                            return Ok(());
                        }
                    }
                    if downloaded + count as u64 > expected {
                        return Err(format!(
                            "El servidor entregó bytes fuera del segmento {}",
                            segment.index + 1
                        ));
                    }
                    file.write_all(&buffer[..count])
                        .map_err(|error| format!("No se pudo escribir un segmento: {error}"))?;
                    downloaded += count as u64;
                }
                Err(error) => {
                    stream_error = Some(error.to_string());
                    break;
                }
            }
        }
        file.flush().map_err(|error| error.to_string())?;
        if downloaded == expected {
            file.sync_all().map_err(|error| error.to_string())?;
            return Ok(());
        }
        if attempt == HTTP_SEGMENT_RETRIES {
            return Err(format!(
                "El segmento {} quedó incompleto: {} de {}{}",
                segment.index + 1,
                human_bytes(downloaded),
                human_bytes(expected),
                stream_error
                    .as_deref()
                    .map(|error| format!(" · {error}"))
                    .unwrap_or_default()
            ));
        }
        thread::sleep(Duration::from_millis(450 * (u64::from(attempt) + 1)));
    }
    Ok(())
}

fn persist_segmented_progress(
    connection: &Connection,
    id: i64,
    downloaded: u64,
    total: u64,
    speed: f64,
) -> Result<(), String> {
    let progress = (downloaded as f64 * 100.0 / total as f64).clamp(0.0, 99.9);
    let eta = (speed > 1.0 && total > downloaded)
        .then_some(((total - downloaded) as f64 / speed).ceil() as i64);
    let detail = format!(
        "{} / {} · {}/s · 8 conexiones HTTP",
        human_bytes(downloaded),
        human_bytes(total),
        human_bytes(speed as u64)
    );
    let transaction = connection
        .unchecked_transaction()
        .map_err(|error| error.to_string())?;
    transaction
        .execute(
            "UPDATE jobs SET progress=?1,detail=?2,updated_at=CURRENT_TIMESTAMP WHERE id=?3",
            params![progress, detail, id],
        )
        .map_err(|error| error.to_string())?;
    transaction
        .execute(
            "UPDATE download_jobs SET downloaded_bytes=?1,total_bytes=?2,resumable=1,speed_bps=?3,eta_seconds=?4,updated_at=CURRENT_TIMESTAMP WHERE job_id=?5",
            params![downloaded as i64, total as i64, speed, eta, id],
        )
        .map_err(|error| error.to_string())?;
    transaction.commit().map_err(|error| error.to_string())
}

#[allow(clippy::too_many_arguments)]
pub(super) fn try_segmented_http_download(
    db_path: &Path,
    id: i64,
    client: &Client,
    url: &str,
    destination: &Path,
    temp_path: &Path,
    referrer: Option<&str>,
    bandwidth_limiter: Option<Arc<BandwidthLimiter>>,
) -> Result<Option<SegmentedDownloadResult>, String> {
    let existing_temp = temp_path.metadata().map(|value| value.len()).unwrap_or(0);
    let has_segments =
        (0..HTTP_SEGMENT_MAX).any(|index| http_segment_path(temp_path, index).is_file());
    if existing_temp > 0 && !has_segments {
        return Ok(None);
    }

    let mut probe =
        request_download_response_with_range(client, url, Some("bytes=0-0".into()), referrer)?;
    if probe.status() != StatusCode::PARTIAL_CONTENT {
        if has_segments {
            remove_http_segment_artifacts(db_path, id);
        }
        if probe.status().is_client_error() {
            // A server can reject the preliminary range request while still
            // serving the complete object sequentially.  Discard only the
            // segment bookkeeping and let the bounded sequential path decide.
            return Ok(None);
        }
        return Ok(None);
    }
    if response_is_unexpected_html(&probe, destination) {
        return Err(
            "El enlace devolvió una página web en vez del archivo. Usa el enlace directo de descarga o vuelve a analizarlo"
                .into(),
        );
    }
    let facts = response_content_range(&probe).ok_or_else(|| {
        "El servidor no informó el tamaño exacto mediante Content-Range".to_string()
    })?;
    let total = facts
        .total
        .filter(|value| *value > 0)
        .ok_or_else(|| "El servidor no informó un tamaño total verificable".to_string())?;
    let _ = probe.read(&mut [0_u8; 1]);
    if total < HTTP_SEGMENT_MIN_TOTAL {
        return Ok(None);
    }

    let segment_count = (total.div_ceil(HTTP_SEGMENT_TARGET) as usize).clamp(2, HTTP_SEGMENT_MAX);
    let chunk = total.div_ceil(segment_count as u64);
    let segments = (0..segment_count)
        .map(|index| {
            let start = index as u64 * chunk;
            let end = std::cmp::min(total - 1, start + chunk - 1);
            HttpSegment {
                index,
                start,
                end,
                path: http_segment_path(temp_path, index),
            }
        })
        .filter(|segment| segment.start <= segment.end)
        .collect::<Vec<_>>();
    if segments.len() < 2 {
        return Ok(None);
    }
    for index in segments.len()..HTTP_SEGMENT_MAX {
        let _ = fs::remove_file(http_segment_path(temp_path, index));
    }
    if let Some(parent) = temp_path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let existing_downloaded = segments
        .iter()
        .map(|segment| {
            segment
                .path
                .metadata()
                .map(|value| value.len())
                .unwrap_or(0)
        })
        .sum::<u64>();
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    configure_connection(&connection).map_err(|error| error.to_string())?;
    connection
        .execute(
            "UPDATE download_jobs SET total_bytes=?1,downloaded_bytes=?2,resumable=1,error=NULL,updated_at=CURRENT_TIMESTAMP WHERE job_id=?3",
            params![total as i64, existing_downloaded as i64, id],
        )
        .map_err(|error| error.to_string())?;
    connection
        .execute(
            "UPDATE jobs SET status='running',detail=?1,updated_at=CURRENT_TIMESTAMP WHERE id=?2",
            params![
                format!("Descarga HTTP multihilo · {} conexiones", segments.len()),
                id
            ],
        )
        .map_err(|error| error.to_string())?;
    shadow_http_response_headers(
        id,
        probe.status().as_u16(),
        existing_downloaded,
        probe.content_length(),
        Some(facts),
        http_v1_observation(
            existing_downloaded,
            Some(total),
            None,
            None,
            "running",
            None,
        ),
    );
    shadow_http_start_stream(
        id,
        existing_downloaded,
        Some(total),
        http_v1_observation(
            existing_downloaded,
            Some(total),
            None,
            None,
            "running",
            None,
        ),
    );

    let mut sampler = TransferRateSampler::new(existing_downloaded);
    let mut last_update = Instant::now() - Duration::from_secs(1);
    let results = std::thread::scope(|scope| {
        let handles = segments
            .iter()
            .map(|segment| {
                let segment = segment.clone();
                let client = client.clone();
                let url = url.to_string();
                let referrer = referrer.map(str::to_string);
                let bandwidth_limiter = bandwidth_limiter.clone();
                scope.spawn(move || {
                    download_one_http_segment(
                        db_path,
                        id,
                        &client,
                        &url,
                        referrer.as_deref(),
                        &segment,
                        bandwidth_limiter.as_ref(),
                    )
                })
            })
            .collect::<Vec<_>>();
        loop {
            let downloaded = segments
                .iter()
                .map(|segment| {
                    segment
                        .path
                        .metadata()
                        .map(|value| value.len())
                        .unwrap_or(0)
                        .min(segment.end - segment.start + 1)
                })
                .sum::<u64>();
            let speed = sampler.sample(downloaded);
            shadow_http_observe(
                id,
                downloaded,
                http_v1_observation(
                    downloaded,
                    Some(total),
                    (speed > 0.0).then_some(speed),
                    (speed > 1.0 && total > downloaded)
                        .then_some(((total - downloaded) as f64 / speed).ceil() as u64),
                    "running",
                    None,
                ),
            );
            if last_update.elapsed() >= Duration::from_millis(DOWNLOAD_PROGRESS_UPDATE_INTERVAL_MS)
            {
                persist_segmented_progress(&connection, id, downloaded, total, speed)?;
                last_update = Instant::now();
            }
            let status = download_job_status(&connection, id)?;
            if status == "paused"
                || status == "cancelled"
                || handles.iter().all(|handle| handle.is_finished())
            {
                let joined = handles
                    .into_iter()
                    .map(|handle| {
                        handle
                            .join()
                            .map_err(|_| "Un segmento HTTP terminó de forma inesperada".to_string())
                            .and_then(|result| result)
                    })
                    .collect::<Result<Vec<_>, _>>();
                joined?;
                break;
            }
            thread::sleep(Duration::from_millis(180));
        }
        Ok::<(), String>(())
    });
    results?;

    let status = download_job_status(&connection, id)?;
    if matches!(status.as_str(), "paused" | "cancelled") {
        let detail = if status == "paused" {
            "En pausa · segmentos HTTP conservados"
        } else {
            "Cancelada · segmentos HTTP conservados"
        };
        connection
            .execute(
                "UPDATE jobs SET detail=?1,updated_at=CURRENT_TIMESTAMP WHERE id=?2",
                params![detail, id],
            )
            .map_err(|error| error.to_string())?;
        if status == "paused" {
            shadow_mark_http_paused(id);
        } else {
            shadow_mark_http_cancelled(id);
        }
        return Ok(Some(SegmentedDownloadResult::PausedOrCancelled));
    }
    let downloaded = segments
        .iter()
        .map(|segment| {
            segment
                .path
                .metadata()
                .map(|value| value.len())
                .unwrap_or(0)
        })
        .sum::<u64>();
    if downloaded != total {
        return Err(format!(
            "La descarga multihilo quedó incompleta: {} de {}",
            human_bytes(downloaded),
            human_bytes(total)
        ));
    }
    shadow_mark_http_post_processing(id);
    let mut assembled = OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true)
        .open(temp_path)
        .map_err(|error| format!("No se pudo crear el ensamblador temporal: {error}"))?;
    for segment in &segments {
        let mut input = fs::File::open(&segment.path).map_err(|error| {
            format!("No se pudo leer el segmento {}: {error}", segment.index + 1)
        })?;
        std::io::copy(&mut input, &mut assembled).map_err(|error| {
            format!(
                "No se pudo ensamblar el segmento {}: {error}",
                segment.index + 1
            )
        })?;
    }
    assembled.flush().map_err(|error| error.to_string())?;
    assembled.sync_all().map_err(|error| error.to_string())?;
    drop(assembled);
    shadow_mark_http_finalizing(id);
    let final_size = temp_path
        .metadata()
        .map_err(|error| format!("No se pudo verificar el ensamblado HTTP: {error}"))?
        .len();
    if final_size != total {
        return Err("El archivo ensamblado no coincide con Content-Range".into());
    }
    if destination.exists() {
        return Err("Ya existe un archivo con el mismo nombre".into());
    }
    fs::rename(temp_path, destination)
        .map_err(|error| format!("No se pudo finalizar el archivo ensamblado: {error}"))?;
    finalize_http_job(
        db_path,
        id,
        destination,
        total,
        "Completada y verificada · HTTP multihilo",
    )?;
    for segment in &segments {
        let _ = fs::remove_file(&segment.path);
    }
    shadow_mark_http_completed(id, total);
    Ok(Some(SegmentedDownloadResult::Completed))
}
