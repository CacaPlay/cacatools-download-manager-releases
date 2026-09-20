use super::{complete_verified_http_job, finalize_http_job, BandwidthPolicy};
use crate::progress::adapter::{
    shadow_http_observe, shadow_http_response_headers, shadow_http_start_stream,
    shadow_mark_http_completed, shadow_mark_http_finalizing, shadow_mark_http_preparing,
};
use crate::progress::http::{parse_content_range, ContentRangeFacts};
use crate::{
    background_command, chaos, configure_connection, kill_process_tree, register_external_process,
    ExternalProcessKind, ExternalProcessRegistry,
};
use reqwest::blocking::{Client, Response};
use reqwest::header::{
    ACCEPT, ACCEPT_ENCODING, CONTENT_LENGTH, CONTENT_RANGE, CONTENT_TYPE, RANGE, REFERER,
};
use reqwest::StatusCode;
use rusqlite::{params, Connection};
use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, Read, Write};
use std::path::Path;
use std::process::{Child, Stdio};
use std::thread;
use std::time::Duration;
use url::Url;

pub(crate) const HTTP_ARIA2_FEATURE_KEY: &str = "http_aria2_enabled";
pub(crate) const ARIA2_USER_AGENT: &str =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

#[derive(Debug, Clone)]
pub(crate) struct HttpInspection {
    pub(crate) final_url: Url,
    pub(crate) status_code: u16,
    pub(crate) content_type: Option<String>,
    pub(crate) content_length: Option<u64>,
    pub(crate) content_range: Option<ContentRangeFacts>,
    pub(crate) total_bytes: Option<u64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum InspectionOutcome {
    Direct,
    MediaRedirect,
    UnsupportedHtml,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Aria2Result {
    Completed,
    PausedOrCancelled,
}

pub(crate) const ARIA2_MAX_RESUME_RETRIES: i64 = 3;

pub(crate) fn http_aria2_enabled(connection: &Connection) -> bool {
    if let Ok(value) = std::env::var("CACATOOLS_HTTP_ARIA2") {
        return parse_bool(&value);
    }
    connection
        .query_row(
            "SELECT value FROM settings WHERE key=?1",
            params![HTTP_ARIA2_FEATURE_KEY],
            |row| row.get::<_, String>(0),
        )
        .map(|value| parse_bool(&value))
        .unwrap_or(true)
}

pub(crate) fn inspect_http(
    url: &str,
    referrer: Option<&str>,
) -> Result<(HttpInspection, InspectionOutcome), String> {
    let parsed = crate::parse_public_http_url(url, "El enlace de descarga no es válido")?;
    crate::ensure_public_network_resolution(&parsed)?;
    let client = Client::builder()
        .user_agent(ARIA2_USER_AGENT)
        .connect_timeout(Duration::from_secs(5))
        .timeout(Duration::from_secs(8))
        .redirect(reqwest::redirect::Policy::custom(|attempt| {
            if attempt.previous().len() >= 8 {
                return attempt.error("La descarga superó el límite de redirecciones");
            }
            if crate::url_has_public_network_target(attempt.url()) {
                attempt.follow()
            } else {
                attempt.error("La redirección apunta a una dirección local o privada")
            }
        }))
        .build()
        .map_err(|error| format!("No se pudo preparar la inspección HTTP: {error}"))?;

    let head = build_request(client.head(parsed.clone()), referrer)
        .header(ACCEPT, "*/*")
        .header(ACCEPT_ENCODING, "identity")
        .send();
    if let Ok(response) = head {
        if response.status().is_success() && head_is_conclusive(&response) {
            return classify_response(response, parsed, false);
        }
    }

    let response = build_request(client.get(parsed.clone()), referrer)
        .header(ACCEPT, "*/*")
        .header(ACCEPT_ENCODING, "identity")
        .header(RANGE, "bytes=0-0")
        .send()
        .map_err(|error| format!("No se pudo inspeccionar el archivo remoto: {error}"))?;
    if response.status() == StatusCode::RANGE_NOT_SATISFIABLE {
        return classify_response(response, parsed, false);
    }
    if !response.status().is_success() {
        return Err(format!(
            "El servidor respondió {} durante la inspección HTTP",
            response.status()
        ));
    }
    classify_response(response, parsed, true)
}

fn build_request(
    request: reqwest::blocking::RequestBuilder,
    referrer: Option<&str>,
) -> reqwest::blocking::RequestBuilder {
    match referrer
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .and_then(|value| Url::parse(value).ok())
        .filter(crate::url_has_public_network_target)
    {
        Some(value) => request.header(REFERER, value.as_str()),
        None => request,
    }
}

fn head_is_conclusive(response: &Response) -> bool {
    response.headers().contains_key(CONTENT_TYPE)
        || response.headers().contains_key(CONTENT_LENGTH)
        || response.headers().contains_key(CONTENT_RANGE)
}

fn classify_response(
    mut response: Response,
    original_url: Url,
    read_body_prefix: bool,
) -> Result<(HttpInspection, InspectionOutcome), String> {
    let final_url = response.url().clone();
    if !crate::url_has_public_http_target(&final_url) {
        return Err("La descarga terminó en una dirección local o privada no permitida".into());
    }
    let content_type = response
        .headers()
        .get(CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .map(str::to_string);
    let content_length = response
        .headers()
        .get(CONTENT_LENGTH)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.parse::<u64>().ok());
    let content_range = response
        .headers()
        .get(CONTENT_RANGE)
        .and_then(|value| value.to_str().ok())
        .and_then(parse_content_range);
    let total_bytes = content_range
        .and_then(|value| value.total)
        .or(content_length.filter(|value| *value > 1));
    let body_is_html = if read_body_prefix {
        let mut prefix = Vec::with_capacity(1024);
        response
            .by_ref()
            .take(1024)
            .read_to_end(&mut prefix)
            .map_err(|error| format!("No se pudo validar la respuesta HTTP: {error}"))?;
        html_prefix(&prefix)
    } else {
        false
    };
    let content_is_html = content_type
        .as_deref()
        .map(is_html_content_type)
        .unwrap_or(false)
        || body_is_html;
    let inspection = HttpInspection {
        final_url,
        status_code: response.status().as_u16(),
        content_type,
        content_length,
        content_range,
        total_bytes,
    };
    if !content_is_html {
        return Ok((inspection, InspectionOutcome::Direct));
    }
    if is_supported_media_host(&original_url) || is_supported_media_host(&inspection.final_url) {
        Ok((inspection, InspectionOutcome::MediaRedirect))
    } else {
        Ok((inspection, InspectionOutcome::UnsupportedHtml))
    }
}

pub(crate) fn is_supported_media_host(url: &Url) -> bool {
    let host = url.host_str().unwrap_or_default().to_ascii_lowercase();
    [
        "youtube.com",
        "youtu.be",
        "vimeo.com",
        "tiktok.com",
        "instagram.com",
        "pinterest.com",
        "pin.it",
        "x.com",
        "twitter.com",
        "facebook.com",
        "reddit.com",
        "v.redd.it",
        "soundcloud.com",
        "twitch.tv",
        "dailymotion.com",
    ]
    .iter()
    .any(|domain| host == *domain || host.ends_with(&format!(".{domain}")))
}

fn is_html_content_type(value: &str) -> bool {
    let lower = value.to_ascii_lowercase();
    lower.contains("text/html") || lower.contains("application/xhtml")
}

pub(crate) fn is_html_content_type_for_queue(value: &str) -> bool {
    is_html_content_type(value)
}

fn html_prefix(bytes: &[u8]) -> bool {
    let text = String::from_utf8_lossy(bytes)
        .trim_start_matches('\u{feff}')
        .trim_start()
        .to_ascii_lowercase();
    text.starts_with("<!doctype html")
        || text.starts_with("<html")
        || text.starts_with("<head")
        || text.starts_with("<body")
        || (text.starts_with('<') && text.contains("<body"))
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn run_aria2c(
    db_path: &Path,
    id: i64,
    aria2_path: &Path,
    destination: &Path,
    temp_path: &Path,
    referrer: Option<&str>,
    inspection: &HttpInspection,
    external_processes: Option<&ExternalProcessRegistry>,
    bandwidth_policy: &BandwidthPolicy,
) -> Result<Aria2Result, String> {
    let parent = destination
        .parent()
        .ok_or_else(|| "La carpeta de destino no es válida".to_string())?;
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    let output_name = destination
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| "El nombre final del archivo no es válido".to_string())?;
    // El archivo debe crecer con los bytes realmente recibidos. La
    // preasignación hacía que su tamaño pareciera completo desde el primer
    // instante, dejaba la UI en 0 B y complicaba la transición final cuando
    // el control .aria2 seguía presente.
    let stored_resume_bytes = persisted_downloaded_bytes(db_path, id);
    let resume_bytes = temp_path
        .metadata()
        .map(|value| value.len())
        .ok()
        .filter(|value| *value > 0)
        .or_else(|| {
            // aria2 keeps its resumable output at the final destination while
            // the control file exists. Prefer that real contiguous size over
            // a stale SQLite sample so a restart cannot report a false burst.
            aria2_control_path(destination)
                .is_file()
                .then(|| destination.metadata().map(|value| value.len()).unwrap_or(0))
                .filter(|value| *value > 0)
        })
        .unwrap_or(stored_resume_bytes);

    if destination.exists() && temp_path.exists() {
        return Err("Hay un archivo final y un parcial simultáneos; se requiere intervención para evitar sobrescritura".into());
    }
    if temp_path.exists() {
        fs::rename(temp_path, destination)
            .map_err(|error| format!("No se pudo preparar la reanudación aria2c: {error}"))?;
    }

    if let Err(error) = persist_started(db_path, id, inspection.total_bytes, resume_bytes) {
        let _ = move_output_to_temp(destination, temp_path);
        return Err(error);
    }

    let mut command = background_command(aria2_path);
    command
        .arg("--dir")
        .arg(parent)
        .arg("--out")
        .arg(output_name)
        .arg("--check-integrity=true")
        .arg("--allow-overwrite=false")
        .arg("--auto-file-renaming=false")
        .arg("--continue=true")
        // Progress is sampled from the output length. Multiple ranged
        // connections make that length sparse/out-of-order and can therefore
        // look like hundreds of MB/s before the missing ranges arrive. Keep
        // one contiguous stream so UI/SQLite bytes represent actual receipt.
        .arg("--split=1")
        .arg("--max-connection-per-server=1")
        .arg("--file-allocation=none")
        .arg("--max-tries=5")
        .arg("--retry-wait=2")
        .arg(format!("--user-agent={ARIA2_USER_AGENT}"))
        .arg("--timeout=60")
        .arg("--connect-timeout=30")
        .arg("--no-file-allocation-limit=4M")
        .arg("--disk-cache=32M")
        .arg("--download-result=hide")
        .arg("--console-log-level=warn")
        .arg("--summary-interval=0")
        .arg("--uri-selector=adaptive");
    bandwidth_policy.apply_to_aria2(&mut command);
    if let Some(referrer) = referrer.map(str::trim).filter(|value| !value.is_empty()) {
        command.arg("--referer").arg(referrer);
    }
    command
        .arg(inspection.final_url.as_str())
        .stdout(Stdio::null())
        .stderr(Stdio::piped());
    let mut child = match command.spawn() {
        Ok(child) => child,
        Err(error) => {
            let _ = move_output_to_temp(destination, temp_path);
            return Err(format!("No se pudo iniciar aria2c: {error}"));
        }
    };
    let pid = child.id();
    let _process_guard = if let Some(registry) = external_processes {
        match register_external_process(registry, id, pid, ExternalProcessKind::Aria2) {
            Ok(guard) => Some(guard),
            Err(error) => {
                kill_process_tree(pid);
                let _ = child.wait();
                let _ = move_output_to_temp(destination, temp_path);
                return Err(error);
            }
        }
    } else {
        None
    };
    let stderr_reader = spawn_stderr_reader(&mut child);
    let total = inspection.total_bytes;
    shadow_mark_http_preparing(id);
    shadow_http_response_headers(
        id,
        inspection.status_code,
        resume_bytes,
        inspection.content_length,
        inspection.content_range,
        super::http_v1_observation(resume_bytes, total, None, None, "running", None),
    );
    shadow_http_start_stream(
        id,
        resume_bytes,
        total,
        super::http_v1_observation(resume_bytes, total, None, None, "running", None),
    );

    let mut speed_sampler = crate::TransferRateSampler::new(resume_bytes);
    let mut hot_chaos = chaos::HotChaosController::new();
    let exit_status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {}
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = move_output_to_temp(destination, temp_path);
                return Err(format!("No se pudo consultar aria2c: {error}"));
            }
        }
        // Con file-allocation=none, metadata().len() representa los bytes
        // recibidos tanto si el total es conocido como si no. Persistir ambos
        // casos mantiene la fila útil desde el primer bloque y evita que el
        // usuario tenga que pausar/reanudar para que aparezca el progreso.
        let current = destination.metadata().map(|value| value.len()).unwrap_or(0);
        let speed = speed_sampler.sample(current);
        let _ = persist_progress(db_path, id, current, total, speed);
        if let Ok(state) = job_status(db_path, id) {
            if matches!(state.as_str(), "paused" | "cancelled") {
                let _ = child.kill();
                let _ = child.wait();
                move_output_to_temp(destination, temp_path)?;
                return Ok(Aria2Result::PausedOrCancelled);
            }
        }
        if total.is_some_and(|value| value >= 32 * 1024 * 1024) && hot_chaos.due() {
            let _ = persist_job_detail(
                db_path,
                id,
                "Reintentando · corte de red simulado por Hot Chaos",
                "retrying",
            );
            if hot_chaos.maybe_cut(pid, "aria2c") {
                let _ = persist_job_detail(db_path, id, "Descarga HTTP · aria2c", "running");
            }
        }
        thread::sleep(Duration::from_millis(250));
    };
    let stderr = stderr_reader.join().unwrap_or_default();
    let code = exit_status.code().unwrap_or(-1);
    if !exit_status.success() {
        // aria2c may exit non-zero after writing the complete output (for
        // example when its final control-file cleanup races with shutdown).
        // Preserve that verified output and recover the SQLite commit before
        // converting it back into a partial file for another engine.
        if total.is_some_and(|expected| expected > 0)
            && destination
                .metadata()
                .map(|metadata| metadata.len() == total.unwrap_or(0))
                .unwrap_or(false)
            && !file_looks_like_html(destination)?
        {
            if complete_verified_http_job(db_path, id) {
                let _ = fs::remove_file(aria2_control_path(destination));
                return Ok(Aria2Result::Completed);
            }
            return Err(
                "aria2c dejó un archivo completo verificado, pero no se pudo confirmar SQLite; se conserva la salida final"
                    .into(),
            );
        }
        let has_resume_control = aria2_control_path(destination).is_file();
        move_output_to_temp(destination, temp_path)?;
        let message = stderr.trim().chars().take(600).collect::<String>();
        let prefix = if has_resume_control && aria2_failure_is_retryable(code, &stderr) {
            "aria2c_retryable"
        } else {
            "aria2c_exit"
        };
        return Err(format!("{prefix}:aria2c_exit_code:{code}: {message}"));
    }

    let final_size = destination
        .metadata()
        .map_err(|error| format!("aria2c terminó sin crear el archivo final: {error}"))?
        .len();
    if total.is_some_and(|expected| expected != final_size) {
        move_output_to_temp(destination, temp_path)?;
        return Err(format!(
            "aria2c terminó con tamaño incorrecto: {} de {} bytes",
            final_size,
            total.unwrap_or(final_size)
        ));
    }
    if file_looks_like_html(destination)? {
        move_output_to_temp(destination, temp_path)?;
        return Err(
            "html_direct_unsupported: aria2c recibió una página HTML en lugar del archivo".into(),
        );
    }
    let mut final_file = OpenOptions::new()
        .read(true)
        .write(true)
        .open(destination)
        .map_err(|error| format!("No se pudo verificar el archivo aria2c: {error}"))?;
    final_file
        .flush()
        .map_err(|error| format!("No se pudo sincronizar el archivo aria2c: {error}"))?;
    final_file
        .sync_all()
        .map_err(|error| format!("No se pudo confirmar el archivo aria2c: {error}"))?;
    drop(final_file);
    shadow_mark_http_finalizing(id);
    finalize_job(db_path, id, destination, final_size)?;
    // El estado de la descarga ya quedó confirmado. El control solo sirve
    // para reanudar parciales y no debe sobrevivir junto a un archivo final.
    let _ = fs::remove_file(aria2_control_path(destination));
    shadow_mark_http_completed(id, final_size);
    Ok(Aria2Result::Completed)
}

