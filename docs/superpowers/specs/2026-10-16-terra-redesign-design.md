# NLFS — Terra redesign, sidebar, settings (theme + language)

**Date:** 2026-10-16
**Status:** awaiting Nikita's approval
**Design source:** `frontend/stitch_nlfs_spanish_learning_platform/` — the **Terra** variant only
(`nlfs_spanish_learning_dashboard_terra/code.html` + `screen.png`, tokens in `terra/DESIGN.md`).
The orange "Warm Iberian Modernism" variant is **not** used.

## Intent

Make NLFS look and feel like the Terra dashboard design: calm, warm, green-on-cream, with a left
sidebar instead of the top link bar. The learning materials aren't ready yet, so most of the
dashboard has no data behind it. Those parts still appear, as clearly labelled **"Coming soon"**
sections, so the page matches the design and Nikita can see what's left to build.

## Goals

1. **Terra visual style everywhere.** This covers the dashboard and every existing page (Theory, level roadmap,
   topic, Flashcards, Quizzes, History/Progress, error, 404).
2. **Left sidebar** replaces the top header and holds all navigation, including a **Settings** button.
3. **Settings page** with two controls:
   - **Theme:** Light / Dark.
   - **Interface language:** English / Castellano / Русский.
4. **Light and dark themes**, both Terra. The app **never follows the OS/laptop theme**. It starts
   **Light** and remembers the last choice.
5. **Interface language** starts as **English** and remembers the last choice.
6. **Dashboard rebuilt on the Terra layout**, using real data wherever the backend has it and labelled
   "Coming soon" placeholders everywhere else.

## Non-goals

- No backend changes. No new endpoints, models or tables. Everything real on the dashboard comes from the
  existing `/api/stats`, `/api/theory/topics`, `/api/srs/review` and `/api/quiz/history`.
- No translation of learning content. Theory text, topic titles, flashcards and quiz prompts stay as
  stored (English/Spanish). **Russian theory is not supported for now.** Choosing Русский only
  translates the interface around the content.
- No fake numbers. Nothing from the mockup (Elena, 14-day streak, 350/500 XP, 1,420 words…) is shown
  as if it were real.
- The orange design, auth/real user accounts and mobile bottom-tab navigation are out of scope.

## Anti-goals (would count as failure even if it "works")

- The page flashes the wrong theme or language on load. Both must be correct in the first server-rendered HTML.
- A "Coming soon" block that doesn't say *what* is coming.
- The dark theme following the laptop's setting.
- Existing flows (flip and rate a flashcard, take and submit a quiz, mark a topic read) broken or changed in behaviour.

## Decisions made by Nikita

| Topic | Decision |
|---|---|
| Design variant | Terra (green) only |
| Themes | Light + dark; never rely on the OS theme |
| Theme control | Toggle lives on a Settings page, reached from a Settings button in the sidebar |
| Missing data | Show the sections as "Coming soon", each clearly labelled with what's missing |
| Languages | English, Castellano, Русский, chosen in Settings |
| Default language | English |
| Content language | Theory stays English/Spanish; no Russian theory for now |

## Design

### Visual tokens (from `terra/DESIGN.md` + the Terra HTML config)

- **Light:**
  - background `#faf6f0`
  - surfaces from `#ffffff` (cards) through `#f4f0e8` / `#eae6de`
  - text `#2e3230`, muted text `#4a4e4a` / outline `#74796e`
  - primary `#4a7c59`, primary tint `#c8e8d0`
  - tertiary/amber `#705c30`, amber tint `#f8e0a8`
  - error `#b83230`
