use std::sync::Arc;
use url::Url;

use crate::{
    ensure_public_network_resolution, first_string, media_host_is, normalize_tiktok_source_url,
    parse_public_http_url, player_preview_audio_entry, player_preview_low_progressive_entry,
    player_preview_max_height, player_preview_progressive_entry, player_preview_qualities,
    player_preview_quality_limited, player_preview_selected_entry, player_preview_technical,
    player_preview_technical_for_entries, thumbnail_from, validate_media_url, AppHandle,
    PlayerOnlineEmbedSnapshot, PlayerOnlinePreviewSnapshot, Value, WindowOperation,
};

use super::{
    instagram_post_id, pinterest_pin_id, resolve_pinterest_short_link, resolver, tiktok_video_id,
    youtube_preview_thumbnail,
};

pub(crate) fn resolve_online_embed(url: String) -> Result<PlayerOnlineEmbedSnapshot, String> {
    let validated = validate_media_url(&url)?;
    let initial = Url::parse(&validated)
        .map_err(|_| "El enlace de reproducción online no es válido".to_string())?;
    ensure_public_network_resolution(&initial)?;

    if media_host_is(&initial, "tiktok.com") {
        let id = tiktok_video_id(&initial)
            .ok_or_else(|| "No se pudo identificar el video de TikTok".to_string())?;
        return Ok(PlayerOnlineEmbedSnapshot {
            url: format!(
                "https://www.tiktok.com/player/v1/{id}?autoplay=0&controls=1&progress_bar=1&play_button=1&volume_control=1&fullscreen_button=1&timestamp=1"
            ),
            platform: "TikTok".into(),
        });
    }

    if media_host_is(&initial, "instagram.com") {
        let id = instagram_post_id(&initial)
            .ok_or_else(|| "No se pudo identificar la publicación de Instagram".to_string())?;
        return Ok(PlayerOnlineEmbedSnapshot {
            url: format!("https://www.instagram.com/p/{id}/embed/"),
            platform: "Instagram".into(),
        });
    }

    if media_host_is(&initial, "pin.it") {
        let resolved = resolve_pinterest_short_link(&initial)?;
        let id = pinterest_pin_id(&resolved)
            .ok_or_else(|| "No se pudo identificar el Pin de Pinterest".to_string())?;
        return Ok(PlayerOnlineEmbedSnapshot {
            url: format!("https://assets.pinterest.com/ext/embed.html?id={id}"),
            platform: "Pinterest".into(),
        });
    }

    if media_host_is(&initial, "pinterest.com") {
        let id = pinterest_pin_id(&initial)
            .ok_or_else(|| "No se pudo identificar el Pin de Pinterest".to_string())?;
        return Ok(PlayerOnlineEmbedSnapshot {
            url: format!("https://assets.pinterest.com/ext/embed.html?id={id}"),
            platform: "Pinterest".into(),
        });
    }

    Err("Esta plataforma no ofrece un reproductor oficial compatible".into())
}