fn spawn_stderr_reader(child: &mut Child) -> thread::JoinHandle<String> {
    let stderr = child.stderr.take();
    thread::spawn(move || {
        let mut bytes = Vec::new();
        if let Some(stderr) = stderr {
            let _ = BufReader::new(stderr).read_to_end(&mut bytes);
        }
        String::from_utf8_lossy(&bytes).into_owned()
    })
}

fn persist_started(
    db_path: &Path,
    id: i64,
    total: Option<u64>,
    resume_bytes: u64,
) -> Result<(), String> {
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    configure_connection(&connection).map_err(|error| error.to_string())?;
    connection
        .execute(
            "UPDATE jobs SET status='running',detail='Descarga HTTP · aria2c',updated_at=CURRENT_TIMESTAMP WHERE id=?1",
            params![id],
        )
        .map_err(|error| error.to_string())?;
    connection
        .execute(
            "UPDATE download_jobs SET downloaded_bytes=?1,total_bytes=?2,resumable=1,error=NULL,updated_at=CURRENT_TIMESTAMP WHERE job_id=?3",
            params![resume_bytes as i64, total.map(|value| value as i64), id],
        )
        .map_err(|error| error.to_string())?;
    Ok(())
}

fn persist_progress(
    db_path: &Path,
    id: i64,
    downloaded: u64,
    total: Option<u64>,
    speed: f64,
) -> Result<(), String> {
    let progress = total
        .filter(|value| *value > 0)
        .map(|value| (downloaded as f64 / value as f64 * 100.0).clamp(0.0, 99.9));
    let eta = total
        .filter(|value| speed > 1.0 && *value > downloaded)
        .map(|value| ((value - downloaded) as f64 / speed).ceil() as i64);
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    configure_connection(&connection).map_err(|error| error.to_string())?;
    connection
        .execute(
            "UPDATE jobs SET progress=COALESCE(?1,progress),detail='Descarga HTTP · aria2c',updated_at=CURRENT_TIMESTAMP WHERE id=?2 AND status='running'",
            params![progress, id],
        )
        .map_err(|error| error.to_string())?;
    connection
        .execute(
            "UPDATE download_jobs SET downloaded_bytes=?1,total_bytes=COALESCE(?2,total_bytes),speed_bps=?3,eta_seconds=?4,updated_at=CURRENT_TIMESTAMP WHERE job_id=?5",
            params![downloaded as i64, total.map(|value| value as i64), speed, eta, id],
        )
        .map_err(|error| error.to_string())?;
    shadow_http_observe(
        id,
        downloaded,
        super::http_v1_observation(
            downloaded,
            total,
            Some(speed),
            eta.map(|value| value as u64),
            "running",
            None,
        ),
    );
    Ok(())
}

