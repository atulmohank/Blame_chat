---
name: BlameChat
description: git blame, but it's a group chat. A dark editor-ink theme over the real CometChat React UI Kit, one hue per file.
colors:
  editor-ink: "#12161c"
  panel-slate: "#1a2029"
  raised-slate: "#212834"
  hairline: "#2a323d"
  code-well: "#0d1117"
  text-primary: "#d6dee8"
  text-secondary: "#9aa6b5"
  text-tertiary: "#7d8899"
  diff-red: "#f0716b"
  diff-green: "#5bd18b"
  hue-auth-blue: "#7aa2f7"
  hue-db-amber: "#e0af68"
  hue-utils-rose: "#f7768e"
  hue-cart-lime: "#9ece6a"
  hue-api-violet: "#bb9af7"
typography:
  title:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.2
  body:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  sender:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.2
  code-inline:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "13.5px"
    fontWeight: 500
    lineHeight: 1.4
  code-receipt:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.4
  label:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1
  chip:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "11.5px"
    fontWeight: 500
    lineHeight: 1.3
  meta:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  xs: "3px"
  sm: "4px"
  md: "6px"
  badge: "7px"
spacing:
  2xs: "2px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
  2xl: "16px"
components:
  header-bar:
    backgroundColor: "{colors.editor-ink}"
    textColor: "{colors.text-primary}"
    typography: "{typography.title}"
    height: "44px"
    padding: "0 16px"
  bubble-incoming:
    backgroundColor: "{colors.panel-slate}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "2px 4px 2px 8px"
  bubble-outgoing:
    backgroundColor: "transparent"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "2px 4px"
  file-badge:
    backgroundColor: "{colors.panel-slate}"
    typography: "{typography.label}"
    rounded: "{rounded.badge}"
    size: "30px"
  sender-name:
    typography: "{typography.sender}"
    padding: "0 0 4px 2px"
  inline-code:
    backgroundColor: "{colors.code-well}"
    textColor: "{colors.text-primary}"
    typography: "{typography.code-inline}"
    rounded: "{rounded.sm}"
    padding: "1px 5px"
  test-pill:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    height: "28px"
    padding: "0 10px"
  test-pill-failing:
    textColor: "{colors.diff-red}"
  test-pill-passing:
    textColor: "{colors.diff-green}"
  receipt:
    backgroundColor: "{colors.code-well}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
  receipt-diff:
    textColor: "{colors.diff-red}"
    typography: "{typography.code-receipt}"
    padding: "8px 10px"
  evidence-chip:
    backgroundColor: "{colors.panel-slate}"
    textColor: "{colors.text-primary}"
    typography: "{typography.chip}"
    rounded: "{rounded.sm}"
    padding: "2px 7px"
  composer:
    backgroundColor: "{colors.editor-ink}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "0"
---

# Design System: BlameChat

## Overview

**Creative North Star: "Blame Gutter"**

The chat is a git blame view that talks back. Every file in the repo is a group member, and each one speaks from its own colored gutter, the way an editor's blame column tints the lines a commit owns. The surface is dark editor ink, flat and quiet, so the only saturated color on screen is identity (which file is talking) or test state (red failing, green passing). Banter is set in a humanist sans; anything that is a fact (file name, line, code fragment, commit hash, tool name) is set in mono and framed like code.

The system is a skin, not a rebuild. It is the real CometChat React UI Kit v7.2.3, themed only through the kit's own extension points: its `--cometchat-*` CSS tokens (mapped from the `--bc-*` tokens on `:root`), its BEM classes, the message header's view slots (leading, title, subtitle, trailing), and a text plugin that swaps the leading view, header view, bubble wrapper and status view. Future surfaces extend the kit the same way; they never re-implement a header, list, bubble or composer by hand.

Density is tuned for a ~850 CSS px recording viewport watched as compressed video: a slim 44px header, 15px body text, short bubbles that hug their content, and generous vertical rhythm between speakers so the argument can be followed at a glance. The visual rejection is confirmed by the direction: not the stock CometChat sample look (purple bubbles, robot avatars, Roboto on grey).

