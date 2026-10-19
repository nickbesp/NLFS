# Terra Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle NLFS in the Terra design. This adds a left sidebar, a Settings page (Light/Dark, English/Castellano/Русский, stored in cookies) and a Terra dashboard that shows real data plus labelled "Coming soon" placeholders.

**Architecture:**
- Pure logic lives in small dependency-free modules under `src/lib/`, unit-tested with Node's built-in test runner (`node --test`, native TS type-stripping on Node 24): preferences, i18n, the coming-soon registry and dashboard derivations.
- The root layout reads the `nlfs-theme` and `nlfs-lang` cookies on the server and renders `<html data-theme lang>`, so there's no flash.
- Server Actions write the cookies. Client components get strings from a context provider.

**Tech Stack:** Next.js 16.4 (App Router, Server Components, Server Actions), React 19, plain CSS, `next/font/google` (Literata, Nunito Sans), Material Symbols Outlined (Google Fonts stylesheet), `node:test`.

**Spec:** `docs/superpowers/specs/2026-10-16-terra-redesign-design.md`

## Global Constraints

- Terra light tokens:

  | Token | Value |
  |---|---|
  | `--bg` | `#faf6f0` |
  | `--surface-lowest` | `#ffffff` |
  | `--surface-low` | `#f4f0e8` |
  | `--surface` | `#eae6de` |
  | `--fg` | `#2e3230` |
  | `--muted` | `#4a4e4a` |
  | `--outline` | `#74796e` |
  | `--primary` | `#4a7c59` |
  | `--primary-tint` | `#c8e8d0` |
  | `--tertiary` | `#705c30` |
  | `--tertiary-tint` | `#f8e0a8` |
  | `--error` | `#b83230` |

- Terra dark tokens:

  | Token | Value |
  |---|---|
  | `--bg` | `#141a17` |
  | `--surface-lowest` | `#1c2420` |
  | `--surface-low` | `#18201c` |
  | `--surface` | `#24302a` |
  | `--fg` | `#ece6dc` |
  | `--muted` | `#b9b3a8` |
  | `--outline` | `#8c8a80` |
  | `--primary` | `#8ecf9e` |
  | `--on-primary` | `#10301c` |
  | `--primary-tint` | `#24402e` |
  | `--tertiary` | `#dcc48e` |
  | `--tertiary-tint` | `#3a3220` |
  | `--error` | `#ff8a80` |

- Shadow `0 4px 20px rgba(46,50,48,.06)`. Radii: cards 16px, buttons 12px, pills 999px.
- **No `prefers-color-scheme` anywhere.** The theme comes only from the `nlfs-theme` cookie (default `light`).
- Languages are `en` | `es` | `ru`, default `en`. Cookie `nlfs-lang`. Cookies use `maxAge` 31536000 and `path` "/".
- Learning content (topic titles, theory markdown, cards, quiz prompts) is never translated.
- No backend changes. No fake numbers from the mockup.
- Next.js 16: `cookies()` is async, and `.set` only works in Server Actions.
- No git repo: skip commit steps.

## Review Focus

1. **Stale or tampered cookie** (`nlfs-lang=de`, `nlfs-theme=blue`): falls back to `en` / `light` (Task 1 test).
2. **No topics, or all topics completed:** the dashboard shows the empty state or the "All topics completed" state instead of crashing (Task 4 tests).
3. **No quiz history:** average accuracy is `null`, rendered as "—", not `NaN%` (Task 4 test).
4. **Topic with fewer than 5 cards, or none:** the quiz count is `min(5, n)`. With 0, the quiz module is not a link (Task 4 test).
5. **Backend down while the layout renders:** the sidebar's due-count fetch must not crash the shell. It's caught and the badge hidden, so `error.tsx` still renders inside the sidebar (Task 5, manual check).

---

### Task 1: Test runner + preferences

**Files:**
- Modify: `frontend/package.json` (add `"test": "node --test \"src/**/*.test.ts\""`)
- Modify: `frontend/tsconfig.json` (add `"allowImportingTsExtensions": true`)
- Create: `frontend/src/lib/prefs.ts`, `frontend/src/lib/prefs.test.ts`

**Interfaces:**
- Produces:
  - `THEMES = ["light","dark"] as const`, `type Theme`
  - `LANGS = ["en","es","ru"] as const`, `type Lang`
  - `THEME_COOKIE = "nlfs-theme"`, `LANG_COOKIE = "nlfs-lang"`
  - `parseTheme(v: string | undefined): Theme`, `parseLang(v: string | undefined): Lang`

- [ ] Step 1: Tests:
  - `parseTheme(undefined)==="light"`, `parseTheme("dark")==="dark"`, `parseTheme("blue")==="light"`
  - `parseLang(undefined)==="en"`, `parseLang("ru")==="ru"`, `parseLang("de")==="en"`
- [ ] Step 2: Run `npm test`. Expected: FAIL (module missing).
- [ ] Step 3: Implement `prefs.ts`. It must import nothing, so it's testable under plain Node.
- [ ] Step 4: Run `npm test`. Expected: PASS.

### Task 2: i18n dictionaries

