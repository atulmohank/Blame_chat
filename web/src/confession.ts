// The confession's facts. Source of truth: the metadata the brain attaches to the culprit's message
// (brain/server.py confession_metadata, computed by ground.py from pytest + git). Messages posted
// before the brain sent metadata fall back to the confession text itself; only the culprit may write
// a line number, code and a commit hash (brain/validator.py). Nothing here is hardcoded.
export type Confession = {
  file: string;
  line: number | null;
  fragment: string | null;
  commit: string;
  failingTest: string | null;
  evidence: string[]; // how the brain found it, e.g. ["pytest trace", "git diff", "git blame"]
};

type Meta = {
  blamechat?: {
    kind?: string; file?: string; line?: number | null; fragment?: string | null;
    commit?: string; failing_test?: string | null; evidence?: string[];
  };
};

const CONFESSION = /`([^`\s]+)`\s+L(\d+)\s+`([^`]+)`[\s\S]*?commit\s+`([0-9a-f]{7,40})`/;

export function confessionOf(message: CometChat.TextMessage): Confession | undefined {
  const meta = (message.getMetadata?.() as Meta | undefined)?.blamechat;
  if (meta?.kind === "confession" && meta.file && meta.commit) {
    return {
      file: meta.file,
      line: meta.line ?? null,
      fragment: meta.fragment ?? null,
      commit: meta.commit,
      failingTest: meta.failing_test ?? null,
      evidence: meta.evidence ?? [],
    };
  }
  const m = CONFESSION.exec(message.getText?.() ?? "");
  return m
    ? { file: m[1], line: Number(m[2]), fragment: m[3], commit: m[4], failingTest: null, evidence: [] }
    : undefined;
}
