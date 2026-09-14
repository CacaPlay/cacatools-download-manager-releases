use super::*;

pub(crate) const SPOTIFY_CLIENT_ID: &str = "f8ec131878d3446eabe040ee976ddc1f";
pub(crate) const SPOTIFY_REDIRECT_URI: &str = "http://127.0.0.1:43821/callback";
const SPOTIFY_TOKEN_SETTING: &str = "spotify_pkce_token_v1";
const SPOTIFY_AUTH_TIMEOUT: Duration = Duration::from_secs(180);

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct SpotifyAuthStatus {
    pub(crate) connected: bool,
}

#[derive(Clone, Serialize, Deserialize)]
struct StoredSpotifyToken {
    access_token: String,
    refresh_token: String,
    expires_at: i64,
}

#[cfg(windows)]
#[repr(C)]
struct DataBlob {
    cb_data: u32,
    pb_data: *mut u8,
}

#[cfg(windows)]
#[link(name = "crypt32")]
unsafe extern "system" {
    fn CryptProtectData(
        data_in: *const DataBlob,
        description: *const u16,
        entropy: *const DataBlob,
        reserved: *mut std::ffi::c_void,
        prompt: *const std::ffi::c_void,
        flags: u32,
        data_out: *mut DataBlob,
    ) -> i32;
    fn CryptUnprotectData(
        data_in: *const DataBlob,
        description: *mut *mut u16,
        entropy: *const DataBlob,
        reserved: *mut std::ffi::c_void,
        prompt: *const std::ffi::c_void,
        flags: u32,
        data_out: *mut DataBlob,
    ) -> i32;
}

#[cfg(windows)]
#[link(name = "kernel32")]
unsafe extern "system" {
    fn LocalFree(memory: *mut std::ffi::c_void) -> *mut std::ffi::c_void;
}

#[cfg(windows)]
#[link(name = "bcrypt")]
unsafe extern "system" {
    fn BCryptGenRandom(
        algorithm: *mut std::ffi::c_void,
        buffer: *mut u8,
        length: u32,
        flags: u32,
    ) -> i32;
}

fn random_bytes(length: usize) -> Result<Vec<u8>, String> {
    let mut bytes = vec![0_u8; length];
    #[cfg(windows)]
    {
        // BCryptGenRandom with the system-preferred provider is the Windows
        // CSPRNG and does not depend on a user-controlled process or clock.
        let status = unsafe {
            BCryptGenRandom(
                std::ptr::null_mut(),
                bytes.as_mut_ptr(),
                bytes.len() as u32,
                0x00000002,
            )
        };
        if status != 0 {
            return Err(format!(
                "No se pudo generar aleatoriedad segura (BCrypt {status})"
            ));
        }
    }
    #[cfg(not(windows))]
    {
        use std::io::Read as _;
        let mut source = std::fs::File::open("/dev/urandom")
            .map_err(|error| format!("No se pudo abrir el CSPRNG del sistema: {error}"))?;
        source
            .read_exact(&mut bytes)
            .map_err(|error| format!("No se pudo leer el CSPRNG del sistema: {error}"))?;
    }
    Ok(bytes)
}

fn base64_url(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    let mut result = String::with_capacity((bytes.len() * 4).div_ceil(3));
    let mut index = 0;
    while index < bytes.len() {
        let first = bytes[index] as u32;
        let second = bytes.get(index + 1).copied().unwrap_or(0) as u32;
        let third = bytes.get(index + 2).copied().unwrap_or(0) as u32;
        let value = (first << 16) | (second << 8) | third;
        result.push(ALPHABET[((value >> 18) & 63) as usize] as char);
        result.push(ALPHABET[((value >> 12) & 63) as usize] as char);
        if index + 1 < bytes.len() {
            result.push(ALPHABET[((value >> 6) & 63) as usize] as char);
        }
        if index + 2 < bytes.len() {
            result.push(ALPHABET[(value & 63) as usize] as char);
        }
        index += 3;
    }
    result
}

#[cfg(windows)]
fn protect_token(value: &[u8]) -> Result<Vec<u8>, String> {
    let input = DataBlob {
        cb_data: value.len() as u32,
        pb_data: value.as_ptr() as *mut u8,
    };
    let mut output = DataBlob {
        cb_data: 0,
        pb_data: std::ptr::null_mut(),
    };
    let success = unsafe {
        CryptProtectData(
            &input,
            std::ptr::null(),
            std::ptr::null(),
            std::ptr::null_mut(),
            std::ptr::null(),
            1,
            &mut output,
        )
    };
    if success == 0 || output.pb_data.is_null() {
        return Err("Windows no pudo proteger el token de Spotify con DPAPI".into());
    }
    let protected =
        unsafe { std::slice::from_raw_parts(output.pb_data, output.cb_data as usize) }.to_vec();
    unsafe {
        let _ = LocalFree(output.pb_data as *mut std::ffi::c_void);
    }
    Ok(protected)
}