**Key Characteristics:**
- Dark editor ink with tonal layering (ink, panel, raised, code well); no drop shadows.
- One hue per file, carried by the gutter stripe, the badge and the sender name, never by the bubble fill.
- Diff red and green are reserved for test state and the confession.
- Mono for facts and names, sans for banter.
- Facts appear as code, sourced from git and pytest, never as decorated prose.
- Real CometChat UI Kit components, themed through tokens, slots and plugins only.

## Colors

A cool, near-monochrome slate ground with five pastel-bright file hues and one red/green diff pair, each color tied to a single meaning.

### Primary
- **Text Primary** (`text-primary`): the kit's primary color and the body text. Deliberately a light neutral, not an accent, so no kit control (send icon, mentions, highlights) competes with the file hues.

### Secondary (file hues)
Five identity hues, one per file slot, assigned by `data-hue` 0-4. Unknown files hash into one of the five slots so they still get a stable color.
- **Auth Blue** (`hue-auth-blue`, slot 0, `auth.py`): also the focus ring and the text selection tint.
- **DB Amber** (`hue-db-amber`, slot 1, `db.py`).
- **Utils Rose** (`hue-utils-rose`, slot 2, `utils.py`).
- **Cart Lime** (`hue-cart-lime`, slot 3, `cart.py`).
- **API Violet** (`hue-api-violet`, slot 4, `api.py`).

### Tertiary (diff state)
- **Diff Red** (`diff-red`): failing tests (pill), the confession ring, the removed-line row of the receipt, and the error detail on the status screen.
- **Diff Green** (`diff-green`): passing tests (pill) and the composer caret.

### Neutral
- **Editor Ink** (`editor-ink`): page, message list, header and composer background.
- **Panel Slate** (`panel-slate`): incoming bubble fill, evidence chips, badge base.
- **Raised Slate** (`raised-slate`): mention spans and the kit's raised background.
- **Hairline** (`hairline`): every border and divider, the outgoing bubble outline, the scrollbar thumb.
- **Code Well** (`code-well`): inline code and the receipt body; the darkest surface, read as "this is code".
- **Text Secondary** (`text-secondary`): repo name, pill at rest, receipt header, line numbers, `.py` tag.
- **Text Tertiary** (`text-tertiary`): source line ("computed by") and pending/connecting text.

### Named Rules
**The One Hue Per File Rule.** A file's hue appears only on that file's gutter stripe, badge, sender name and receipt location. It is never a bubble fill and never shared across files.

**The Diff-Only Red/Green Rule.** Red and green mean test state and the culprit line, nothing else. No red for generic errors in chat, no green for generic success.

**The Neutral Primary Rule.** The kit's primary color is mapped to the body text color, so stock kit accents never introduce a sixth hue.

## Typography

**Display Font:** none (the system has no display tier)
**Body Font:** IBM Plex Sans (with system-ui, sans-serif), weights 400/500/600
**Label/Mono Font:** JetBrains Mono Variable (with JetBrains Mono, ui-monospace, Consolas, monospace)

**Character:** Plex Sans carries the personas' voices plainly; JetBrains Mono carries everything that would appear in a terminal or an editor. The pairing reads as "a chat inside an IDE".

### Hierarchy
- **Title** (600 mono, 15px, 1.2): the header's "BlameChat / tinyshop"; the separator and repo drop to 400 in Text Secondary.
- **Body** (400 sans, 15px, 1.5): every message and the composer input.
- **Sender** (600 mono, 13px, 1.2): the file name above each incoming bubble, in that file's hue.
- **Code Inline** (500 mono, 13.5px, 1.4): backticked spans and mentions inside messages.
- **Code Receipt** (500 mono, 15px, 1.4): the culprit fragment in the confession receipt; line number drops to 13px.
- **Label** (500 mono, 13px, 1): the test pill; the badge monogram uses 700 mono at 12.5px.
- **Chip** (500 mono, 11.5px, 1.3): evidence chips naming the tool.
- **Meta** (400 sans, 12px, 1.3): the receipt's source line.

### Named Rules
**The Facts Are Mono Rule.** File names, line numbers, code, hashes and tool names are always mono. Persona banter is always sans. A sentence may mix both, but a fact never appears in sans.

## Layout

