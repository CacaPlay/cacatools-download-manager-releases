use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Condvar, Mutex, OnceLock};
use std::time::{Duration, Instant};

use tauri::AppHandle;

use super::search_media_internal_with_timeout_cancelable;
use crate::MediaSearchResult;

const SEARCH_CACHE_TTL: Duration = Duration::from_secs(30);
const SEARCH_CACHE_LIMIT: usize = 32;
const SEARCH_CONTRACT_VERSION: &str = "search-metadata-v1";
const SEARCH_PROVIDER: &str = "youtube";
const SEARCH_SESSION_FINGERPRINT: &str = "anonymous-public-v1";

#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq)]
enum SearchKind {
    Suggestions,
    Title,
}

#[derive(Clone, Debug, Hash, PartialEq, Eq)]
struct SearchKey {
    query: String,
    offset: usize,
    limit: usize,
    provider: String,
    session_fingerprint: String,
    contract_version: String,
    kind: SearchKind,
}

struct SearchCacheEntry {
    value: Vec<MediaSearchResult>,
    expires_at: Instant,
    last_used: u64,
}

struct SearchFlight {
    result: Mutex<Option<Result<Vec<MediaSearchResult>, String>>>,
    ready: Condvar,
    consumers: AtomicUsize,
    cancelled: AtomicBool,
}

#[derive(Default)]
struct SearchState {
    cache: HashMap<SearchKey, SearchCacheEntry>,
    in_flight: HashMap<SearchKey, Arc<SearchFlight>>,
    clock: u64,
}

struct SearchConsumer {
    flight: Arc<SearchFlight>,
}

impl Drop for SearchConsumer {
    fn drop(&mut self) {
        if self.flight.consumers.fetch_sub(1, Ordering::SeqCst) == 1
            && self
                .flight
                .result
                .lock()
                .map(|result| result.is_none())
                .unwrap_or(true)
        {
            self.flight.cancelled.store(true, Ordering::SeqCst);
            self.flight.ready.notify_all();
        }
    }
}

enum SearchAcquire {
    Cache(Vec<MediaSearchResult>),
    Flight {
        flight: Arc<SearchFlight>,
        leader: bool,
    },
}

static SEARCH_STATE: OnceLock<Mutex<SearchState>> = OnceLock::new();

pub(crate) async fn search_video_suggestions(
    query: String,
    limit: Option<usize>,
    app: AppHandle,
) -> Result<Vec<MediaSearchResult>, String> {
    search_video_suggestions_page(query, limit, Some(0), app).await
}

pub(crate) async fn search_video_suggestions_page(
    query: String,
    limit: Option<usize>,
    offset: Option<usize>,
    app: AppHandle,
) -> Result<Vec<MediaSearchResult>, String> {
    let query = query.trim().to_string();
    if query.len() < 2 || query.len() > 180 {
        cancel_all_searches();
        return Ok(Vec::new());
    }
    let limit = limit.unwrap_or(10).clamp(1, 20);
    let offset = offset.unwrap_or(0).min(40);
    run_search(
        query,
        limit,
        offset,
        SearchKind::Suggestions,
        Duration::from_secs(7),
        app,
    )
    .await
    .map_err(|error| format!("La búsqueda predictiva se interrumpió: {error}"))
}

pub(crate) async fn search_media_by_title(
    query: String,
    limit: Option<usize>,
    app: AppHandle,
) -> Result<Vec<MediaSearchResult>, String> {
    search_media_by_title_page(query, limit, Some(0), app).await
}

pub(crate) async fn search_media_by_title_page(
    query: String,
    limit: Option<usize>,
    offset: Option<usize>,
    app: AppHandle,
) -> Result<Vec<MediaSearchResult>, String> {
    let query = query.trim().to_string();
    let limit = limit.unwrap_or(15).clamp(1, 30);
    let offset = offset.unwrap_or(0).min(40);
    run_search(
        query,
        limit,
        offset,
        SearchKind::Title,
        Duration::from_secs(16),
        app,
    )
    .await
    .map_err(|error| format!("La búsqueda multimedia se interrumpió: {error}"))
}