#[cfg(not(windows))]
fn protect_token(_value: &[u8]) -> Result<Vec<u8>, String> {
    Err("El almacenamiento seguro de Spotify requiere Windows DPAPI".into())
}

#[cfg(windows)]
fn unprotect_token(value: &[u8]) -> Result<Vec<u8>, String> {
    let input = DataBlob {
        cb_data: value.len() as u32,
        pb_data: value.as_ptr() as *mut u8,
    };
    let mut output = DataBlob {
        cb_data: 0,
        pb_data: std::ptr::null_mut(),
    };
    let success = unsafe {
        CryptUnprotectData(
            &input,
            std::ptr::null_mut(),
            std::ptr::null(),
            std::ptr::null_mut(),
            std::ptr::null(),
            1,
            &mut output,
        )
    };
    if success == 0 || output.pb_data.is_null() {
        return Err("Windows no pudo descifrar el token de Spotify".into());
    }
    let plain =
        unsafe { std::slice::from_raw_parts(output.pb_data, output.cb_data as usize) }.to_vec();
    unsafe {
        let _ = LocalFree(output.pb_data as *mut std::ffi::c_void);
    }
    Ok(plain)
}

#[cfg(not(windows))]
fn unprotect_token(_value: &[u8]) -> Result<Vec<u8>, String> {
    Err("El almacenamiento seguro de Spotify requiere Windows DPAPI".into())
}