Three full-height columns (`100dvh`): **In the room** (left, `clamp(200px, 17vw, 240px)`), the chat (center), **Evidence** (right, `clamp(288px, 26vw, 360px)`), split by hairlines. Each side panel opens with a 44px head that lines up with the kit header. The chat column is the real kit: 44px header, message list filling the remaining height, composer pinned at the bottom with a 1px hairline above it. No group list, no thread panes. Recording sizes are 1350×900 (chat ≈770px) and 1100×900 (chat ≈612px). Below 1000px the room collapses to a 56px strip of badges; below 760px Evidence becomes a right-hand drawer opened from an "Evidence" button beside the pytest pill (Escape closes it); at 520px and below the room strip is hidden. Incoming messages sit left with a 30px file badge as the leading view and the sender name above the bubble; outgoing (the human) sit right with no badge. The list gets 12px block padding; bubbles hug their content. Per-bubble timestamps, receipts, date separators, sticky dates and group action messages are all hidden: in a 90-second recording they are noise.

The primary viewport is ~850 CSS px (the recording width); wider desktop simply gives the column more room. At 520px and below, the header title shrinks to 14px and ellipsizes, the pill drops its "pytest" tool label and tightens, and the receipt's diff and chips step down a size. The receipt's code fragment may wrap only before a `.` in a call chain, never inside a token.

## Elevation & Depth

Flat. Depth comes from tonal layering only: Code Well (darkest) for code, Editor Ink for the ground, Panel Slate for incoming bubbles and chips, Raised Slate for mentions. Hairline borders separate regions. The one `box-shadow` in the system is the inset gutter stripe, which is a 3px colored edge, not elevation. The confession uses a 1px Diff Red outline offset 2px outside the bubble, so the ring and the speaker's gutter remain two separate marks.

### Named Rules
**The Flat Ink Rule.** No drop shadows, glows or blur anywhere. If something needs to stand out, it changes tone, gains a hairline, or takes a diff color.

## Shapes

Small, editor-like corners: 6px for bubbles, the pill and the receipt; 4px for inline code and chips; 3px for the badge's `.py` tag; 7px for the 30px file badge (a rounded square, never a circle). The composer is square-cornered and full-bleed. The Blame Gutter itself is a straight 3px vertical stripe on the inside left edge of every incoming bubble. The header mark is five short rounded bars, one per file hue, a miniature gutter.

## Components

### Header Bar
Slim and quiet. 44px tall on Editor Ink, padded 0 16px. Leading slot: the five-bar gutter mark (20px). Title slot: "BlameChat / repo" in mono, the repo name stripped of any emoji from the group name. Subtitle slot: empty and hidden. Trailing slot: the test pill. Back, search, voice and video controls are hidden through kit props.

### Test Pill (signature)
A status readout, not a button. 28px tall, 6px radius, hairline border, mono label with a 14px stroked icon (circle / cross / check) and a "pytest" tool label.
- **Unknown:** Text Secondary on transparent, "tests not run yet".
- **Failing:** Diff Red text, border Diff Red at 45%, fill Diff Red at 10%.
- **Passing:** Diff Green text, border Diff Green at 45%, fill Diff Green at 10%.
- **Transition:** color, border and background ease over 0.4s `cubic-bezier(0.16, 1, 0.3, 1)`; off under `prefers-reduced-motion`.
- **Source:** it only mirrors the brain's own pytest-backed template lines; the UI never infers test state on its own. It is a polite live region.

### File Badge
Replaces the kit's avatar through the plugin's leading view. 30px rounded square (7px), fill = file hue at 16% over Panel Slate, border = file hue at 55%, two-letter monogram (first two letters of the stem) in the file hue, 700 mono 12.5px. A small `.ext` tag in Text Secondary on Editor Ink sits off the bottom-right corner. Purely decorative to assistive tech; the sender name carries the identity.

### Message Bubbles
- **Incoming (file):** Panel Slate fill, 6px radius, the Blame Gutter stripe (`inset 3px 0 0` in the file hue, falling back to Hairline), padding 2px 4px 2px 8px. Sender name above in the file hue.
- **Outgoing (human):** no fill, 1px Hairline outline, padding 2px 4px, body text color.
- **Inline code / mentions:** Code Well fill with a Hairline border and 4px radius for code; Raised Slate for mentions. Both mono 13.5px.

