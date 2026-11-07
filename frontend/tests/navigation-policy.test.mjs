import assert from "node:assert/strict";
import test from "node:test";
import { needsNavigationDecision } from "../lib/navigation-policy.ts";

test("empty and completed workspaces can navigate directly", () => {
  assert.equal(needsNavigationDecision("idle", "http://localhost:3000/rotate-pdf", "/"), false);
});

test("local drafts and processing require a decision before changing tool", () => {
  for (const state of ["draft", "processing"]) {
    assert.equal(needsNavigationDecision(state, "http://localhost:3000/rotate-pdf", "/pdf-to-jpg"), true);
    assert.equal(needsNavigationDecision(state, "http://localhost:3000/rotate-pdf", "/"), true);
  }
});

test("same tool anchors, external destinations and another tab do not discard the current workspace", () => {
  const source = "http://localhost:3000/rotate-pdf";
  assert.equal(needsNavigationDecision("draft", source, "#main-content"), false);
  assert.equal(needsNavigationDecision("draft", source, source), false);
  assert.equal(needsNavigationDecision("draft", source, "/pdf-to-jpg", true), false);
  assert.equal(needsNavigationDecision("draft", source, "https://example.com/"), false);
  assert.equal(needsNavigationDecision("draft", source, "/rotate-pdf?different=true"), true);
});