- **Dark (Claude's call; Terra has no dark variant):**
  - background: deep green-charcoal (≈ `#141a17`), surfaces stepping up (≈ `#1c2420`, `#24302a`)
  - text: cream (≈ `#ece6dc`) with a muted cream for secondary text
  - primary: a lighter green (≈ `#8ecf9e`) on dark, so it stays readable
  - amber: ≈ `#dcc48e`
  - Contrast for body text must be ≥ 4.5:1.
- **Fonts:** Literata (headlines) and Nunito Sans (body/labels), loaded with `next/font/google`.
- **Icons:** Material Symbols Outlined, as in the design (Google Fonts stylesheet).
- **Shape and depth:** cards 16px radius, buttons 12px, pills fully rounded. Very soft shadow
  `0 4px 20px rgba(46,50,48,.06)`. Tonal layering is preferred over borders.
- All colours are CSS custom properties on `:root[data-theme="light"]` and `:root[data-theme="dark"]` in
  `globals.css`. The existing `@media (prefers-color-scheme: dark)` block is **removed**.
- Styling stays as plain CSS in `globals.css` (the project's current idiom). No Tailwind.

### Theme and language persistence

- Both are stored in cookies: `nlfs-theme` (`light`|`dark`) and `nlfs-lang` (`en`|`es`|`ru`).
- The root layout reads them on the server (`cookies()` from `next/headers`) and renders
  `<html lang=… data-theme=…>`. That gives the correct first paint with no flash. Missing or invalid values fall back to `light` / `en`.
- The Settings controls call a **Server Action** that sets the cookie (long expiry, ~1 year) and
  revalidates the layout. This matches how the app already writes data.

### Interface text (i18n)

- One dictionary per language in `src/lib/i18n/` (`en.ts`, `es.ts`, `ru.ts`) with identical keys.
  `en` is the source of truth, and the others are typed against it, so a missing key is a type error.
- Server components get the dictionary with a helper that reads the cookie.
- Client components (`FlashcardReview`, `QuizRunner`, `error.tsx`, the settings controls) get it from a small
  React context provider placed in the root layout.
- Every hard-coded UI string moves into the dictionaries. That includes the current mixed ones ("Nivel",
  "No encontrado", "Práctica:", "¡Terminado!").
- Spanish uses Castilian conventions (Castellano).

### Layout shell

- **Sidebar, desktop ≥ 1024px:** fixed, about 260px wide, on a slightly darker cream surface. Contents, top to bottom:
  - **Brand:** NLFS logo text.
  - **Learning:**

    | Item | Route | Note |
    |---|---|---|
    | Dashboard | `/` | |
    | Theory & Rules | `/theory` | |
    | Quizzes | `/quizzes` | |
    | Flashcards | `/flashcards` | Shows a small count badge when cards are due |
    | CEFR Levels | `/theory` | Claude's call: the existing level-picker page is the CEFR level view; Theory & Rules and CEFR Levels both land there for now |

  - **Personal:**

    | Item | Route | Note |
    |---|---|---|
    | My Progress | `/history` | Existing History page, renamed in the UI |
    | Settings | `/settings` | New |

  - **Bottom of the sidebar:** the profile card from the design, as a "Coming soon: Profile" placeholder.
  - **Active route:** solid green pill, as in the design.
- **Tablet, 768–1023px:** the sidebar collapses to icons only, about 72px wide (Claude's call, from the design notes).
- **Mobile, < 768px:** the sidebar is hidden behind a menu button in a slim top strip and opens as an overlay (Claude's call).
- **Top bar on the dashboard,** as in the design:
  - Search: a "Coming soon: Search" pill.
  - A1–C1 level chips: real. Each links to `/theory/{level}`.
  - Notifications bell: "Coming soon".
  - **Daily Practice** button: real, goes to `/flashcards`.

  Other pages show only the page content, without the top bar (Claude's call).
- The content area is wider than today's 820px: about 1200px for the dashboard and about 820px for reading pages.

### Dashboard sections

Each section is marked **real**, **partly real** or **coming soon**.

1. **Welcome hero** (partly real)
   - **Real:**
     - Greeting "Hello, Nikita!" in the current language.
     - A **Continue: {next topic}** button to the first uncompleted topic (lowest level, then `order_index`).
     - If every topic is done, the button reads "All topics completed" and goes to `/theory`.
   - **Coming soon:**
     - "Weekly streak" strip.
     - "Daily XP goal" card.
2. **Main study plan** (real)
   - The current level is the level of the next uncompleted topic.
   - Shows "{done} of {total} lessons completed" and a progress bar with % for that level.
   - Three module cards:
     - **Theory:** the next topic.
     - **Quiz:** that topic's quiz, with its question count.
     - **Vocabulary:** that topic's card count. It links to the topic page.
   - Card fields with no data (XP rewards, minutes) are left out, not faked.
   - The quiz question count is `min(5, topic card count)`, which matches what `/api/quiz/generate` returns.
   - **Empty state:** if there are no topics at all, the section shows "No topics yet: materials are being prepared" instead of the cards.
3. **Recommended practice today** (real)
   - Spaced repetition: `cards_due` and a "Review now" button.
   - Theory block: the next topic.
   - Quick quiz: a quiz for the next topic.
4. **Learning metrics** (partly real)
   - **Real tiles:**
     - Vocabulary in deck (`cards_total`).
     - Tests completed (`quizzes_taken`).
     - Average accuracy (mean score/total over quiz history, or "—" when there's none).
   - **Coming soon:**
     - "Study hours per day" chart.
     - "Weekly study time".
     - "CEFR skills breakdown" (listening, speaking, grammar).
5. **Next level exam** (coming soon): the whole card is "Coming soon: Mock CEFR exam".
6. **Culture & real usage** (coming soon): "Coming soon: Culture tip".

### "Coming soon" placeholders

- One reusable component. It renders the section's real layout shape, greyed out and non-interactive, with:
  - a **"Coming soon"** pill
  - the feature **name**, for example "XP & daily goal"
  - a one-line **"Needs:"** note saying what has to exist first, for example "Needs: XP rules and activity tracking in the backend"
- Every placeholder is declared in a single list, `src/lib/comingSoon.ts`, with id, name and needs-note
  (translated through the dictionaries). That file doubles as Nikita's to-do list. The initial entries are:

  | Feature | Where it appears |
  |---|---|
  | Search | Dashboard top bar |
  | Notifications | Dashboard top bar |
  | Profile | Sidebar card |
  | Weekly streak | Welcome hero |
  | XP & daily goal | Welcome hero |
  | Study-hours chart | Learning metrics |
  | Weekly study time | Learning metrics |
  | CEFR skills breakdown | Learning metrics |
  | Mock CEFR exam | Dashboard card |
  | Culture tip | Dashboard card |

### Settings page (`/settings`)

- **Appearance:** a segmented control, Light | Dark. It takes effect immediately.
- **Language:** a segmented control or radio, English | Castellano | Русский. It takes effect immediately.
  - A short note says that lesson content stays in English/Spanish.
- No other settings for now.

### Other pages

These keep their structure and behaviour. They're restyled with Terra cards, buttons, badges, tables and
headings, and their strings are translated.

- **Flashcards:** a Terra flashcard component (white card, 16px radius, soft shadow). Rating buttons 0–5 are unchanged in behaviour.
- **Quizzes:** answer options become Terra selection tiles.
- **History:** retitled "My Progress", with the same table.

## Constraints

- Next.js 16.4 (per `frontend/AGENTS.md`). Check `node_modules/next/dist/docs/` for `cookies()`, Server
  Actions and `next/font` before using them.
- Data is still fetched on the Next.js server, and writes go through Server Actions (the existing architecture).
- No git repository, so nothing is committed.

## Left to the builder

- Exact component split and file names, apart from the files named above.
- Exact dark-palette hex values, within the stated direction and contrast rule.
- Exact Spanish and Russian wording.
- Icon choice per sidebar item and section, taken from the design wherever it has one.

## Verification

- `npm run build` passes with no type errors.
- Backend tests still pass (they shouldn't be touched).
- Manual run with the backend up, checking:
  - every page in light and dark, and in en/es/ru
  - setting the laptop to dark mode does **not** change the app
  - reloading keeps both choices
  - flashcard review, quiz submit and "mark as read" still work
  - the sidebar works at desktop, tablet and phone widths
  - every "Coming soon" block shows its name and its "Needs:" note