async fn run_search(
    query: String,
    limit: usize,
    offset: usize,
    kind: SearchKind,
    timeout: Duration,
    app: AppHandle,
) -> Result<Vec<MediaSearchResult>, String> {
    let key = SearchKey {
        query: normalize_search_key(&query),
        offset,
        limit,
        provider: SEARCH_PROVIDER.into(),
        session_fingerprint: SEARCH_SESSION_FINGERPRINT.into(),
        contract_version: SEARCH_CONTRACT_VERSION.into(),
        kind,
    };
    tauri::async_runtime::spawn_blocking(move || {
        execute_search(key, query, limit, offset, timeout, app)
    })
    .await
    .map_err(|error| format!("La búsqueda terminó de forma inesperada: {error}"))?
}

fn execute_search(
    key: SearchKey,
    query: String,
    limit: usize,
    offset: usize,
    timeout: Duration,
    app: AppHandle,
) -> Result<Vec<MediaSearchResult>, String> {
    let acquired = {
        let state = SEARCH_STATE.get_or_init(|| Mutex::new(SearchState::default()));
        let mut state = state
            .lock()
            .map_err(|_| "No se pudo bloquear la caché de búsquedas".to_string())?;
        search_cache_prune(&mut state);
        if state.cache.contains_key(&key) {
            state.clock = state.clock.saturating_add(1);
            let clock = state.clock;
            let entry = state.cache.get_mut(&key).expect("cache entry exists");
            entry.last_used = clock;
            SearchAcquire::Cache(entry.value.clone())
        } else {
            // A new query supersedes older query work. Pages and request kinds
            // of the same query remain independent and are allowed to finish.
            cancel_obsolete_searches(&state, &key.query);
            let reusable_flight = state
                .in_flight
                .get(&key)
                .cloned()
                .filter(|flight| !flight.cancelled.load(Ordering::SeqCst));
            if let Some(flight) = reusable_flight {
                flight.consumers.fetch_add(1, Ordering::SeqCst);
                SearchAcquire::Flight {
                    flight,
                    leader: false,
                }
            } else {
                state.in_flight.remove(&key);
                let flight = Arc::new(SearchFlight {
                    result: Mutex::new(None),
                    ready: Condvar::new(),
                    consumers: AtomicUsize::new(1),
                    cancelled: AtomicBool::new(false),
                });
                state.in_flight.insert(key.clone(), flight.clone());
                SearchAcquire::Flight {
                    flight,
                    leader: true,
                }
            }
        }
    };

    let (flight, leader) = match acquired {
        SearchAcquire::Cache(value) => return Ok(value),
        SearchAcquire::Flight { flight, leader } => (flight, leader),
    };
    let _consumer = SearchConsumer {
        flight: flight.clone(),
    };
    if !leader {
        return wait_for_search(&flight);
    }
    let result =
        search_media_internal_with_timeout_cancelable(&query, limit, offset, &app, timeout, || {
            flight.cancelled.load(Ordering::SeqCst)
        });
    if let Ok(value) = &result {
        if let Ok(mut state) = SEARCH_STATE
            .get_or_init(|| Mutex::new(SearchState::default()))
            .lock()
        {
            state.clock = state.clock.saturating_add(1);
            let clock = state.clock;
            state.cache.insert(
                key.clone(),
                SearchCacheEntry {
                    value: value.clone(),
                    expires_at: Instant::now() + SEARCH_CACHE_TTL,
                    last_used: clock,
                },
            );
            search_cache_prune(&mut state);
        }
    }
    if let Ok(mut shared) = flight.result.lock() {
        *shared = Some(result.clone());
        flight.ready.notify_all();
    }
    if let Ok(mut state) = SEARCH_STATE
        .get_or_init(|| Mutex::new(SearchState::default()))
        .lock()
    {
        if state
            .in_flight
            .get(&key)
            .is_some_and(|current| Arc::ptr_eq(current, &flight))
        {
            state.in_flight.remove(&key);
        }
    }
    result
}

