use std::path::Path;
use std::time::Duration;

use reqwest::blocking::Client;
use tauri::AppHandle;

use super::{analyze_media_url, duration_label, MediaAnalysisSnapshot};
use crate::{
    presentation_thumbnail_url, resolve_spotify_track, spotify_access_token, spotify_api_source,
    spotify_source_parts,
};

pub(crate) fn resolve_spotify_analysis_sync(
    url: &str,
    app: &AppHandle,
    db_path: &Path,
) -> Result<MediaAnalysisSnapshot, String> {
    let (kind, id, canonical_url) = spotify_source_parts(url)?;
    let client = Client::builder()
        .timeout(Duration::from_secs(12))
        .user_agent("CacaTools Download Manager/0.25.1")
        .gzip(true)
        .build()
        .map_err(|error| error.to_string())?;
    let token = spotify_access_token(&client, db_path)?;
    let (title, creator, thumbnail, tracks, _) =
        spotify_api_source(&client, &token, &kind, &id, &canonical_url)?;
    if tracks.is_empty() {
        return Err("metadata_incomplete: Spotify no devolvió canciones".into());
    }
    let items = tracks
        .iter()
        .map(|track| resolve_spotify_track(track, app))
        .collect::<Vec<_>>();
    let formats = items
        .iter()
        .find(|item| item.resolution_state == "ready" && !item.selected_source_url.is_empty())
        .and_then(|item| analyze_media_url(item.selected_source_url.clone(), app.clone()).ok())
        .map(|snapshot| snapshot.formats)
        .unwrap_or_default();
    let total_duration = tracks
        .iter()
        .filter_map(|track| track.duration_seconds)
        .sum::<f64>();
    Ok(MediaAnalysisSnapshot {
        kind: if kind == "track" { "video" } else { "playlist" }.into(),
        title,
        creator,
        thumbnail: presentation_thumbnail_url(&thumbnail),
        duration_label: duration_label(Some(total_duration)),
        duration_seconds: (total_duration > 0.0).then_some(total_duration),
        formats,
        items,
        resolver: "Spotify Web API + YouTube Music / yt-dlp".into(),
    })
}
