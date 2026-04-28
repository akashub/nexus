import { useEffect, useRef, useState } from "react";

const API_URL = "http://127.0.0.1:7777";
const POLL_INTERVAL = 2000;

export type BackendStatus = "connecting" | "ready" | "error";

export function useBackend() {
  const [status, setStatus] = useState<BackendStatus>("connecting");
  const childRef = useRef<{ kill: () => Promise<void> } | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function startBackend() {
      try {
        const { Command } = await import("@tauri-apps/plugin-shell");
        const cmd = Command.create("nexus-serve", ["serve", "--port", "7777"]);
        cmd.on("error", () => {});
        const child = await cmd.spawn();
        childRef.current = child;
      } catch {
        // Shell plugin not available (running in browser dev mode) — assume manual start
      }
    }

    async function pollHealth() {
      while (!cancelled) {
        try {
          const res = await fetch(`${API_URL}/api/stats`);
          if (res.ok) {
            setStatus("ready");
            return;
          }
        } catch {
          // Server not up yet
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL));
      }
    }

    startBackend();
    pollHealth();

    return () => {
      cancelled = true;
      childRef.current?.kill().catch(() => {});
    };
  }, []);

  return status;
}
