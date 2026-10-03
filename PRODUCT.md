# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- **Primary (now):** CometChat "Zero to Chat" hackathon judges, who are CometChat developers. They watch a recorded demo under 90 s long, shot at 1920×1080 with the browser on the left ~55% of the screen at 125% zoom (about 850 CSS px wide). They judge creativity, real use of CometChat, and whether the demo is credible.
- **Primary (in the demo):** one developer (`atul`, the only human member) who is debugging a broken login in a small repo and asks the group "who broke login?".
- **Future (product seed):** dev teams who want regression triage to show up as a conversation in a chat they already use, on any repo, with several humans in it.

## Product Purpose
BlameChat is "git blame, but it's a group chat". Each file in the repo is a CometChat group member. When a human asks what broke, the files argue, deflect and finally confess: the culprit names the exact line, the code fragment and the commit. After the human commits a fix, a post-commit hook makes the files react: the culprit grumbles about the rewrite and auth.py reports that the tests pass again.

Success: a judge comes away believing two things equally: (1) it is funny *and* every fact is real, and (2) it is a clever, native use of CometChat (real users, a real group, REST plus the React UI Kit), not a mock-up.

## Positioning
The banter is LLM personality, but every fact in it is computed: culprit, line, code fragment, commit and test status come from git (blame, diff, bisect) and pytest. A validator rejects any LLM line that states a fact it wasn't given. Only the culprit may write a line number, code, backticks or a hash. Generic "AI explains your bug" tools can't truthfully copy that guarantee.

## Operating Context
- Demo repo `tinyshop/`: auth.py, db.py, utils.py, cart.py, api.py. History: init, then the bug commit, then two decoy commits. The bug is in utils.py L6, `.strip().lower()`.
- `brain/` (FastAPI) posts messages as the file users through the CometChat REST API. `/ask` handles the human's question; `/commit` is called by the post-commit hook.
- `web/` (Vite + React + CometChat React UI Kit v7.2.3) is logged in as `atul` and shows one group per take (`repo-tinyshop-tN`).
- Each take is reset with `reset_take.py`. A take also uses a terminal running `cli.py login alice Secret1`, which fails until the fix is in.

## Capabilities and Constraints
- The chat must be made of real CometChat UI Kit components (CometChatMessageHeader, CometChatMessageList, CometChatMessageComposer). Customise them with UI Kit theming (CSS variables, custom views, formatters/plugins); never rebuild the chat by hand.
- Don't modify `brain/` or `tinyshop/` as part of UI work.
- Must read well at ~850 CSS px wide (the recording viewport). Wider desktop is secondary.
- Messages are plain CometChat text. Code shows up inline as backticked spans (file names, `L6`, the code fragment, short hashes).
- Member personas: auth.py is a paranoid gatekeeper, db.py a tired senior, utils.py a people-pleaser who breaks things, cart.py a sarcastic bystander, api.py a sleepy bystander.
- Undecided: how several humans and arbitrary repos would work after the hackathon.

## Brand Commitments
- Name: **BlameChat**. Tagline: "git blame, but it's a group chat".
- Voice: playful dev drama that stays credible. Jokes come from the personas; facts stay exact.
- Member names are the literal file names (`auth.py`, …).

## Evidence on Hand
- A live, reproducible take (reset + brain + Vite) with the full blame conversation and the post-commit reaction.
- Real git history and pytest results in `tinyshop/`.
- There are no users, testimonials or metrics, so don't invent any.

## Product Principles
1. **Facts are computed, never generated.** Anything that looks like data (line, code, hash, test result) must come from git or pytest, and the UI should make that visible.
2. **CometChat is the stage, not a backdrop.** Show the real UI Kit working, styled through its own extension points.
3. **The files are the characters.** Each member should be recognisable at a glance as a specific file with its own personality.
4. **Readable in a 90-second recording.** Optimise for legibility at ~850 px and for following the conversation at a glance.

## Accessibility & Inclusion
No product-specific requirement was set. The baseline is WCAG AA contrast, because the demo is watched as compressed video.