fn wait_for_search(flight: &Arc<SearchFlight>) -> Result<Vec<MediaSearchResult>, String> {
    let mut shared = flight
        .result
        .lock()
        .map_err(|_| "No se pudo esperar la búsqueda compartida".to_string())?;
    while shared.is_none() {
        shared = flight
            .ready
            .wait(shared)
            .map_err(|_| "No se pudo esperar la búsqueda compartida".to_string())?;
    }
    shared
        .as_ref()
        .cloned()
        .unwrap_or_else(|| Err("La búsqueda compartida no devolvió resultados".into()))
}

fn cancel_all_searches() {
    if let Some(state) = SEARCH_STATE.get() {
        if let Ok(state) = state.lock() {
            for flight in state.in_flight.values() {
                flight.cancelled.store(true, Ordering::SeqCst);
                flight.ready.notify_all();
            }
        }
    }
}

fn cancel_obsolete_searches(state: &SearchState, current_query: &str) {
    for (active_key, flight) in &state.in_flight {
        if active_key.query != current_query {
            flight.cancelled.store(true, Ordering::SeqCst);
            flight.ready.notify_all();
        }
    }
}

fn search_cache_prune(state: &mut SearchState) {
    let now = Instant::now();
    state.cache.retain(|_, entry| entry.expires_at > now);
    while state.cache.len() > SEARCH_CACHE_LIMIT {
        let oldest = state
            .cache
            .iter()
            .min_by_key(|(_, entry)| entry.last_used)
            .map(|(key, _)| key.clone());
        let Some(oldest) = oldest else { break };
        state.cache.remove(&oldest);
    }
}

