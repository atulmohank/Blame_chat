import { useEffect, useLayoutEffect, useRef, type ReactNode } from "react";
import { useBrain, type BrainEvent } from "./brainEvents";
import { fileIdentity } from "./files";

// Read-only timeline of the brain's steps, straight from /events. Every time is the brain's own
// log stamp and every chip is a value from the event's refs (ground.py, pytest, git, CometChat).
// Nothing is delayed, reordered or invented here.

const HIDDEN = new Set(["room", "status"]); // the room panel and the pytest pill show these

type Icon = "ask" | "ground" | "test" | "diff" | "trace" | "commit" | "files" | "post" | "flag" | "wording" | "alert" | "fix" | "split" | "dot";

const PATHS: Record<Icon, ReactNode> = {
  ask: <path d="M3 4.5h10v6H7.5L5 13v-2.5H3z" />,
  ground: <><circle cx="8" cy="8" r="4.5" /><path d="M8 1.5v3M8 11.5v3M1.5 8h3M11.5 8h3" /></>,
  test: <path d="M6 2h4M6.5 2v4.2L3 12.6A1 1 0 0 0 3.9 14h8.2a1 1 0 0 0 .9-1.4L9.5 6.2V2M4.6 10h6.8" />,
  diff: <path d="M5 2.5v6M2 5.5h6M8.5 12h5.5" />,
  trace: <path d="M3 3.5h4v3h6M7 6.5v6h6M3 3.5v9" />,
  commit: <><circle cx="8" cy="8" r="2.8" /><path d="M1.5 8h3.7M10.8 8h3.7" /></>,
  files: <path d="M4 2h5l3 3v9H4zM9 2v3h3" />,
  post: <path d="M2.5 8l11-5.5-3.5 11-2.5-4.5z" />,
  flag: <path d="M3.5 14V2.5M3.5 3h8l-1.8 3 1.8 3h-8" />,
  wording: <path d="M2.5 4h11M2.5 8h7M2.5 12h9" />,
  alert: <path d="M8 2.5l6 11H2zM8 6.5v3.2M8 11.6v.2" />,
  fix: <path d="M10.5 2.5a3 3 0 0 0-2.7 4.2L2.5 12l1.5 1.5 5.3-5.3a3 3 0 0 0 4.2-2.7l-1.8 1.3-1.7-.5-.5-1.7z" />,
  split: <path d="M4 2v4c0 2 4 2 4 4v4M12 2v4c0 2-4 2-4 4" />,
  dot: <circle cx="8" cy="8" r="2" />,
};

function Glyph({ name }: { name: Icon }) {
  return (
    <svg className="bc-ev__icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">{PATHS[name]}</svg>
  );
}

function Chip({ children, tone }: { children: ReactNode; tone?: "red" | "green" }) {
  return <code className="bc-ev__chip" data-tone={tone}>{children}</code>;
}

// Test ids may wrap only after a "/" or "::", never inside a name.
function Path({ text }: { text: string }) {
  return (
    <code className="bc-ev__path">
      {String(text).split(/(?<=\/|::)/).map((part, i) => <span key={i}>{i > 0 && <wbr />}{part}</span>)}
    </code>
  );
}

function Tool({ children }: { children: ReactNode }) {
  return <code className="bc-ev__tool">{children}</code>;
}

function FileChip({ file, line }: { file: string; line?: number | null }) {
  const id = fileIdentity(file.replace(/\./g, "_"), file);
  return (
    <code className="bc-ev__chip bc-ev__chip--file" data-hue={id?.slot}>
      {file}{line ? <span className="bc-ev__line"> L{line}</span> : null}
    </code>
  );
}

const short = (hash?: string | null) => (hash ? hash.slice(0, 7) : null);

function position(refs: Record<string, any>) {
  if (!refs.index || !refs.of) return null;
  return `commit ${refs.index} of ${refs.of}${refs.is_head ? ", HEAD" : ", not HEAD"}`;
}

type Row = { icon: Icon; label: ReactNode; facts?: ReactNode; note?: ReactNode };

