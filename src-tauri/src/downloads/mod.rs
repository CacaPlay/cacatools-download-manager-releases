#![allow(clippy::invisible_characters)]

use rusqlite::Connection;

mod aria2;
mod bandwidth;
mod commands;
mod concurrency;
mod http;
mod segmented;
mod storage;
mod validation;
mod worker;

pub(crate) use bandwidth::*;
pub(crate) use commands::*;
pub(crate) use concurrency::*;
pub(crate) use http::*;
pub(crate) use storage::*;
pub(crate) use validation::*;
pub(crate) use worker::*;

use http::{
    bytes_look_like_html, http_v1_observation, request_download_response_with_range,
    response_content_range,
};
use segmented::{remove_http_segment_artifacts, HTTP_SEGMENT_MAX};

pub(crate) fn http_aria2_feature_enabled(connection: &Connection) -> bool {
    aria2::http_aria2_enabled(connection)
}
