import type { TestState, TestStatus } from "./useTestState";

// Five gutter bars, one per member hue: the blame gutter the whole UI is built on.
export function Mark() {
  return (
    <svg className="bc-mark" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x="2" y={2 + i * 3.4} width={i === 2 ? 16 : 10 + ((i * 3) % 5)} height="2.2" rx="1.1" data-hue={i} />
      ))}
    </svg>
  );
}

export function Title({ group }: { group: CometChat.Group }) {
  // Group names carry an emoji ("tinyshop 🧑‍💻"); the header shows the repo name only.
  const repo = group.getName().replace(/[^\p{L}\p{N}._-]+/gu, " ").trim();
  return (
    <h1 className="bc-title">
      <span className="bc-title__product">BlameChat</span>
      <span className="bc-title__sep" aria-hidden="true">/</span>
      <span className="bc-title__repo">{repo}</span>
    </h1>
  );
}

const LABEL: Record<TestState, string> = {
  unknown: "tests not run yet",
  failing: "tests failing",
  passing: "tests passing",
};

// Everything shown comes from the brain's cached pytest result (GET /status).
export function TestPill({ status }: { status: TestStatus }) {
  const { state } = status;
  const hint = state === "unknown"
    ? "The brain has not run pytest yet"
    : `pytest at ${status.head}: ${status.failed} failed, ${status.passed ?? "?"} passed (checked ${status.checked_at})`
      + (status.failing_test ? `. Failing: ${status.failing_test}` : "");
  return (
    <span className="bc-pill" data-state={state} title={hint} role="status" aria-live="polite">
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        {state === "passing" && <path d="M3.5 8.5l3 3 6-7" />}
        {state === "failing" && <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" />}
        {state === "unknown" && <circle cx="8" cy="8" r="4.5" />}
      </svg>
      <span className="bc-pill__tool">pytest</span>
      {LABEL[state]}
    </span>
  );
}
