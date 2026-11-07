export type Theme = "light" | "dark";
export const THEME_STORAGE_KEY = "privcon-theme";
const THEME_EVENT = "privcon-theme-change";
let sessionPreference: Theme | undefined;

export function resolveTheme(preference: unknown, systemDark: boolean): Theme {
  return preference === "light" || preference === "dark" ? preference : systemDark ? "dark" : "light";
}

function readPreference(): Theme | undefined {
  if (sessionPreference) return sessionPreference;
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    if (value === "light" || value === "dark") return value;
  } catch {
    // A disabled preference store must not prevent local theme switching.
  }
  return sessionPreference;
}

export function getTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function setTheme(theme: Theme): void {
  sessionPreference = theme;
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // The selected theme still applies for this session when storage is blocked.
  }
  window.dispatchEvent(new Event(THEME_EVENT));
}

export function subscribeTheme(onChange: () => void): () => void {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const synchronize = () => {
    document.documentElement.dataset.theme = resolveTheme(readPreference(), media.matches);
    onChange();
  };
  const onStorage = (event: StorageEvent) => {
    if (event.key !== THEME_STORAGE_KEY && event.key !== null) return;
    sessionPreference = undefined;
    synchronize();
  };
  window.addEventListener(THEME_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  media.addEventListener("change", synchronize);
  return () => {
    window.removeEventListener(THEME_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
    media.removeEventListener("change", synchronize);
  };
}

// Static, trusted initialization runs before paint; no document data is read.
export const THEME_BOOTSTRAP_SCRIPT = `(()=>{let preference;try{preference=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)})}catch{}document.documentElement.dataset.theme=preference==="light"||preference==="dark"?preference:window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"})()`;
