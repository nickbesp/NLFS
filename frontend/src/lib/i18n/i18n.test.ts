import assert from "node:assert/strict";
import { test } from "node:test";

import { en } from "./en.ts";
import { es } from "./es.ts";
import { format, translate } from "./index.ts";
import { ru } from "./ru.ts";

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

for (const [name, dict] of [["es", es], ["ru", ru]] as const) {
  test(`${name} has exactly the English keys`, () => {
    assert.deepEqual(Object.keys(dict).sort(), Object.keys(en).sort());
  });

  test(`${name} uses the same placeholders as English for every key`, () => {
    for (const key of Object.keys(en) as (keyof typeof en)[]) {
      assert.deepEqual(placeholders(dict[key]), placeholders(en[key]), key);
    }
  });
}

test("no dictionary has an empty string", () => {
  for (const dict of [en, es, ru]) {
    for (const [key, value] of Object.entries(dict)) assert.ok(value.trim().length > 0, key);
  }
});

test("format fills placeholders", () => {
  assert.equal(format("Hi {name}", { name: "Nikita" }), "Hi Nikita");
});

test("format leaves unknown placeholders untouched", () => {
  assert.equal(format("{a} and {b}", { a: 1 }), "1 and {b}");
});

test("translate picks the requested language", () => {
  assert.equal(translate("es", "nav.settings"), es["nav.settings"]);
  assert.equal(translate("en", "nav.settings"), "Settings");
});
