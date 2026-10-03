---
version: 1
slug: "web-src-app-tsx"
primary_target: "web/src/App.tsx"
related_targets: ["web/src/index.css","web/src/main.tsx"]
---

# Surface: BlameChat chat view (web/src/App.tsx)

Mode: Operate (the viewer follows a live group chat; it is recorded for a <90 s demo at ~850 CSS px wide).
Audience/job: CometChat judges watch the files argue and confess; atul asks "who broke login?", commits a fix, and watches the reaction.
Proof/content: every fact (culprit, line, code fragment, commit, test result) is computed by brain/ from git + pytest. Never invent facts in the UI.
Constraints: the real CometChatMessageHeader/List/Composer, styled only through theme tokens, view slots, a text plugin and formatters. No edits to brain/ or tinyshop/.
Build path: code-led (no image generation available).

## Direction contract
THESIS: The chat is a git blame view that talks back. Each file speaks from its own colored gutter, and facts appear as code, never as chat prose. It refuses the stock CometChat sample app (purple bubbles, robot avatars, Roboto on grey).
OWN-WORLD: Dark editor ink #12161C, panel #1A2029, line #2A323D, text #D6DEE8. Per-file hues: auth #7AA2F7, db #E0AF68, utils #F7768E, cart #9ECE6A, api #BB9AF7. Diff red #F0716B and green #5BD18B only for test state and the fix. JetBrains Mono for file names, code, hashes and header; IBM Plex Sans for the banter. Flat 6px bubbles with a 3px left gutter stripe in the speaker's hue. Members are 28px rounded-square monogram badges ("ut") with a .py tag.
STORY: The judge sees the files argue, then sees utils.py confess in a bubble that changes register: a diff-hunk frame with utils.py:6 and the commit, the fragment in red, and receipt chips ("git blame", "pytest") showing where each fact came from. They believe it is funny and real.
FIRST VIEWPORT: A slim 44px top bar reading "BlameChat / tinyshop" in mono, with a test-state pill on the right (red failing, then green after the fix). Below it, the message list fills the height. A borderless composer at the bottom has only input and send, with the placeholder "Ask the files… e.g. who broke login?". The signature moment is the confession bubble.
FORM: User-pinned direction, no concept-seed roll (seed key: none). The user chose from the phase-1 shortlist of 3 hand-built directions and waived the roll by picking directly: "go with the recomended A", then "A — Blame Gutter. Use the receipt-chip idea from C for the confession as you suggested."
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Resolved during build
- Test-state pill: mirrors the brain's own pytest-backed template lines (confession / "failing: `…`" / "still red." -> failing; "tests green ✅" / "all green right now ✅" / "tests are already green ✅" -> passing). Verified live: red after the confession, green after the real fix commit.
- Confession detection: text match on `file` L<n> `fragment` … commit `hash` (only the culprit may write these, per brain/validator.py). Verified on the real confession.
- Header is one 44px line; the tagline subtitle was dropped (not in FIRST VIEWPORT).
