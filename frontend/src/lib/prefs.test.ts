import assert from "node:assert/strict";
import { test } from "node:test";

import { parseLang, parseTheme } from "./prefs.ts";

test("parseTheme defaults to light when the cookie is missing", () => {
  assert.equal(parseTheme(undefined), "light");
});

test("parseTheme accepts dark", () => {
  assert.equal(parseTheme("dark"), "dark");
});

test("parseTheme falls back to light for an unknown value", () => {
  assert.equal(parseTheme("blue"), "light");
});

test("parseLang defaults to English when the cookie is missing", () => {
  assert.equal(parseLang(undefined), "en");
});

test("parseLang accepts Russian", () => {
  assert.equal(parseLang("ru"), "ru");
});

test("parseLang falls back to English for an unsupported language", () => {
  assert.equal(parseLang("de"), "en");
});