function describe(e: BrainEvent): Row {
  const r = e.refs;
  switch (e.kind) {
    case "asked":
      return { icon: "ask", label: "atul asked", note: <q className="bc-ev__quote">{r.text}</q> };
    case "grounding":
      return { icon: "ground", label: "Grounding the question" };
    case "pytest": {
      const red = r.failed > 0;
      return {
        icon: "test",
        label: <><Tool>pytest</Tool>{r.changed ? " after the commit" : ""}</>,
        facts: <Chip tone={red ? "red" : "green"}>{r.failed} failed{r.passed != null ? `, ${r.passed} passed` : ""}</Chip>,
        note: r.failing_test ? <Path text={r.failing_test} /> : undefined,
      };
    }
    case "changed":
      return {
        icon: "diff",
        label: <>Changed since green{r.last_green && <> <Chip>{short(r.last_green)}</Chip></>}</>,
        facts: (r.files ?? []).map((f: string) => <FileChip key={f} file={f} />),
      };
    case "ran":
      return {
        icon: "trace",
        label: "Ran in the failing test",
        facts: (r.hits ?? []).map((h: any) => <FileChip key={`${h.file}:${h.line}`} file={h.file} line={h.line} />),
      };
    case "bisect":
      return { icon: "split", label: <><Tool>git bisect</Tool>{r.commit ? " first bad commit" : ""}</>, facts: r.commit && <Chip>{r.commit}</Chip>,
        note: r.failing_test ? <Path text={r.failing_test} /> : undefined };
    case "blame": {
      const where = position(r);
      return {
        icon: "commit",
        label: <Tool>git blame</Tool>,
        facts: <>
          {r.file && <FileChip file={r.file} line={r.line} />}
          {r.commit && <Chip>{r.commit}</Chip>}
          {where && <Chip>{where}</Chip>}
        </>,
        note: r.summary ? <Path text={r.summary} /> : undefined,
      };
    }
    case "asking":
      return { icon: "files", label: `Asking the files (${(r.speakers ?? []).length} replies)` };
    case "posted": {
      return {
        icon: "post",
        label: <>{r.file ? <FileChip file={r.file} /> : r.uid} posted</>,
        facts: r.id != null && <Chip>message {r.id}</Chip>,
      };
    }
    case "llm":
      if (r.fallback) return { icon: "wording", label: "Wording: template fallback" };
      if (r.attempt) return { icon: "wording", label: `Wording: attempt ${r.attempt} ${r.ok ? "passed the validator" : "rejected"}` };
      return { icon: "wording", label: `Wording the facts (${r.mode})` };
    case "commit":
      return {
        icon: "commit",
        label: r.changed ? "Commit touched no files in the room" : "Commit detected",
        facts: r.commit && <Chip>{r.commit}</Chip>,
        note: r.subject ? <Path text={r.subject} /> : undefined,
      };
    case "last_green":
      return { icon: "flag", label: <><Tool>last_green</Tool> moved</>, facts: <Chip tone="green">{r.commit}</Chip> };
    case "still_red":
      return { icon: "alert", label: "Still red", facts: <>{r.file && <FileChip file={r.file} line={r.line} />}{r.commit && <Chip>{r.commit}</Chip>}</> };
    case "fix":
      return { icon: "fix", label: "Fix computed", facts: <>{r.file && <FileChip file={r.file} line={r.line} />}{r.fragment && <Chip tone="red">{r.fragment}</Chip>}</> };
    case "failing":
      return { icon: "alert", label: "Failing test", note: <Path text={r.test} />, facts: r.owner && <FileChip file={r.owner} /> };
    case "error":
      return { icon: "alert", label: e.text };
    default:
      return { icon: "dot", label: e.text };
  }
}

function useStickToBottom(dep: unknown) {
  const ref = useRef<HTMLOListElement>(null);
  const pinned = useRef(true);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onScroll = () => { pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24; };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);
  useLayoutEffect(() => {
    const el = ref.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [dep]);
  return ref;
}

export function Evidence({ id, onClose }: { id: string; onClose?: () => void }) {
  const brain = useBrain();
  const steps = brain.events.filter((e) => !HIDDEN.has(e.kind));
  const list = useStickToBottom(steps.length);

  return (
    <aside className="bc-panel bc-evidence" id={id} aria-label="Evidence">
      <header className="bc-panel__head">
        <h2 className="bc-panel__title">Evidence</h2>
        <span className="bc-evidence__head" title="tinyshop HEAD">
          {brain.head ? <>tinyshop HEAD <Chip>{brain.head}</Chip></> : brain.connected ? null : "brain offline"}
        </span>
        {onClose && (
          <button type="button" className="bc-icon-btn" onClick={onClose} aria-label="Close evidence">
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" /></svg>
          </button>
        )}
      </header>
      {steps.length === 0 ? (
        <p className="bc-evidence__empty">
          {brain.connected
            ? <>Nothing yet. Ask the files something and every step the brain runs shows up here as it happens.</>
            : <>Can't reach the brain at its event stream. Start it with <code>uvicorn server:app --port 8787</code> in brain/.</>}
        </p>
      ) : (
        <ol className="bc-evidence__list" ref={list} aria-live="polite">
          {steps.map((e) => {
            const row = describe(e);
            return (
              <li key={e.seq} className="bc-ev" data-kind={e.kind}>
                <time className="bc-ev__time">{e.ts}</time>
                <Glyph name={row.icon} />
                <div className="bc-ev__body">
                  <span className="bc-ev__label">{row.label}</span>
                  {row.facts && <span className="bc-ev__facts">{row.facts}</span>}
                  {row.note && <span className="bc-ev__note">{row.note}</span>}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </aside>
  );
}
