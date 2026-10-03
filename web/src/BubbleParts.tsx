import type { ReactNode } from "react";
import type { FileIdentity } from "./files";
import type { Confession } from "./confession";

export function FileBadge({ file }: { file: FileIdentity }) {
  return (
    <span className="bc-badge" data-hue={file.slot} aria-hidden="true">
      <span className="bc-badge__mono">{file.monogram}</span>
      <span className="bc-badge__ext">.{file.ext}</span>
    </span>
  );
}

export function Receipt({ confession, children }: { confession: Confession; children: ReactNode }) {
  const { file, line, fragment, commit, failingTest, evidence } = confession;
  return (
    <div className="bc-confession">
      {children}
      <figure className="bc-receipt" aria-label={`Evidence: ${file}${line ? ` line ${line}` : ""}, commit ${commit}`}>
        <figcaption className="bc-receipt__head">
          <span className="bc-receipt__loc">{line ? `${file}:${line}` : file}</span>
          <span className="bc-receipt__commit">{commit}</span>
        </figcaption>
        {fragment && (
          <div className="bc-receipt__diff">
            <span className="bc-receipt__lineno" aria-hidden="true">{line}</span>
            <span className="bc-receipt__sign" aria-hidden="true">−</span>
            <code className="bc-receipt__code">
              {/* Narrow screens may break a call chain only before a ".", never inside a token. */}
              {fragment.split(/(?=\.)/).map((part, i) => (
                <span key={i}>{i > 0 && <wbr />}{part}</span>
              ))}
            </code>
          </div>
        )}
        {(evidence.length > 0 || failingTest) && (
          <p className="bc-receipt__source">
            {evidence.length > 0 && <>found by {evidence.map((e) => <span key={e} className="bc-chip">{e}</span>)}</>}
            {failingTest && <span className="bc-receipt__test">{failingTest}</span>}
          </p>
        )}
      </figure>
    </div>
  );
}

const clock = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });

export function MessageTime({ sentAt }: { sentAt: number }) {
  if (!sentAt) return null;
  const at = new Date(sentAt * 1000);
  return <time className="bc-time" dateTime={at.toISOString()}>{clock.format(at)}</time>;
}
