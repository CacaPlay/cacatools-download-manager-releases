use crate::*;
use tauri::Emitter;

#[tauri::command]
pub(crate) fn get_appearance_settings(
    state: State<'_, LocalState>,
) -> Result<Option<AppearanceSettings>, String> {
    crate::settings::get_appearance_settings(state)
}

#[tauri::command]
pub(crate) fn save_appearance_settings(
    app: AppHandle,
    appearance: AppearanceSettings,
    state: State<'_, LocalState>,
) -> Result<(), String> {
    let saved = crate::settings::save_appearance_settings(appearance, state)?;
    let revision = saved.revision;
    crate::windows::backdrop::apply_to_all(&app, &saved.surface_mode);
    app.emit(
        "appearance-changed",
        serde_json::json!({
            "appearance": saved,
            "revision": revision,
            "persisted": true,
            "sourceWindow": "command"
        }),
    )
    .map_err(|error| error.to_string())?;
    Ok(())
}

#[tauri::command]
pub(crate) fn window_behavior_settings(
    state: State<'_, LocalState>,
) -> Result<WindowBehaviorSettings, String> {
    crate::settings::window_behavior_settings(state)
}

#[tauri::command]
pub(crate) fn save_window_behavior_settings(
    settings: WindowBehaviorSettings,
    state: State<'_, LocalState>,
) -> Result<WindowBehaviorSettings, String> {
    crate::settings::save_window_behavior_settings(settings, state)
}

#[tauri::command]
pub(crate) fn get_experience_settings(
    state: State<'_, LocalState>,
) -> Result<ExperienceSettings, String> {
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    Ok(crate::settings::read_experience_settings(&connection))
}

#[tauri::command]
pub(crate) fn save_experience_settings(
    settings: ExperienceSettings,
    state: State<'_, LocalState>,
) -> Result<ExperienceSettings, String> {
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    crate::settings::persist_experience_settings(&connection, &settings)
}

#[tauri::command]
pub(crate) fn get_bandwidth_settings(
    state: State<'_, LocalState>,
) -> Result<BandwidthSettings, String> {
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    Ok(crate::downloads::read_bandwidth_settings(&connection))
}

#[tauri::command]
pub(crate) fn save_bandwidth_settings(
    settings: BandwidthSettings,
    state: State<'_, LocalState>,
) -> Result<BandwidthSettings, String> {
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    crate::downloads::persist_bandwidth_settings(&connection, settings)
}

#[tauri::command]
pub(crate) fn set_download_speed_limit(
    id: i64,
    settings: BandwidthSettings,
    state: State<'_, LocalState>,
) -> Result<BandwidthSettings, String> {
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    crate::downloads::persist_job_bandwidth_settings(&connection, id, settings)
}

#[tauri::command]
pub(crate) fn set_playlist_speed_limit(
    batch_id: i64,
    settings: BandwidthSettings,
    state: State<'_, LocalState>,
) -> Result<BandwidthSettings, String> {
    let connection = state
        .connection
        .lock()
        .map_err(|_| "No se pudo bloquear la base local".to_string())?;
    crate::downloads::persist_playlist_bandwidth_settings(&connection, batch_id, settings)
}

#[tauri::command]
pub(crate) fn save_download_concurrency(
    settings: DownloadConcurrencySettings,
    state: State<'_, LocalState>,
) -> Result<DownloadConcurrencySettings, String> {
    let saved = {
        let connection = state
            .connection
            .lock()
            .map_err(|_| "No se pudo bloquear la base local".to_string())?;
        crate::downloads::persist_download_concurrency_settings(&connection, settings)?
    };
    state.dispatcher.update_concurrency(saved);
    Ok(saved)
}

#[tauri::command]
pub(crate) fn spotify_auth_status(
    state: State<'_, LocalState>,
) -> Result<SpotifyAuthStatus, String> {
    crate::spotify_auth_status(&state.db_path)
}

#[tauri::command]
pub(crate) async fn spotify_login(
    app: AppHandle,
    state: State<'_, LocalState>,
) -> Result<SpotifyAuthStatus, String> {
    let db_path = state.db_path.clone();
    tauri::async_runtime::spawn_blocking(move || crate::spotify_login(app, &db_path))
        .await
        .map_err(|error| format!("No se pudo completar el login de Spotify: {error}"))?
}

#[tauri::command]
pub(crate) fn spotify_logout(state: State<'_, LocalState>) -> Result<(), String> {
    crate::spotify_logout(&state.db_path)
}