fn persist_job_detail(db_path: &Path, id: i64, detail: &str, status: &str) -> Result<(), String> {
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    configure_connection(&connection).map_err(|error| error.to_string())?;
    connection
        .execute(
            "UPDATE jobs SET status=?1,detail=?2,updated_at=CURRENT_TIMESTAMP WHERE id=?3",
            params![status, detail, id],
        )
        .map_err(|error| error.to_string())?;
    Ok(())
}

fn job_status(db_path: &Path, id: i64) -> Result<String, String> {
    Connection::open(db_path)
        .map_err(|error| error.to_string())?
        .query_row("SELECT status FROM jobs WHERE id=?1", params![id], |row| {
            row.get(0)
        })
        .map_err(|error| error.to_string())
}

fn persisted_downloaded_bytes(db_path: &Path, id: i64) -> u64 {
    Connection::open(db_path)
        .ok()
        .and_then(|connection| {
            connection
                .query_row(
                    "SELECT downloaded_bytes FROM download_jobs WHERE job_id=?1",
                    params![id],
                    |row| row.get::<_, i64>(0),
                )
                .ok()
        })
        .unwrap_or(0)
        .max(0) as u64
}

fn aria2_failure_is_retryable(code: i32, stderr: &str) -> bool {
    let lower = stderr.to_ascii_lowercase();
    let terminal = [
        "403",
        "404",
        "416",
        "429",
        "certificate",
        "checksum",
        "html",
        "not enough disk",
        "file already exists",
        "unsupported",
    ];
    if terminal.iter().any(|marker| lower.contains(marker)) {
        return false;
    }
    let network = [
        "timeout",
        "timed out",
        "socket",
        "connection",
        "could not connect",
        "network",
        "temporarily unavailable",
        "reset by peer",
    ];
    network.iter().any(|marker| lower.contains(marker)) || matches!(code, 2 | 6 | 7 | 8 | 23)
}

