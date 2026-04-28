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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let cmd = if let Some(dir) = read_backend_dir() {
                format!("uv run --project '{dir}' nexus serve --port 7777")
            } else {
                "nexus serve --port 7777".to_string()
            };
            let child = Command::new("zsh")
                .args(["-lc", &cmd])
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .spawn()
                .ok();
            app.manage(BackendProcess(Mutex::new(child)));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
