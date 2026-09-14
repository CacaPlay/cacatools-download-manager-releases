use rusqlite::{params, OptionalExtension};
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Emitter, Manager, State, WebviewUrl};
use url::Url;

use crate::{
    begin_window_operation, build_media_player_window, ensure_public_network_resolution,
    invalidate_window_operation, output_mode_conversion_state, player_media_kind,
    probe_player_technical, validate_media_url, LocalState, PlayerMediaSnapshot,
    PlayerPlaylistQueueItem, PlayerPlaylistQueueSnapshot,
};

pub(crate) fn online_player_query(validated: &str) -> String {
    let mut serializer = url::form_urlencoded::Serializer::new(String::new());
    serializer.append_pair("preview", validated);
    serializer.finish()
}

pub(crate) async fn player_media_snapshot(
    job_id: i64,
    app: AppHandle,
    state: State<'_, LocalState>,
) -> Result<PlayerMediaSnapshot, String> {
    let row = {
        let connection = state
            .connection
            .lock()
            .map_err(|_| "No se pudo bloquear la base local".to_string())?;
        connection
            .query_row(
                "SELECT j.title,j.status,j.detail,j.progress,
                    COALESCE(NULLIF(mj.output_path,''),NULLIF(pi.output_path,''),''),
                    COALESCE(NULLIF(pi.thumbnail,''),NULLIF(mj.thumbnail,''),''),
                    mj.output_mode,mj.destination_dir
             FROM jobs j
             JOIN media_jobs mj ON mj.job_id=j.id
             LEFT JOIN playlist_items pi ON pi.job_id=j.id
             WHERE j.id=?1",
                params![job_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, f64>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, String>(5)?,
                        row.get::<_, String>(6)?,
                        row.get::<_, String>(7)?,
                    ))
                },
            )
            .optional()
            .map_err(|error| error.to_string())?
            .ok_or_else(|| "La tarea seleccionada no es una descarga multimedia".to_string())?
    };

    let (title, status, detail, progress, stored_path, thumbnail, output_mode, destination_dir) =
        row;
    let candidate = PathBuf::from(&stored_path);
    let playable_path = if status == "completed" && candidate.is_file() {
        let canonical_path = candidate.canonicalize().ok();
        let canonical_destination = PathBuf::from(destination_dir).canonicalize().ok();
        match (canonical_path, canonical_destination) {
            (Some(path), Some(destination)) => {
                path.starts_with(destination.as_path()).then_some(path)
            }
            _ => None,
        }
    } else {
        None
    };
    let playable = playable_path.is_some();
    let kind_path = playable_path.as_deref().unwrap_or(candidate.as_path());
    let kind = player_media_kind(&output_mode, kind_path);
    let state_title = match status.as_str() {
        "completed" if playable => "Listo para reproducir",
        "completed" => "Archivo local no disponible",
        "running" => "Descarga todavía en curso",
        "paused" => "Descarga en pausa",
        "failed" => "La descarga terminó con error",
        "cancelled" => "La descarga fue cancelada",
        _ => "Preparando descarga multimedia",
    }
    .to_string();
    let message = if playable {
        "Se reproducirá el archivo local final validado por CacaTools.".to_string()
    } else if status == "completed" {
        "El registro está completado, pero el archivo final ya no existe dentro de su carpeta de descarga.".to_string()
    } else {
        "CacaTools no reproduce archivos .part, fragmentos incompletos ni vídeo y audio separados. El reproductor se habilitará cuando exista un archivo final seguro.".to_string()
    };
    if let Some(path) = playable_path.as_deref() {
        app.asset_protocol_scope()
            .allow_file(path)
            .map_err(|error| {
                format!("No se pudo autorizar el archivo local para el reproductor: {error}")
            })?;
    }
    // ffprobe can take noticeable time on a large, fragmented, or partially
    // indexed file. This command is async so the Tauri/WebView UI thread is
    // never blocked while collecting optional technical metadata.
    let technical = match (state.media_runtime.clone(), playable_path.clone()) {
        (Some(runtime), Some(path)) => {
            tauri::async_runtime::spawn_blocking(move || probe_player_technical(&runtime, &path))
                .await
                .ok()
                .flatten()
        }
        _ => None,
    };
    let converted = output_mode_conversion_state(&output_mode);

    Ok(PlayerMediaSnapshot {
        job_id,
        title,
        status,
        detail,
        progress,
        thumbnail,
        output_mode,
        kind,
        playable,
        local_path: playable_path
            .map(|path| path.to_string_lossy().to_string())
            .unwrap_or_default(),
        state_title,
        message,
        converted,
        technical,
    })
}
pub(crate) fn player_playlist_queue_snapshot(
    batch_id: i64,
    state: State<'_, LocalState>,
) -> Result<PlayerPlaylistQueueSnapshot, String> {
    if batch_id <= 0 {
        return Err("La playlist seleccionada no es válida".into());
    }
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    let title = connection
        .query_row(
            "SELECT title FROM playlist_batches WHERE id=?1",
            params![batch_id],
            |row| row.get::<_, String>(0),
        )
        .optional()
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "La playlist ya no existe".to_string())?;
    let mut statement = connection
        .prepare(
            "SELECT pi.job_id,pi.position,COALESCE(pi.title,''),COALESCE(pi.creator,''),COALESCE(pi.thumbnail,''), \
                    COALESCE(pi.status,''),COALESCE(pi.output_path,mj.output_path,'') \
             FROM playlist_items pi \
             LEFT JOIN media_jobs mj ON mj.job_id=pi.job_id \
             WHERE pi.batch_id=?1 \
             ORDER BY pi.position",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(params![batch_id], |row| {
            let status = row.get::<_, String>(5)?;
            let output_path = row.get::<_, String>(6)?;
            let playable = status == "completed"
                && !output_path.is_empty()
                && Path::new(&output_path).is_file();
            Ok(PlayerPlaylistQueueItem {
                job_id: row.get(0)?,
                position: row.get(1)?,
                title: row.get(2)?,
                creator: row.get(3)?,
                thumbnail: row.get(4)?,
                status,
                playable,
            })
        })
        .map_err(|error| error.to_string())?;
    let items = rows
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?;
    Ok(PlayerPlaylistQueueSnapshot {
        batch_id,
        title,
        items,
    })
}
pub(crate) async fn open_online_media_player(url: String, app: AppHandle) -> Result<(), String> {
    let (validated, parsed) = tauri::async_runtime::spawn_blocking(move || {
        let validated = validate_media_url(&url)?;
        let parsed = Url::parse(&validated).map_err(|_| "El enlace multimedia no es válido")?;
        ensure_public_network_resolution(&parsed)?;
        Ok::<_, String>((validated, parsed))
    })
    .await
    .map_err(|error| format!("No se pudo preparar el reproductor: {error}"))??;
    if parsed
        .query_pairs()
        .any(|(key, value)| key == "cacatools_preview" && value == "embedded")
    {
        // The preparation window owns the official YouTube IFrame preview.
        return Ok(());
    }

    // Every new player route owns a fresh generation. A close keeps a
    // cancelled tombstone, so a late snapshot from the previous route cannot
    // start work again; the next explicit open replaces it here.
    let operations = app.state::<LocalState>().preparation_operations.clone();
    begin_window_operation(&operations, "player");

    // Online playback always starts in the internal CacaTools player. The UI
    // may offer an explicit external action only after the provider explains
    // that embedding is unavailable.
    let query = online_player_query(&validated);

    if app.get_webview_window("player").is_some() {
        let route = serde_json::to_string(&format!("./index.html?{query}"))
            .map_err(|error| error.to_string())?;
        let app_for_ui = app.clone();
        return crate::subwindows::run_on_main_thread(app, move || {
            let window = app_for_ui
                .get_webview_window("player")
                .ok_or_else(|| "La ventana del reproductor ya no esta disponible".to_string())?;
            window.unminimize().map_err(|error| error.to_string())?;
            window.show().map_err(|error| error.to_string())?;
            window.set_focus().map_err(|error| error.to_string())?;
            window
                .eval(format!("window.location.replace({route});"))
                .map_err(|error| error.to_string())
        })
        .await;
    }

    let player_url = WebviewUrl::App(format!("app-ui/player/index.html?{query}").into());
    build_media_player_window(app, player_url).await
}
pub(crate) async fn player_resize_for_media(
    width: f64,
    height: f64,
    kind: String,
    details_open: bool,
    app: AppHandle,
) -> Result<(), String> {
    let _window = app
        .get_webview_window("player")
        .ok_or_else(|| "La ventana del reproductor no está disponible".to_string())?;

    let (target_width, target_height) = if kind.trim() == "audio" {
        // Audio keeps the same visual footprint as the video player; the
        // artwork occupies the media stage while the transport stays below.
        (1360.0, if details_open { 860.0 } else { 765.0 })
    } else {
        let safe_width = if width.is_finite() && width > 0.0 {
            width
        } else {
            854.0
        };
        let safe_height = if height.is_finite() && height > 0.0 {
            height
        } else {
            480.0
        };
        // Preserve square/vertical media so the WebView can letterbox it
        // instead of sizing the native window as if every source were 16:9.
        let aspect = (safe_width / safe_height).clamp(0.35, 2.4);
        let mut media_width = safe_width.clamp(1360.0, 1600.0);
        let mut media_height = media_width / aspect;
        if media_height > 920.0 {
            media_height = 920.0;
            media_width = media_height * aspect;
        }
        (media_width, media_height)
    };

    crate::subwindows::run_on_main_thread(app.clone(), move || {
        let window = app
            .get_webview_window("player")
            .ok_or_else(|| "La ventana del reproductor no esta disponible".to_string())?;
        window
            .set_size(tauri::LogicalSize::new(target_width, target_height))
            .map_err(|error| error.to_string())
    })
    .await
}
pub(crate) async fn open_media_player(job_id: i64, app: AppHandle) -> Result<(), String> {
    if job_id <= 0 {
        return Err("La descarga multimedia seleccionada no es válida".into());
    }
    if app.get_webview_window("player").is_some() {
        return crate::subwindows::run_on_main_thread(app.clone(), move || {
            let window = app
                .get_webview_window("player")
                .ok_or_else(|| "La ventana del reproductor ya no esta disponible".to_string())?;
            window.unminimize().map_err(|error| error.to_string())?;
            window.show().map_err(|error| error.to_string())?;
            window.set_focus().map_err(|error| error.to_string())?;
            window
                .eval(format!("window.cacatoolsPlayerLoadJob?.({job_id});"))
                .map_err(|error| error.to_string())
        })
        .await;
    }
    let url = WebviewUrl::App(format!("app-ui/player/index.html?job={job_id}").into());
    build_media_player_window(app, url).await
}
pub(crate) async fn open_playlist_media_player(
    batch_id: i64,
    app: AppHandle,
) -> Result<(), String> {
    if batch_id <= 0 {
        return Err("La playlist seleccionada no es válida".into());
    }
    if app.get_webview_window("player").is_some() {
        return crate::subwindows::run_on_main_thread(app.clone(), move || {
            let window = app
                .get_webview_window("player")
                .ok_or_else(|| "La ventana del reproductor ya no esta disponible".to_string())?;
            window.unminimize().map_err(|error| error.to_string())?;
            window.show().map_err(|error| error.to_string())?;
            window.set_focus().map_err(|error| error.to_string())?;
            window
                .eval(format!("window.cacatoolsPlayerLoadPlaylist?.({batch_id});"))
                .map_err(|error| error.to_string())
        })
        .await;
    }
    let url = WebviewUrl::App(format!("app-ui/player/index.html?playlist={batch_id}").into());
    build_media_player_window(app, url).await
}