fn move_output_to_temp(destination: &Path, temp_path: &Path) -> Result<(), String> {
    if !destination.exists() {
        return Ok(());
    }
    // When aria2's control file exists, the destination/control pair is the
    // authoritative resume state. Keep it together instead of manufacturing
    // a second .part file that could make recovery ambiguous.
    if aria2_control_path(destination).is_file() {
        return Ok(());
    }
    if temp_path.exists() {
        let destination_size = destination.metadata().map(|value| value.len()).unwrap_or(0);
        let temp_size = temp_path.metadata().map(|value| value.len()).unwrap_or(0);
        if destination_size > temp_size {
            fs::remove_file(temp_path).map_err(|error| error.to_string())?;
        } else {
            fs::remove_file(destination).map_err(|error| error.to_string())?;
            return Ok(());
        }
    }
    fs::rename(destination, temp_path)
        .map_err(|error| format!("No se pudo conservar el parcial aria2c: {error}"))
}

fn aria2_control_path(destination: &Path) -> std::path::PathBuf {
    std::path::PathBuf::from(format!("{}.aria2", destination.display()))
}

fn file_looks_like_html(path: &Path) -> Result<bool, String> {
    let mut file = File::open(path).map_err(|error| error.to_string())?;
    let mut prefix = Vec::new();
    std::io::Read::by_ref(&mut file)
        .take(1024)
        .read_to_end(&mut prefix)
        .map_err(|error| error.to_string())?;
    Ok(html_prefix(&prefix))
}

