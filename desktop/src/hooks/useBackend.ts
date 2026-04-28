import { useEffect, useState } from "react";

const API_URL = "http://127.0.0.1:7777";
const POLL_INTERVAL = 2000;
const MAX_POLLS = 15;

export type BackendStatus = "connecting" | "ready" | "error";

export function useBackend() {
  const [status, setStatus] = useState<BackendStatus>("connecting");

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    async function poll() {
      while (!cancelled && attempts < MAX_POLLS) {
        try {
          const res = await fetch(`${API_URL}/api/stats`);
          if (res.ok) {
            setStatus("ready");
            return;
          }
        } catch {
          // Backend not up yet — Rust side is spawning it
        }
        attempts++;
        await new Promise((r) => setTimeout(r, POLL_INTERVAL));
      }
      if (!cancelled) setStatus("error");
    }

    poll();
    return () => { cancelled = true; };
  }, []);

  return status;
}
