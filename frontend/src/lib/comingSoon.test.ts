import assert from "node:assert/strict";
import { test } from "node:test";

import { COMING_SOON, comingSoonKeys } from "./comingSoon.ts";
import { en } from "./i18n/en.ts";

test("there are exactly ten unique coming-soon features", () => {
  const ids = COMING_SOON.map((f) => f.id);
  assert.equal(ids.length, 10);
  assert.equal(new Set(ids).size, 10);
});

test("every coming-soon feature has a name and a needs-note in the dictionary", () => {
  for (const { id } of COMING_SOON) {
    const keys = comingSoonKeys(id);
    assert.ok(keys.name in en, keys.name);
    assert.ok(keys.needs in en, keys.needs);
  }
});