fn finalize_job(
    db_path: &Path,
    id: i64,
    destination: &Path,
    final_size: u64,
) -> Result<(), String> {
    finalize_http_job(
        db_path,
        id,
        destination,
        final_size,
        "Completada y verificada · aria2c",
    )
}

fn parse_bool(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on" | "enabled"
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn whitelist_accepts_supported_media_hosts_only() {
        assert!(is_supported_media_host(
            &Url::parse("https://youtu.be/abc").unwrap()
        ));
        assert!(is_supported_media_host(
            &Url::parse("https://www.tiktok.com/@a/video/1").unwrap()
        ));
        assert!(!is_supported_media_host(
            &Url::parse("https://example.com/index.html").unwrap()
        ));
        assert!(!is_supported_media_host(
            &Url::parse("https://youtube.com.attacker.example/file").unwrap()
        ));
    }

    #[test]
    fn html_prefix_detection_is_conservative() {
        assert!(html_prefix(b"\n<!doctype html><html>"));
        assert!(html_prefix(b"<html><body>login</body>"));
        assert!(!html_prefix(b"MZ\x90\0\x03\0"));
        assert!(!html_prefix(b"PK\x03\x04archive"));
    }

    #[test]
    fn feature_flag_values_are_explicit() {
        assert!(parse_bool("true"));
        assert!(parse_bool("1"));
        assert!(!parse_bool("false"));
        assert!(!parse_bool("0"));
    }

    #[test]
    fn retry_classification_does_not_loop_on_http_auth_or_rate_limits() {
        assert!(!aria2_failure_is_retryable(22, "HTTP error 403 Forbidden"));
        assert!(!aria2_failure_is_retryable(
            22,
            "HTTP error 429 Too Many Requests"
        ));
        assert!(aria2_failure_is_retryable(2, "timeout while connecting"));
        assert!(aria2_failure_is_retryable(
            1,
            "network connection reset by peer"
        ));
    }

    #[test]
    fn preallocated_aria2_pair_is_kept_for_resume() {
        let root = std::env::temp_dir().join(format!(
            "cacatools-aria2-resume-test-{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).expect("test directory");
        let destination = root.join("large.bin");
        let partial = root.join("large.bin.part");
        fs::write(&destination, vec![0u8; 42 * 1024 * 1024]).expect("preallocated file");
        fs::write(&partial, vec![1u8; 8 * 1024 * 1024]).expect("old partial");
        fs::write(aria2_control_path(&destination), b"control").expect("aria2 control file");

        move_output_to_temp(&destination, &partial).expect("preserve aria2 pair");
        assert!(destination.is_file());
        assert!(aria2_control_path(&destination).is_file());
        assert_eq!(
            partial.metadata().expect("partial metadata").len(),
            8 * 1024 * 1024
        );
        let _ = fs::remove_dir_all(root);
    }
}