### Confession Receipt (signature)
The one bubble that changes register. The stock text bubble still renders the message (never truncated behind "Read more"); the bubble fill tints to Diff Red at 6% over Panel Slate and gains the offset red ring. Below the text sits a receipt figure: Code Well, 1px Hairline, 6px radius.
- **Head:** `file:line` in the culprit's hue on the left, commit hash on the right, mono 12.5px, hairline below.
- **Diff row:** a three-column hunk (line number, `−` sign, fragment) in Diff Red on Diff Red at 12%.
- **Source line:** "computed by" in Meta, followed by evidence chips.
- **Entrance:** a top-to-bottom clip-path reveal with fade, 0.6s `cubic-bezier(0.16, 1, 0.3, 1)`; off under `prefers-reduced-motion`.
- **Source of truth:** it shows only the four facts parsed from the culprit's own message (file, line, fragment, commit). It never adds a fact the message did not state.

### Evidence Chips
Tool names as tags: Panel Slate, 1px Hairline, 4px radius, padding 2px 7px, mono 11.5px in Text Primary. Static; they name where facts came from (`pytest`, `git`).

### In the Room (side panel)
Read-only roster of the real CometChat group members: atul first (neutral badge, "you, online" with a neutral presence dot, since presence is not test state), then the five files in gutter order with their file badge and mono name in the file hue. Under each file, a mono 12px status from the brain's `room` event, derived from `find_culprit`'s facts: `culprit · L6` in Diff Red on a Diff Red 8% row, `changed, never ran` and `ran in test` in Text Secondary, `bystander` and `not checked yet` in Text Tertiary, and after a green commit a stroked check plus `green` in Diff Green on a Diff Green 6% row. A 9px status mark on the badge corner (red or green only) keeps the status readable once the panel collapses to its strip.

### Evidence (side panel)
A read-only timeline of the brain's steps from `GET /events`, on Code Well (machine output, like the receipt). The head shows "Evidence" and `tinyshop HEAD` with the hash as a chip; it follows commit events. Each row: the brain's own `HH:MM:SS` (mono 11.5px, tabular, Text Tertiary), a 14px stroked icon per step kind, a sans 13px label with tool names in mono, and the facts as code chips (file chips in that file's hue, test counts in Diff Red or Diff Green, hashes and "commit 1 of 3, not HEAD" neutral). Each new question or commit starts a block with a hairline above it. Rows appear exactly when the brain emits them, with no added delay or entrance animation; the list stays pinned to the newest step unless the viewer scrolls up. Status and room events are not repeated here; the pill and the room show them.

### Composer
The kit composer reduced to input and send: attachments, emoji, voice, stickers and live reactions hidden by props. Editor Ink, square corners, 1px Hairline top border, body type, placeholder "Ask the files… e.g. who broke login?", Diff Green caret.

### Browser States
Focus is a 2px Auth Blue outline offset 2px on every focusable element inside the kit. Selection is Auth Blue at 35%. Scrollbars are thin, Hairline on transparent. The pre-mount loading and error screens use mono, centered, with the error detail in Diff Red.

## Do's and Don'ts

### Do:
- **Do** theme through the kit: set `--cometchat-*` tokens from `--bc-*`, target kit BEM classes, fill header view slots, and extend the text plugin.
- **Do** mark every incoming file bubble with the 3px inset Blame Gutter stripe in that file's hue.
- **Do** set file names, lines, code, hashes and tool names in JetBrains Mono.
- **Do** reserve Diff Red and Diff Green for test state, the culprit line and the confession.
- **Do** show only facts that git or pytest produced, and show where they came from with evidence chips.
- **Do** build depth from tone and hairlines (Code Well, Editor Ink, Panel Slate, Raised Slate, Hairline).
- **Do** disable the receipt reveal and pill transition under `prefers-reduced-motion`.

### Don't:
- **Don't** rebuild the header, message list, bubbles or composer by hand, or swap in non-kit chat components.
- **Don't** fill a bubble with a file hue, or let one file's hue appear on another file's message.
- **Don't** use red or green for anything other than test state and the culprit line.
- **Don't** use drop shadows, glows or blur; the only shadow is the inset gutter stripe.
- **Don't** let the UI invent or infer a fact (line, fragment, commit, test result) the brain did not send.
- **Don't** fall back to the stock CometChat sample look: purple bubbles, robot avatars, Roboto on grey.
- **Don't** fold the confession behind "Read more"; it carries the commit.
