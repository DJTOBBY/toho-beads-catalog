"use client";

import { useCallback, useSyncExternalStore } from "react";

type Mode = "system" | "light" | "dark";

const KEY = "toho-theme";
const NEXT: Record<Mode, Mode> = { system: "light", light: "dark", dark: "system" };
const LABEL: Record<Mode, string> = { system: "自動", light: "ライト", dark: "ダーク" };

/**
 * The stored theme is browser state, not React state, so it is read through
 * useSyncExternalStore: that keeps the server render ("system") and the client
 * render consistent without an effect that immediately sets state.
 */
const listeners = new Set<() => void>();

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

function getSnapshot(): Mode {
  return (window.localStorage.getItem(KEY) as Mode | null) ?? "system";
}

function getServerSnapshot(): Mode {
  return "system";
}

export function ThemeToggle() {
  const mode = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const cycle = useCallback(() => {
    const next = NEXT[getSnapshot()];
    window.localStorage.setItem(KEY, next);
    const root = document.documentElement;
    if (next === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", next);
    for (const listener of listeners) listener();
  }, []);

  return (
    <button
      type="button"
      onClick={cycle}
      className="ml-1 shrink-0 whitespace-nowrap rounded-full px-3 py-1.5 text-[12px] transition-colors"
      style={{ border: "1px solid var(--line)", color: "var(--fg-2)" }}
      aria-label={`表示テーマ: ${LABEL[mode]}（クリックで切り替え）`}
    >
      {LABEL[mode]}
    </button>
  );
}
