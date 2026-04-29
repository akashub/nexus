use std::fs;
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

impl Drop for BackendProcess {
    fn drop(&mut self) {
        if let Some(mut child) = self.0.lock().unwrap().take() {
            let _ = child.kill();
        }
    }
}

fn read_backend_dir() -> Option<String> {
    let home = std::env::var("HOME").ok()?;
    let path = format!("{home}/.nexus/backend_dir");
    fs::read_to_string(path).ok().map(|s| s.trim().to_string())
}

fn find_uv() -> String {
    let home = std::env::var("HOME").unwrap_or_default();
    let candidates = [
        format!("{home}/.local/bin/uv"),
        format!("{home}/.cargo/bin/uv"),
        "/opt/homebrew/bin/uv".to_string(),
        "/usr/local/bin/uv".to_string(),
        "uv".to_string(),
    ];
    for c in &candidates {
        if std::path::Path::new(c).exists() {
            return c.clone();
        }
    }
    candidates.last().unwrap().clone()
}

fn spawn_backend(dir: Option<String>) -> Option<Child> {
    let uv = find_uv();
    match dir {
        Some(d) => Command::new(&uv)
            .args(["run", "--project", &d, "nexus", "serve", "--port", "7777"])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .ok(),
        None => Command::new(&uv)
            .args(["run", "nexus", "serve", "--port", "7777"])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .ok(),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let child = spawn_backend(read_backend_dir());
            app.manage(BackendProcess(Mutex::new(child)));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
