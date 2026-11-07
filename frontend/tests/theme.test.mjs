import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { getTheme, resolveTheme, setTheme, subscribeTheme, THEME_BOOTSTRAP_SCRIPT, THEME_STORAGE_KEY } from "../lib/theme.ts";

test("an explicit theme wins over system preference", () => {
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("dark", false), "dark");
  assert.equal(resolveTheme(null, true), "dark");
  assert.equal(resolveTheme("invalid", false), "light");
});

test("failed preference writes cannot revert a session choice, and listeners clean up", () => {
  const keys = ["document", "window", "localStorage"];
  const previous = keys.map(key => Object.getOwnPropertyDescriptor(globalThis, key));
  const media = Object.assign(new EventTarget(), { matches: false });
  const browserWindow = Object.assign(new EventTarget(), { matchMedia: () => media });
  const document = { documentElement: { dataset: { theme: "light" } } };
  Object.defineProperty(globalThis, "document", { configurable: true, value: document });
  Object.defineProperty(globalThis, "window", { configurable: true, value: browserWindow });
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: { getItem: () => "light", setItem: () => { throw new Error("full"); } } });
  let updates = 0;
  const unsubscribe = subscribeTheme(() => updates++);
  try {
    setTheme("dark");
    media.matches = true;
    media.dispatchEvent(new Event("change"));
    assert.equal(getTheme(), "dark");
    assert.equal(updates, 2);
    const storageEvent = new Event("storage");
    Object.defineProperty(storageEvent, "key", { value: THEME_STORAGE_KEY });
    browserWindow.dispatchEvent(storageEvent);
    assert.equal(getTheme(), "light");
    const count = updates;
    unsubscribe();
    media.dispatchEvent(new Event("change"));
    assert.equal(updates, count);
  } finally {
    unsubscribe();
    keys.forEach((key, index) => { if (previous[index]) Object.defineProperty(globalThis, key, previous[index]); else delete globalThis[key]; });
  }
});

test("bootstrap applies saved theme or system before hydration, including blocked storage", () => {
  for (const [saved, systemDark, blocked, expected] of [["dark", false, false, "dark"], ["light", true, false, "light"], [null, true, false, "dark"], ["invalid", false, false, "light"], [null, true, true, "dark"]]) {
    const document = { documentElement: { dataset: {} } };
    vm.runInNewContext(THEME_BOOTSTRAP_SCRIPT, {
      document,
      window: { matchMedia: () => ({ matches: systemDark }) },
      localStorage: { getItem: key => { assert.equal(key, THEME_STORAGE_KEY); if (blocked) throw new Error("blocked"); return saved; } },
    });
    assert.equal(document.documentElement.dataset.theme, expected);
  }
});
