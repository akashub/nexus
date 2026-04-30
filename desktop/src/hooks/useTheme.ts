import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "light" | "system";
type Resolved = "dark" | "light";

const KEY = "nexus-theme";
const ThemeCtx = createContext<{ theme: Theme; resolved: Resolved; cycle: () => void; set: (t: Theme) => void }>({
  theme: "dark", resolved: "dark", cycle: () => {}, set: () => {},
});

function getSystem(): Resolved {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolve(t: Theme): Resolved { return t === "system" ? getSystem() : t; }

export function useThemeProvider() {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem(KEY) as Theme) || "dark");
  const [resolved, setResolved] = useState<Resolved>(() => resolve(theme));

  useEffect(() => {
    const r = resolve(theme);
    setResolved(r);
    document.documentElement.setAttribute("data-theme", r);
    localStorage.setItem(KEY, theme);
  }, [theme]);

  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => { const r = getSystem(); setResolved(r); document.documentElement.setAttribute("data-theme", r); };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const cycle = () => setTheme((t) => t === "dark" ? "light" : t === "light" ? "system" : "dark");
  return { theme, resolved, cycle, set: setTheme };
}

export const ThemeProvider = ThemeCtx.Provider;
export function useTheme() { return useContext(ThemeCtx); }
