import { useEffect, useState } from "react";
import { CometChat } from "@cometchat/chat-sdk-javascript";
import { useBrain, type RoomMember } from "./brainEvents";
import { fileIdentity, type FileIdentity } from "./files";
import { FileBadge } from "./BubbleParts";
import { MY_UID } from "./config";

// Read-only roster: the real CometChat group members, each file with its part in the current
// failure. Statuses come only from the brain's "room" event (derived from find_culprit's facts).

type Member = { uid: string; name: string; file?: FileIdentity };

function useGroupMembers(guid: string) {
  const [members, setMembers] = useState<Member[]>([]);
  useEffect(() => {
    let live = true;
    new CometChat.GroupMembersRequestBuilder(guid).setLimit(30).build().fetchNext()
      .then((list) => {
        if (!live) return;
        const all = list.map((m) => ({ uid: m.getUid(), name: m.getName(), file: fileIdentity(m.getUid(), m.getName()) }));
        // You first, then the files in their gutter order.
        all.sort((a, b) => (a.uid === MY_UID ? -1 : b.uid === MY_UID ? 1 : (a.file?.slot ?? 9) - (b.file?.slot ?? 9)));
        setMembers(all);
      })
      .catch((e) => console.error("group members not fetched", e));
    return () => { live = false; };
  }, [guid]);
  return members;
}

function Check() {
  return <svg className="bc-room__check" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" /></svg>;
}

function statusText(s: RoomMember | undefined) {
  if (!s || s.status === "unknown") return { text: "not checked yet", tone: "quiet" as const };
  switch (s.status) {
    case "culprit": return { text: s.line ? `culprit · L${s.line}` : "culprit", tone: "red" as const };
    case "changed-not-run": return { text: "changed, never ran", tone: "plain" as const };
    case "ran": return { text: "ran in test", tone: "plain" as const };
    case "bystander": return { text: "bystander", tone: "quiet" as const };
    case "green": return { text: "green", tone: "green" as const };
  }
}

export function Room({ guid, online }: { guid: string; online: boolean }) {
  const members = useGroupMembers(guid);
  const { room } = useBrain();
  const byFile = new Map((room ?? []).map((m) => [m.file, m]));

  return (
    <aside className="bc-panel bc-room" aria-label="In the room">
      <header className="bc-panel__head">
        <h2 className="bc-panel__title">In the room</h2>
        {members.length > 0 && <span className="bc-room__count">{members.length}</span>}
      </header>
      <ul className="bc-room__list">
        {members.map((m) => {
          if (!m.file) {
            const label = m.uid === MY_UID ? `you, ${online ? "online" : "connecting"}` : "member";
            return (
              <li key={m.uid} className="bc-room__member" title={`${m.uid} (${label})`}>
                <span className="bc-badge bc-badge--human" aria-hidden="true">
                  <span className="bc-badge__mono">{m.uid.slice(0, 2)}</span>
                  {m.uid === MY_UID && <span className="bc-room__presence" data-online={online} />}
                </span>
                <span className="bc-room__text">
                  <span className="bc-room__name">{m.uid}</span>
                  <span className="bc-room__status" data-tone="quiet">{label}</span>
                </span>
              </li>
            );
          }
          const s = statusText(byFile.get(m.file.name));
          return (
            <li key={m.uid} className="bc-room__member" data-hue={m.file.slot} data-tone={s.tone} title={`${m.file.name}: ${s.text}`}>
              <span className="bc-room__badge">
                <FileBadge file={m.file} />
                {(s.tone === "red" || s.tone === "green") && <span className="bc-room__mark" data-tone={s.tone} />}
              </span>
              <span className="bc-room__text">
                <span className="bc-room__name">{m.file.name}</span>
                <span className="bc-room__status" data-tone={s.tone}>
                  {s.tone === "green" && <Check />}{s.text}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