pub(crate) async fn player_start_dragging(app: AppHandle) -> Result<(), String> {
    crate::subwindows::run_on_main_thread(app.clone(), move || {
        let window = app
            .get_webview_window("player")
            .ok_or_else(|| "La ventana del reproductor no está disponible".to_string())?;
        window.start_dragging().map_err(|error| error.to_string())
    })
    .await
}
pub(crate) async fn player_window_action(action: String, app: AppHandle) -> Result<(), String> {
    if action.trim() == "close" {
        invalidate_window_operation(&app.state::<LocalState>().preparation_operations, "player");
    }
    crate::subwindows::run_on_main_thread(app.clone(), move || {
        let window = app
            .get_webview_window("player")
            .ok_or_else(|| "La ventana del reproductor no está disponible".to_string())?;
        match action.trim() {
            "minimize" => window.minimize(),
            "maximize" => {
                if window.is_maximized().map_err(|error| error.to_string())? {
                    window.unmaximize()
                } else {
                    window.maximize()
                }
            }
            "fullscreen" => {
                let entering = !window.is_fullscreen().map_err(|error| error.to_string())?;
                window
                    .set_fullscreen(entering)
                    .map_err(|error| error.to_string())?;
                let _ = app.emit("player-fullscreen-changed", entering);
                if entering {
                    // set_fullscreen owns the monitor bounds on Windows.
                    // Reapplying the physical monitor size afterwards can
                    // restore a work-area-sized client rectangle, leaving a
                    // taskbar-height black strip and cropping non-16:9 media.
                    window.set_focus()
                } else {
                    window.set_focus()
                }
            }
            "close" => window.close(),
            _ => return Err("La acción de ventana no es válida".into()),
        }
        .map_err(|error| error.to_string())
    })
    .await
}