pub(crate) fn build_player_online_preview_snapshot(
    parsed: Url,
    json: Value,
) -> Result<PlayerOnlinePreviewSnapshot, String> {
    let selected = player_preview_selected_entry(&json);
    let stream_url = first_string(selected, &["url"]);
    if stream_url.is_empty() {
        return Err("La fuente no expuso un flujo directo reproducible".into());
    }
    let stream = parse_public_http_url(&stream_url, "El flujo temporal no es válido")?;
    ensure_public_network_resolution(&stream)?;

    let audio_stream = player_preview_audio_entry(&json)
        .map(|entry| first_string(entry, &["url"]))
        .filter(|url| !url.is_empty())
        .map(|url| parse_public_http_url(&url, "El flujo de audio temporal no es válido"))
        .transpose()?;
    if let Some(audio_stream) = &audio_stream {
        ensure_public_network_resolution(audio_stream)?;
    }

    let progressive = player_preview_progressive_entry(&json);
    let progressive_stream = progressive
        .map(|entry| first_string(entry, &["url"]))
        .filter(|url| !url.is_empty())
        .map(|url| parse_public_http_url(&url, "El flujo progresivo temporal no es válido"))
        .transpose()?;
    if let Some(progressive_stream) = &progressive_stream {
        ensure_public_network_resolution(progressive_stream)?;
    }

    let low_progressive = player_preview_low_progressive_entry(&json);
    let low_progressive_stream = low_progressive
        .map(|entry| first_string(entry, &["url"]))
        .filter(|url| !url.is_empty())
        .map(|url| parse_public_http_url(&url, "El flujo progresivo seguro no es válido"))
        .transpose()?;
    if let Some(low_progressive_stream) = &low_progressive_stream {
        ensure_public_network_resolution(low_progressive_stream)?;
    }

    let fallback_audio_url = audio_stream
        .as_ref()
        .map(ToString::to_string)
        .unwrap_or_default();
    let qualities = player_preview_qualities(&json, &fallback_audio_url)
        .into_iter()
        .filter_map(|mut quality| {
            let parsed_video =
                parse_public_http_url(&quality.url, "El flujo de calidad temporal no es valido")
                    .ok()?;
            if ensure_public_network_resolution(&parsed_video).is_err() {
                return None;
            }
            quality.url = parsed_video.to_string();
            if !quality.audio_url.is_empty() {
                let parsed_audio = parse_public_http_url(
                    &quality.audio_url,
                    "El flujo de audio de calidad no es valido",
                )
                .ok()?;
                if ensure_public_network_resolution(&parsed_audio).is_err() {
                    return None;
                }
                quality.audio_url = parsed_audio.to_string();
            }
            Some(quality)
        })
        .collect::<Vec<_>>();

    let width = selected
        .get("width")
        .and_then(Value::as_u64)
        .and_then(|value| u32::try_from(value).ok());
    let height = selected
        .get("height")
        .and_then(Value::as_u64)
        .and_then(|value| u32::try_from(value).ok());
    let max_height = player_preview_max_height(&json).or(height);

    Ok(PlayerOnlinePreviewSnapshot {
        title: first_string(&json, &["title", "fulltitle"]),
        creator: first_string(&json, &["uploader", "channel", "creator", "artist"]),
        thumbnail: {
            let stable = youtube_preview_thumbnail(&parsed);
            if stable.is_empty() {
                thumbnail_from(&json)
            } else {
                stable
            }
        },
        stream_url: stream.to_string(),
        qualities,
        audio_stream_url: audio_stream.map(|url| url.to_string()).unwrap_or_default(),
        width,
        height,
        max_height,
        quality_limited: player_preview_quality_limited(height, max_height),
        technical: player_preview_technical(&json),
        progressive_stream_url: progressive_stream
            .as_ref()
            .map(ToString::to_string)
            .unwrap_or_default(),
        progressive_width: progressive
            .and_then(|entry| entry.get("width"))
            .and_then(Value::as_u64)
            .and_then(|value| u32::try_from(value).ok()),
        progressive_height: progressive
            .and_then(|entry| entry.get("height"))
            .and_then(Value::as_u64)
            .and_then(|value| u32::try_from(value).ok()),
        progressive_technical: progressive
            .map(|entry| player_preview_technical_for_entries(&json, entry, entry)),
        low_progressive_stream_url: low_progressive_stream
            .as_ref()
            .map(ToString::to_string)
            .unwrap_or_default(),
        low_progressive_width: low_progressive
            .and_then(|entry| entry.get("width"))
            .and_then(Value::as_u64)
            .and_then(|value| u32::try_from(value).ok()),
        low_progressive_height: low_progressive
            .and_then(|entry| entry.get("height"))
            .and_then(Value::as_u64)
            .and_then(|value| u32::try_from(value).ok()),
        low_progressive_technical: low_progressive
            .map(|entry| player_preview_technical_for_entries(&json, entry, entry)),
    })
}
pub(crate) fn player_online_preview_snapshot(
    url: String,
    app: AppHandle,
) -> Result<PlayerOnlinePreviewSnapshot, String> {
    player_online_preview_snapshot_with_operation(url, app, None)
}

pub(crate) fn player_online_preview_snapshot_with_operation(
    url: String,
    app: AppHandle,
    operation: Option<Arc<WindowOperation>>,
) -> Result<PlayerOnlinePreviewSnapshot, String> {
    let validated = validate_media_url(&url)?;
    let parsed = Url::parse(&validated).map_err(|_| "El enlace de vista previa no es válido")?;
    ensure_public_network_resolution(&parsed)?;
    let normalized = normalize_tiktok_source_url(parsed);
    let resolved = resolver::resolve_preview(validated, app, operation)?;
    build_player_online_preview_snapshot(normalized, resolved.json)
}