fn hex_encode(value: &[u8]) -> String {
    value.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn hex_decode(value: &str) -> Result<Vec<u8>, String> {
    if !value.len().is_multiple_of(2) {
        return Err("El token protegido de Spotify está dañado".into());
    }
    (0..value.len())
        .step_by(2)
        .map(|index| {
            u8::from_str_radix(&value[index..index + 2], 16)
                .map_err(|_| "El token protegido de Spotify está dañado".to_string())
        })
        .collect()
}

fn read_stored_token(connection: &Connection) -> Result<Option<StoredSpotifyToken>, String> {
    let value: Option<String> = connection
        .query_row(
            "SELECT value FROM settings WHERE key=?1",
            params![SPOTIFY_TOKEN_SETTING],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    let Some(value) = value else { return Ok(None) };
    let encrypted = hex_decode(&value)?;
    let plain = unprotect_token(&encrypted)?;
    serde_json::from_slice(&plain)
        .map(Some)
        .map_err(|error| format!("El token protegido de Spotify no es válido: {error}"))
}

fn write_stored_token(connection: &Connection, token: &StoredSpotifyToken) -> Result<(), String> {
    let plain = serde_json::to_vec(token).map_err(|error| error.to_string())?;
    let encrypted = protect_token(&plain)?;
    connection
        .execute(
            "INSERT INTO settings(key,value,updated_at) VALUES(?1,?2,CURRENT_TIMESTAMP)
             ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",
            params![SPOTIFY_TOKEN_SETTING, hex_encode(&encrypted)],
        )
        .map_err(|error| error.to_string())?;
    Ok(())
}

pub(crate) fn spotify_auth_status(db_path: &Path) -> Result<SpotifyAuthStatus, String> {
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    Ok(SpotifyAuthStatus {
        connected: read_stored_token(&connection)?.is_some(),
    })
}

pub(crate) fn spotify_logout(db_path: &Path) -> Result<(), String> {
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    connection
        .execute(
            "DELETE FROM settings WHERE key=?1",
            params![SPOTIFY_TOKEN_SETTING],
        )
        .map_err(|error| error.to_string())?;
    Ok(())
}

fn callback_response(status: &str, title: &str, detail: &str) -> String {
    let body = format!(
        "<!doctype html><meta charset=utf-8><title>{title}</title><p>{detail}</p><script>window.close()</script>"
    );
    format!(
        "HTTP/1.1 {status}\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )
}

fn exchange_code(
    client: &Client,
    code: &str,
    verifier: &str,
) -> Result<StoredSpotifyToken, String> {
    let response = client
        .post("https://accounts.spotify.com/api/token")
        .form(&[
            ("grant_type", "authorization_code"),
            ("code", code),
            ("redirect_uri", SPOTIFY_REDIRECT_URI),
            ("client_id", SPOTIFY_CLIENT_ID),
            ("code_verifier", verifier),
        ])
        .send()
        .map_err(|error| format!("No se pudo completar el login de Spotify: {error}"))?;
    let status = response.status();
    let payload: Value = response
        .json()
        .map_err(|error| format!("Spotify devolvió una respuesta de login inválida: {error}"))?;
    if !status.is_success() {
        return Err(format!(
            "Spotify rechazó el login (HTTP {}): {}",
            status.as_u16(),
            first_string(&payload, &["error_description", "error"])
        ));
    }
    let access_token = first_string(&payload, &["access_token"]);
    let refresh_token = first_string(&payload, &["refresh_token"]);
    if access_token.is_empty() || refresh_token.is_empty() {
        return Err("Spotify no devolvió los tokens necesarios para PKCE".into());
    }
    let expires_in = json_number_as_u64(payload.get("expires_in")).unwrap_or(3600);
    Ok(StoredSpotifyToken {
        access_token,
        refresh_token,
        expires_at: UNIX_EPOCH
            .elapsed()
            .unwrap_or_default()
            .as_secs()
            .saturating_add(expires_in) as i64,
    })
}

pub(crate) fn spotify_login(app: AppHandle, db_path: &Path) -> Result<SpotifyAuthStatus, String> {
    let listener = std::net::TcpListener::bind((Ipv4Addr::LOCALHOST, 43821))
        .map_err(|error| format!("No se pudo abrir {SPOTIFY_REDIRECT_URI}: {error}"))?;
    listener
        .set_nonblocking(true)
        .map_err(|error| format!("No se pudo preparar el callback de Spotify: {error}"))?;
    let verifier = base64_url(&random_bytes(64)?);
    let challenge = base64_url(Sha256::digest(verifier.as_bytes()).as_slice());
    let state = base64_url(&random_bytes(32)?);
    let mut query = url::form_urlencoded::Serializer::new(String::new());
    query.append_pair("client_id", SPOTIFY_CLIENT_ID);
    query.append_pair("response_type", "code");
    query.append_pair("redirect_uri", SPOTIFY_REDIRECT_URI);
    query.append_pair("code_challenge_method", "S256");
    query.append_pair("code_challenge", &challenge);
    query.append_pair("state", &state);
    query.append_pair(
        "scope",
        "user-read-private playlist-read-private playlist-read-collaborative",
    );
    let authorization_url = format!("https://accounts.spotify.com/authorize?{}", query.finish());
    app.opener()
        .open_url(&authorization_url, None::<&str>)
        .map_err(|error| format!("No se pudo abrir el navegador para Spotify: {error}"))?;

    let started = Instant::now();
    let mut request = None;
    while started.elapsed() < SPOTIFY_AUTH_TIMEOUT {
        match listener.accept() {
            Ok((mut stream, _)) => {
                let mut bytes = Vec::new();
                let mut buffer = [0_u8; 2048];
                loop {
                    let read = stream
                        .read(&mut buffer)
                        .map_err(|error| error.to_string())?;
                    if read == 0 {
                        break;
                    }
                    bytes.extend_from_slice(&buffer[..read]);
                    if bytes.windows(4).any(|window| window == b"\r\n\r\n") || bytes.len() > 16_384
                    {
                        break;
                    }
                }
                let line = String::from_utf8_lossy(&bytes)
                    .lines()
                    .next()
                    .unwrap_or_default()
                    .to_string();
                let target = line.split_whitespace().nth(1).unwrap_or_default();
                let callback = Url::parse(&format!("http://127.0.0.1{target}"))
                    .map_err(|_| "El callback de Spotify no es válido".to_string())?;
                let detail = callback
                    .query_pairs()
                    .find_map(|(key, value)| {
                        (key == "error_description").then(|| value.into_owned())
                    })
                    .unwrap_or_default();
                if callback.path() != "/callback" {
                    let _ = stream.write_all(
                        callback_response(
                            "400 Bad Request",
                            "Callback inválido",
                            "La ruta del callback no coincide.",
                        )
                        .as_bytes(),
                    );
                    return Err("Spotify devolvió una ruta de callback inválida".into());
                }
                let received_state = callback
                    .query_pairs()
                    .find_map(|(key, value)| (key == "state").then(|| value.into_owned()))
                    .unwrap_or_default();
                if received_state != state {
                    let _ = stream.write_all(
                        callback_response(
                            "400 Bad Request",
                            "Estado inválido",
                            "La validación de seguridad falló.",
                        )
                        .as_bytes(),
                    );
                    return Err("Spotify devolvió un state inválido".into());
                }
                if !detail.is_empty() {
                    let _ = stream.write_all(
                        callback_response("400 Bad Request", "Spotify no autorizó la app", &detail)
                            .as_bytes(),
                    );
                    return Err(format!("Spotify no autorizó la app: {detail}"));
                }
                let code = callback
                    .query_pairs()
                    .find_map(|(key, value)| (key == "code").then(|| value.into_owned()))
                    .unwrap_or_default();
                let _ = stream.write_all(
                    callback_response("200 OK", "Spotify conectado", "Puedes volver a CacaTools.")
                        .as_bytes(),
                );
                request = Some(code);
                break;
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(100));
            }
            Err(error) => return Err(format!("Error esperando el callback de Spotify: {error}")),
        }
    }
    let code = request
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "El login de Spotify expiró o no recibió un código".to_string())?;
    let client = Client::builder()
        .timeout(Duration::from_secs(20))
        .user_agent("CacaTools Download Manager/0.25.1")
        .gzip(true)
        .build()
        .map_err(|error| error.to_string())?;
    let token = exchange_code(&client, &code, &verifier)?;
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    write_stored_token(&connection, &token)?;
    Ok(SpotifyAuthStatus { connected: true })
}

pub(crate) fn spotify_access_token(client: &Client, db_path: &Path) -> Result<String, String> {
    let connection = Connection::open(db_path).map_err(|error| error.to_string())?;
    let token =
        read_stored_token(&connection)?.ok_or_else(|| "spotify_not_connected".to_string())?;
    let now = UNIX_EPOCH.elapsed().unwrap_or_default().as_secs() as i64;
    if token.expires_at > now + 60 {
        return Ok(token.access_token);
    }
    let response = client
        .post("https://accounts.spotify.com/api/token")
        .form(&[
            ("grant_type", "refresh_token"),
            ("refresh_token", token.refresh_token.as_str()),
            ("client_id", SPOTIFY_CLIENT_ID),
        ])
        .send()
        .map_err(|error| format!("No se pudo renovar la sesión de Spotify: {error}"))?;
    let status = response.status();
    let payload: Value = response.json().map_err(|error| error.to_string())?;
    if !status.is_success() {
        return Err(format!(
            "La sesión de Spotify expiró (HTTP {})",
            status.as_u16()
        ));
    }
    let access_token = first_string(&payload, &["access_token"]);
    if access_token.is_empty() {
        return Err("Spotify no devolvió un access token renovado".into());
    }
    let expires_in = json_number_as_u64(payload.get("expires_in")).unwrap_or(3600);
    let updated = StoredSpotifyToken {
        access_token: access_token.clone(),
        refresh_token: first_string(&payload, &["refresh_token"]),
        expires_at: now.saturating_add(expires_in as i64),
    };
    let updated = StoredSpotifyToken {
        refresh_token: if updated.refresh_token.is_empty() {
            token.refresh_token
        } else {
            updated.refresh_token
        },
        ..updated
    };
    write_stored_token(&connection, &updated)?;
    Ok(access_token)
}

#[cfg(all(test, windows))]
mod tests {
    use super::*;
    use crate::migrate;
    use std::fs;

    #[test]
    fn protected_session_status_and_logout_are_consistent() {
        let path = std::env::temp_dir().join(format!(
            "cacatools-spotify-auth-test-{}.sqlite",
            std::process::id()
        ));
        let _ = fs::remove_file(&path);
        let connection = Connection::open(&path).expect("test database");
        migrate(&connection).expect("database migration");
        assert!(
            !spotify_auth_status(&path)
                .expect("initial status")
                .connected
        );
        write_stored_token(
            &connection,
            &StoredSpotifyToken {
                access_token: "access-token".into(),
                refresh_token: "refresh-token".into(),
                expires_at: i64::MAX,
            },
        )
        .expect("protected token");
        assert!(
            spotify_auth_status(&path)
                .expect("connected status")
                .connected
        );
        spotify_logout(&path).expect("logout");
        assert!(
            !spotify_auth_status(&path)
                .expect("logged out status")
                .connected
        );
        drop(connection);
        let _ = fs::remove_file(path);
    }
}