**Files:** Create `frontend/src/lib/i18n/en.ts`, `es.ts`, `ru.ts`, `index.ts`, `i18n.test.ts`

**Interfaces:**
- Consumes: `Lang` from `../prefs.ts`.
- Produces:
  - `en` (flat `const` object of `key → string`, placeholders as `{name}`), `type MessageKey = keyof typeof en`
  - `es`, `ru` typed `Record<MessageKey,string>`
  - `dictionaries: Record<Lang, Record<MessageKey,string>>`
  - `format(template: string, vars?: Record<string,string|number>): string`
  - `translate(lang: Lang, key: MessageKey, vars?): string`

  Key namespaces: `nav.*`, `dash.*`, `theory.*`, `flash.*`, `quiz.*`, `progress.*`, `settings.*`, `common.*`, `error.*`, `notFound.*`, `coming.badge`, `coming.needsLabel` and `coming.<id>.name|needs` for every Task 3 id. Every user-visible string in the app goes here.

- [ ] Step 1: Tests:
  - es and ru have exactly en's key set.
  - No value is empty.
  - For every key, the set of `{placeholders}` in es/ru equals en's.
  - `format("Hi {name}", {name:"Nikita"})==="Hi Nikita"`.
  - `format` leaves unknown placeholders untouched.
- [ ] Step 2: Run `npm test`. Expected: FAIL.
- [ ] Step 3: Write the dictionaries (Castilian Spanish; Russian) and `index.ts`.
- [ ] Step 4: Run `npm test`. Expected: PASS.

### Task 3: Coming-soon registry

**Files:** Create `frontend/src/lib/comingSoon.ts`, `comingSoon.test.ts`

**Interfaces:**
- Produces:
  - `COMING_SOON` as a readonly array of `{ id: ComingSoonId }`, in this order: `search`, `notifications`, `profile`, `streak`, `xp`, `studyHours`, `weeklyTime`, `cefrSkills`, `mockExam`, `cultureTip`
  - `type ComingSoonId`
  - `comingSoonKeys(id): { name: MessageKey; needs: MessageKey }`

  The file's header comment says it is Nikita's to-do list of unbuilt features.

- [ ] Step 1: Tests:
  - 10 unique ids.
  - Every id's `name` and `needs` key exists in `en`.
- [ ] Step 2: Run `npm test`. Expected: FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run `npm test`. Expected: PASS.

### Task 4: Dashboard derivations

**Files:** Create `frontend/src/lib/dashboard.ts`, `dashboard.test.ts`

**Interfaces:**
- Consumes: `TopicSummary`, `HistoryEntry`, `LEVELS` from `./types.ts`. Make `types.ts` itself importable under Node; it already has no imports.
- Produces:
  - `nextTopic(topics: TopicSummary[]): TopicSummary | null`: the first uncompleted topic, ordered by `LEVELS` index, then `order_index`.
  - `levelProgress(topics, level): { done: number; total: number; percent: number }`: `percent` is a rounded integer, 0 when total is 0.
  - `averageAccuracy(history: HistoryEntry[]): number | null`: the mean of score/total as a rounded integer percent; `null` when empty; entries with `total===0` are skipped.
  - `quizQuestionCount(cardCount: number): number` = `Math.min(5, cardCount)`.

- [ ] Step 1: Tests:
  - `nextTopic` picks A1 #2 over B1 #1 when A1 #1 is done.
  - `nextTopic` returns `null` when all are done, and `null` for `[]`.
  - `levelProgress` gives `{2,3,67}` and `{0,0,0}`.
  - `averageAccuracy([])===null`.
  - `averageAccuracy` of 4/5 and 3/5 is `70`.
  - `quizQuestionCount(3)===3`, `(12)===5`, `(0)===0`.
- [ ] Step 2: Run `npm test`. Expected: FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run `npm test`. Expected: PASS.

### Task 5: Theme, fonts, shell, sidebar, settings

**Files:**
- Rewrite `frontend/src/styles/globals.css`: tokens under `:root[data-theme="light"]` and `:root[data-theme="dark"]`; Terra components (`.card`, `.button`, `.badge`, `.pill`, tables, `.flashcard`, `.options`); shell layout; sidebar responsive rules.
- Modify `frontend/src/app/layout.tsx`
- Create:
  - `frontend/src/lib/i18n/server.ts` (`import "server-only"`)
  - `frontend/src/components/I18nProvider.tsx` (client)
  - `frontend/src/components/Sidebar.tsx` (client)
  - `frontend/src/components/Icon.tsx`
  - `frontend/src/app/settings/page.tsx`
- Modify `frontend/src/app/actions.ts`: add `setTheme`, `setLang`.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `getPrefs(): Promise<{theme: Theme; lang: Lang}>`
  - `getT(): Promise<(key: MessageKey, vars?) => string>`
  - `<I18nProvider lang>` + `useT()` + `useLang()`
  - `setTheme(theme: string): Promise<void>` and `setLang(lang: string): Promise<void>`: validate via `parse*`, set the cookie, then `revalidatePath("/", "layout")`
  - `<Icon name="…" />` (Material Symbols span, `aria-hidden`)