fn normalize_search_key(query: &str) -> String {
    query
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(query: &str, offset: usize, limit: usize) -> SearchKey {
        SearchKey {
            query: normalize_search_key(query),
            offset,
            limit,
            provider: SEARCH_PROVIDER.into(),
            session_fingerprint: SEARCH_SESSION_FINGERPRINT.into(),
            contract_version: SEARCH_CONTRACT_VERSION.into(),
            kind: SearchKind::Suggestions,
        }
    }

    fn result(title: &str) -> Vec<MediaSearchResult> {
        vec![MediaSearchResult {
            source_id: title.into(),
            source_url: format!("https://example.test/{title}"),
            title: title.into(),
            creator: String::new(),
            duration_label: String::new(),
            duration_seconds: None,
            thumbnail: String::new(),
            extractor: "youtube".into(),
            similarity: 0.0,
            match_reasons: Vec::new(),
        }]
    }

    #[test]
    fn search_key_isolates_queries_pages_and_contract_context() {
        assert_ne!(key("anime", 0, 10), key("other", 0, 10));
        assert_ne!(key("anime", 0, 10), key("anime", 10, 10));
        assert_ne!(key("anime", 0, 10), key("anime", 0, 20));
        let mut authenticated = key("anime", 0, 10);
        authenticated.session_fingerprint = "authenticated:opaque-fingerprint".into();
        assert_ne!(key("anime", 0, 10), authenticated);
        let mut title = key("anime", 0, 10);
        title.kind = SearchKind::Title;
        assert_ne!(key("anime", 0, 10), title);
    }

    #[test]
    fn cache_hit_and_expiration_are_distinct() {
        let mut state = SearchState::default();
        let first = key("anime", 0, 10);
        state.clock = 1;
        state.cache.insert(
            first.clone(),
            SearchCacheEntry {
                value: result("A"),
                expires_at: Instant::now() - Duration::from_secs(1),
                last_used: state.clock,
            },
        );
        search_cache_prune(&mut state);
        assert!(!state.cache.contains_key(&first));
    }

    #[test]
    fn errors_are_never_inserted_as_success_cache_entries() {
        let mut state = SearchState::default();
        let flight = Arc::new(SearchFlight {
            result: Mutex::new(Some(Err("provider_failed".into()))),
            ready: Condvar::new(),
            consumers: AtomicUsize::new(0),
            cancelled: AtomicBool::new(false),
        });
        state.in_flight.insert(key("anime", 0, 10), flight);
        assert!(state.cache.is_empty());
    }

    #[test]
    fn equivalent_consumers_share_one_flight_and_distinct_queries_do_not() {
        let mut state = SearchState::default();
        let same = key("anime", 0, 10);
        let different = key("lofi music", 0, 10);
        let flight = Arc::new(SearchFlight {
            result: Mutex::new(None),
            ready: Condvar::new(),
            consumers: AtomicUsize::new(1),
            cancelled: AtomicBool::new(false),
        });
        state.in_flight.insert(same.clone(), flight.clone());
        let joined = state.in_flight.get(&same).cloned().expect("flight");
        joined.consumers.fetch_add(1, Ordering::SeqCst);
        assert!(Arc::ptr_eq(&flight, &joined));
        assert!(!state.in_flight.contains_key(&different));
        assert_eq!(joined.consumers.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn cancelled_flight_is_not_confused_with_a_cache_hit() {
        let flight = Arc::new(SearchFlight {
            result: Mutex::new(None),
            ready: Condvar::new(),
            consumers: AtomicUsize::new(1),
            cancelled: AtomicBool::new(false),
        });
        flight.cancelled.store(true, Ordering::SeqCst);
        assert!(flight.cancelled.load(Ordering::SeqCst));
    }

    #[test]
    fn dropping_one_equivalent_consumer_keeps_the_flight_alive() {
        let flight = Arc::new(SearchFlight {
            result: Mutex::new(None),
            ready: Condvar::new(),
            consumers: AtomicUsize::new(2),
            cancelled: AtomicBool::new(false),
        });
        let first = SearchConsumer {
            flight: flight.clone(),
        };
        let second = SearchConsumer {
            flight: flight.clone(),
        };
        drop(first);
        assert!(!flight.cancelled.load(Ordering::SeqCst));
        drop(second);
        assert!(flight.cancelled.load(Ordering::SeqCst));
    }

    #[test]
    fn a_new_query_cancels_old_work_but_keeps_other_pages_isolated() {
        let mut state = SearchState::default();
        let old = key("anime", 0, 10);
        let old_page = key("anime", 10, 10);
        let next = key("lofi music", 0, 10);
        let old_flight = Arc::new(SearchFlight {
            result: Mutex::new(None),
            ready: Condvar::new(),
            consumers: AtomicUsize::new(1),
            cancelled: AtomicBool::new(false),
        });
        let page_flight = Arc::new(SearchFlight {
            result: Mutex::new(None),
            ready: Condvar::new(),
            consumers: AtomicUsize::new(1),
            cancelled: AtomicBool::new(false),
        });
        state.in_flight.insert(old, old_flight.clone());
        state.in_flight.insert(old_page, page_flight.clone());
        cancel_obsolete_searches(&state, &next.query);
        assert!(old_flight.cancelled.load(Ordering::SeqCst));
        assert!(page_flight.cancelled.load(Ordering::SeqCst));
        // The cancellation boundary is the normalized query, so a page of
        // the same query is not cancelled by another page request itself.
        let same_query_page = key("anime", 15, 10);
        let same_page_flight = Arc::new(SearchFlight {
            result: Mutex::new(None),
            ready: Condvar::new(),
            consumers: AtomicUsize::new(1),
            cancelled: AtomicBool::new(false),
        });
        state.in_flight.clear();
        state
            .in_flight
            .insert(key("anime", 0, 10), same_page_flight.clone());
        cancel_obsolete_searches(&state, &same_query_page.query);
        assert!(!same_page_flight.cancelled.load(Ordering::SeqCst));
    }
}
