//! Small, on-demand native clipboard reader for the unified link intake.
//!
//! This command deliberately does not persist clipboard contents and avoids
//! WebView2's navigator.clipboard permission prompt.  It is only called by
//! the focus-driven watcher after the frontend has decided that a check is
//! appropriate.

#[tauri::command]
pub(crate) fn read_clipboard_text() -> Result<String, String> {
    #[cfg(windows)]
    {
        read_windows_unicode_clipboard()
    }

    #[cfg(not(windows))]
    {
        Ok(String::new())
    }
}

#[cfg(windows)]
fn read_windows_unicode_clipboard() -> Result<String, String> {
    use std::ffi::c_void;
    use std::ptr::null_mut;
    use std::slice;

    type HGlobal = *mut c_void;
    type HWnd = *mut c_void;

    const CF_UNICODETEXT: u32 = 13;

    #[link(name = "user32")]
    unsafe extern "system" {
        fn OpenClipboard(owner: HWnd) -> i32;
        fn CloseClipboard() -> i32;
        fn GetClipboardData(format: u32) -> HGlobal;
    }

    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GlobalLock(handle: HGlobal) -> *mut c_void;
        fn GlobalUnlock(handle: HGlobal) -> i32;
        fn GlobalSize(handle: HGlobal) -> usize;
    }

    // Clipboard ownership is process-global. Browsers and WebView2 can hold
    // it briefly while a copy operation completes, so use a short bounded
    // retry instead of converting that normal race into a silent miss.
    let mut opened = false;
    for attempt in 0..8 {
        if unsafe { OpenClipboard(null_mut()) } != 0 {
            opened = true;
            break;
        }
        if attempt < 7 {
            std::thread::sleep(std::time::Duration::from_millis(15));
        }
    }
    if !opened {
        return Ok(String::new());
    }

    let handle = unsafe { GetClipboardData(CF_UNICODETEXT) };
    if handle.is_null() {
        unsafe { CloseClipboard() };
        return Ok(String::new());
    }

    let pointer = unsafe { GlobalLock(handle) } as *const u16;
    if pointer.is_null() {
        unsafe { CloseClipboard() };
        return Ok(String::new());
    }

    let max_units = unsafe { GlobalSize(handle) } / std::mem::size_of::<u16>();
    let mut length = 0usize;
    if max_units > 0 {
        let data = unsafe { slice::from_raw_parts(pointer, max_units) };
        while length < data.len() && data[length] != 0 {
            length += 1;
        }
    }
    let text = if length == 0 {
        String::new()
    } else {
        let data = unsafe { slice::from_raw_parts(pointer, length) };
        String::from_utf16_lossy(data)
    };

    unsafe {
        GlobalUnlock(handle);
        CloseClipboard();
    }
    Ok(text)
}