**Behaviour:**
- **Layout:**
  - Load Literata and Nunito Sans with `subsets: ["latin","cyrillic"]` and `variable` CSS vars.
  - Link the Material Symbols stylesheet.
  - Render `<html lang={lang} data-theme={theme}>`, then a flex shell: `<Sidebar dueCount>` + `<main>`.
  - `dueCount` comes from `api.stats()` wrapped in try/catch, `null` on failure.
- **Sidebar:**
  - Groups "Learning" (Dashboard `/`, Theory & Rules `/theory`, Quizzes `/quizzes`, Flashcards `/flashcards` with due badge, CEFR Levels `/theory`) and "Personal" (My Progress `/history`, Settings `/settings`).
  - The active item is a green pill. Exact match for `/`; prefix match otherwise; CEFR Levels never shows active, so only one item is highlighted.
  - A "Coming soon: Profile" card sits at the bottom.
  - Widths: ≥1024px is 260px; 768–1023px is icons only (72px); below 768px it's hidden behind a top-strip menu button, opens as an overlay and closes on navigation.
- **Settings:**
  - Two sections, Appearance and Language.
  - Each option is a `<form action={setX.bind(null, value)}><button aria-pressed>`; the selected option is styled active.
  - Under Language, a note that lessons stay in English/Spanish.

- [ ] Step 1: Implement everything above.
- [ ] Step 2: Run `npm run build`. Expected: compiles, no type errors.
- [ ] Step 3: Run the app.
  - The sidebar renders. `/settings` switches theme and language instantly, and both survive a reload.
  - OS dark mode has no effect.
  - With the backend stopped, a page shows `error.tsx` inside the shell.

### Task 6: Dashboard

**Files:**
- Rewrite `frontend/src/app/page.tsx`
- Create:
  - `frontend/src/components/ComingSoon.tsx`: server; props `{ id: ComingSoonId; children?: ReactNode }`. It renders children greyed and `inert` under an overlay with the `coming.badge` pill, the name and "Needs: …".
  - `frontend/src/components/ProgressBar.tsx`

**Interfaces:**
- Consumes: `api.stats/topics/history/topic`, Task 4 functions, `getT`, `ComingSoon`.

**Behaviour:** sections in the spec's order, all strings via `t`.
- **Top bar:**
  - search → `ComingSoon search`
  - A1–C1 chips → `/theory/{L}`
  - bell → `ComingSoon notifications`
  - "Daily practice" → `/flashcards`
- **Hero:**
  - Greeting `dash.hello` with `{name:"Nikita"}`.
  - Continue button to `/theory/{level}/{id}`, or "All topics completed" → `/theory`.
  - Streak and XP slots use `ComingSoon`.
- **Study plan:**
  - Level and `levelProgress` for the next topic's level.
  - Three modules (theory / quiz with `quizQuestionCount(topic.cards.length)` / vocabulary count), loaded with `api.topic(next.id)`.
  - Empty state when there are no topics. When everything is completed, the section shows the completed message.
- **Recommended:** SRS with `cards_due`, theory block, quick quiz.
- **Metrics:**
  - `cards_total`, `quizzes_taken`, `averageAccuracy` (or "—").
  - `ComingSoon` for studyHours, weeklyTime and cefrSkills.
- **Mock exam** and **culture tip:** `ComingSoon`.

- [ ] Step 1: Implement.
- [ ] Step 2: Run `npm run build`. Expected: PASS.
- [ ] Step 3: Check in the browser with the seeded backend.
  - The real numbers match `/api/stats`.
  - All 10 coming-soon labels are visible: 9 on the dashboard, plus profile in the sidebar.

### Task 7: Restyle + translate the remaining pages

**Files:** Modify
- `src/app/theory/page.tsx`
- `src/app/theory/[level]/page.tsx`
- `src/app/theory/[level]/[topicId]/page.tsx`
- `src/app/flashcards/page.tsx`
- `src/app/quizzes/page.tsx`
- `src/app/history/page.tsx`
- `src/app/error.tsx`
- `src/app/not-found.tsx`
- `src/components/FlashcardReview.tsx`
- `src/components/QuizRunner.tsx`

**Behaviour:**
- Replace every hard-coded string with `t(...)` (`getT` on the server, `useT` in client components).
- Use the Terra classes. History's title becomes `progress.title` ("My Progress").
- Content strings stay untranslated.
- `error.tsx` keeps its backend hint text, translated.

- [ ] Step 1: Implement.
- [ ] Step 2: Run `npm test && npm run build`. Expected: PASS.
- [ ] Step 3: Grep for leftover literals. Run `grep -nE '>[^<{]*[A-Za-z]{3,}[^<{]*<' src/app src/components`. Expected: only content or brand.

### Task 8: Final verification

- [ ] Run `npm test` (frontend) and `cd backend; .venv\Scripts\python -m pytest`. Expected: all pass.
- [ ] Run `npm run build`. Expected: PASS.
- [ ] Do a browser pass in light and dark, each in en, es and ru, covering:
  - flashcard review
  - quiz submit
  - mark as read
  - the sidebar at 1280, 900 and 390px
  - OS dark mode ignored
  - reload persistence
