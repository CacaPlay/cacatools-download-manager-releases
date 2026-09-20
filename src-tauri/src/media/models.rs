use serde::Serialize;

#[derive(Serialize)]
pub(crate) struct MediaFormatSnapshot {
    pub(crate) id: String,
    pub(crate) label: String,
    pub(crate) ext: String,
    pub(crate) resolution: String,
    pub(crate) audio_only: bool,
    pub(crate) filesize: Option<u64>,
    pub(crate) filesize_estimated: bool,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) audio_codec: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) bitrate_kbps: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) sample_rate_hz: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) channels: Option<u32>,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) container: String,
    pub(crate) lossless: bool,
}

#[derive(Serialize)]
pub(crate) struct MediaItemSnapshot {
    pub(crate) source_id: String,
    pub(crate) source_url: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) metadata_url: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) selected_source_url: String,
    pub(crate) title: String,
    pub(crate) creator: String,
    pub(crate) duration_label: String,
    pub(crate) duration_seconds: Option<f64>,
    pub(crate) thumbnail: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) spotify_url: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) provider: String,
    #[serde(default)]
    pub(crate) match_similarity: f64,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) isrc: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) album: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) album_artist: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) release_date: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) track_number: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) disc_number: Option<u32>,
    #[serde(default)]
    pub(crate) explicit: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) playlist_position: Option<u32>,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) resolution_state: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub(crate) resolution_message: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) resolution_candidates: Vec<SpotifyCandidateSnapshot>,
}

#[derive(Clone, Serialize)]
pub(crate) struct SpotifyCandidateSnapshot {
    pub(crate) source_url: String,
    pub(crate) title: String,
    pub(crate) creator: String,
    pub(crate) duration_label: String,
    pub(crate) duration_seconds: Option<f64>,
    pub(crate) thumbnail: String,
    pub(crate) confidence: f64,
    pub(crate) provider: String,
}

#[derive(Serialize)]
pub(crate) struct MediaAnalysisSnapshot {
    pub(crate) kind: String,
    pub(crate) title: String,
    pub(crate) creator: String,
    pub(crate) thumbnail: String,
    pub(crate) duration_label: String,
    pub(crate) duration_seconds: Option<f64>,
    pub(crate) formats: Vec<MediaFormatSnapshot>,
    pub(crate) items: Vec<MediaItemSnapshot>,
    pub(crate) resolver: String,
}
