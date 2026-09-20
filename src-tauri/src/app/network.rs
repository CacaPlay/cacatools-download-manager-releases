use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, ToSocketAddrs};

use url::{Host, Url};

pub(crate) fn ipv4_is_non_public(address: Ipv4Addr) -> bool {
    let octets = address.octets();
    address.is_private()
        || address.is_loopback()
        || address.is_link_local()
        || address.is_broadcast()
        || address.is_documentation()
        || address.is_unspecified()
        || address.is_multicast()
        || octets[0] == 0
        || (octets[0] == 100 && (64..=127).contains(&octets[1]))
        || (octets[0] == 198 && matches!(octets[1], 18 | 19))
}

pub(crate) fn ipv6_is_non_public(address: Ipv6Addr) -> bool {
    let first = address.segments()[0];
    address.is_loopback()
        || address.is_unspecified()
        || address.is_multicast()
        || first & 0xfe00 == 0xfc00
        || first & 0xffc0 == 0xfe80
        || address.to_ipv4().is_some_and(ipv4_is_non_public)
}

pub(crate) fn ip_is_non_public(address: IpAddr) -> bool {
    match address {
        IpAddr::V4(address) => ipv4_is_non_public(address),
        IpAddr::V6(address) => ipv6_is_non_public(address),
    }
}

pub(crate) fn host_is_public(host: &str) -> bool {
    // `Url::host_str()` may preserve square brackets around IPv6 literals.
    // Normalize them before parsing so loopback, link-local and unique-local
    // IPv6 targets cannot bypass the SSRF guard.
    let host = host
        .trim()
        .trim_start_matches('[')
        .trim_end_matches(']')
        .trim_end_matches('.')
        .to_ascii_lowercase();
    if host.is_empty()
        || host == "localhost"
        || host.ends_with(".localhost")
        || host.ends_with(".local")
        || host.ends_with(".lan")
        || host.ends_with(".internal")
    {
        return false;
    }
    host.parse::<IpAddr>()
        .map(|address| !ip_is_non_public(address))
        .unwrap_or(true)
}

pub(crate) fn url_has_public_http_target(parsed: &Url) -> bool {
    if !matches!(parsed.scheme(), "http" | "https")
        || !parsed.username().is_empty()
        || parsed.password().is_some()
    {
        return false;
    }
    if progress_acceptance_url_allowed(parsed) {
        return true;
    }
    match parsed.host() {
        Some(Host::Domain(host)) => host_is_public(host),
        Some(Host::Ipv4(address)) => !ipv4_is_non_public(address),
        Some(Host::Ipv6(address)) => !ipv6_is_non_public(address),
        None => false,
    }
}

fn progress_acceptance_url_allowed(parsed: &Url) -> bool {
    if cfg!(debug_assertions)
        && std::env::var("CACATOOLS_MEDIA_E2E_ACCEPTANCE")
            .map(|value| value.trim() == "1")
            .unwrap_or(false)
    {
        if let Ok(urls) = std::env::var("CACATOOLS_MEDIA_E2E_URLS") {
            if urls
                .split('|')
                .filter_map(|value| Url::parse(value.trim()).ok())
                .any(|fixture| {
                    parsed.origin() == fixture.origin()
                        && parsed.path() == fixture.path()
                        && parsed.query() == fixture.query()
                })
            {
                return true;
            }
        }
    }
    if !cfg!(debug_assertions)
        || std::env::var("CACATOOLS_PROGRESS_ACCEPTANCE")
            .map(|value| value.trim() != "1")
            .unwrap_or(true)
    {
        return false;
    }
    let Ok(fixture) = std::env::var("CACATOOLS_PROGRESS_ACCEPTANCE_URL") else {
        return false;
    };
    let Ok(fixture) = Url::parse(fixture.trim()) else {
        return false;
    };
    parsed.origin() == fixture.origin()
        && parsed.path() == fixture.path()
        && parsed.query() == fixture.query()
}

pub(crate) fn parse_public_http_url(value: &str, invalid_message: &str) -> Result<Url, String> {
    let mut parsed = Url::parse(value.trim()).map_err(|_| invalid_message.to_string())?;
    if !matches!(parsed.scheme(), "http" | "https") {
        return Err("Solo se permiten enlaces HTTP o HTTPS".into());
    }
    if !parsed.username().is_empty() || parsed.password().is_some() {
        return Err("El enlace no puede incluir credenciales".into());
    }
    if !url_has_public_http_target(&parsed) && !progress_acceptance_url_allowed(&parsed) {
        return Err("El enlace apunta a una dirección local o privada no permitida".into());
    }
    parsed.set_fragment(None);
    Ok(parsed)
}

pub(crate) fn ensure_public_network_resolution(parsed: &Url) -> Result<(), String> {
    if progress_acceptance_url_allowed(parsed) {
        return Ok(());
    }
    let host = match parsed.host() {
        Some(Host::Ipv4(address)) => {
            return if ipv4_is_non_public(address) {
                Err("El host resuelve a una dirección local o privada no permitida".into())
            } else {
                Ok(())
            };
        }
        Some(Host::Ipv6(address)) => {
            return if ipv6_is_non_public(address) {
                Err("El host resuelve a una dirección local o privada no permitida".into())
            } else {
                Ok(())
            };
        }
        Some(Host::Domain(host)) => host,
        None => return Err("El enlace no contiene un host válido".into()),
    };
    let port = parsed
        .port_or_known_default()
        .ok_or_else(|| "No se pudo determinar el puerto del enlace".to_string())?;
    let addresses = (host, port)
        .to_socket_addrs()
        .map_err(|error| format!("No se pudo resolver el host: {error}"))?;
    let mut resolved = false;
    for socket in addresses.take(32) {
        resolved = true;
        if ip_is_non_public(socket.ip()) {
            return Err("El host resuelve a una dirección local o privada no permitida".into());
        }
    }
    if !resolved {
        return Err("El host no devolvió ninguna dirección de red".into());
    }
    Ok(())
}

pub(crate) fn url_has_public_network_target(parsed: &Url) -> bool {
    url_has_public_http_target(parsed) && ensure_public_network_resolution(parsed).is_ok()
}
