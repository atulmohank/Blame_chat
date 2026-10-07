import { useEffect, useState } from "react";
import { CometChat } from "@cometchat/chat-sdk-javascript";
import {
  CometChatProvider,
  CometChatMessageHeader,
  CometChatMessageList,
  CometChatMessageComposer,
} from "@cometchat/chat-uikit-react";
import { BRAIN_URL } from "./config";
import { BlameTextPlugin } from "./BlamePlugin";
import { Mark, TestPill, Title } from "./Header";
import { useTestState } from "./useTestState";
import { useListReady, useStartAtNewest } from "./useListReady";
import { LiveDelivery } from "./LiveDelivery";
import { Evidence } from "./Evidence";
import { Room } from "./Room";

const PLUGINS = [BlameTextPlugin];

export default function App() {
  const [group, setGroup] = useState<CometChat.Group>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${BRAIN_URL}/session`);
        const { guid } = await res.json();
        if (!guid) throw new Error("The brain has no group yet. Run `python reset_take.py` in brain/, then reload.");
        setGroup(await CometChat.getGroup(guid));
      } catch (e) {
        setError(String((e as Error)?.message ?? e));
      }
    })();
  }, []);

  if (error) return <Status title="BlameChat can't reach the brain" detail={error} />;
  if (!group) return <Status title="Loading the repo chat…" />;
  return <Chat group={group} />;
}

export function Status({ title, detail }: { title: string; detail?: string }) {
  return (
    <main className="bc-status">
      <h1>{title}</h1>
      {detail && <pre>{detail}</pre>}
    </main>
  );
}

function Chat({ group }: { group: CometChat.Group }) {
  const tests = useTestState(group.getGuid());
  const listReady = useListReady();
  useStartAtNewest(listReady);
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  useEffect(() => {
    if (!evidenceOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setEvidenceOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [evidenceOpen]);

  // Plan B trigger: the composer only fires this for MY sends, never for bot messages.
  const onSend = (message: CometChat.BaseMessage, mode?: "send" | "edit") => {
    if (mode === "edit") return;
    const text = (message as CometChat.TextMessage).getText?.() ?? "";
    if (!text.trim()) return;
    fetch(`${BRAIN_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, guid: group.getGuid() }),
    }).catch((e) => console.error("/ask failed", e));
  };

  return (
    <div className="bc-shell" data-evidence-open={evidenceOpen || undefined}>
      <Room guid={group.getGuid()} online={listReady} />
      <CometChatProvider theme="dark" plugins={PLUGINS}>
        <LiveDelivery guid={group.getGuid()} />
        <div className="chat">
          <CometChatMessageHeader
            group={group}
            hideBackButton
            showSearchOption={false}
            hideVoiceCallButton
            hideVideoCallButton
            leadingView={<Mark />}
            titleView={<Title group={group} />}
            subtitleView={<></>}
            trailingView={
              <span className="bc-header-end">
                <TestPill status={tests} />
                <EvidenceToggle open={evidenceOpen} controls={EVIDENCE_ID} onToggle={() => setEvidenceOpen((o) => !o)} />
              </span>
            }
          />
          {listReady ? (
            <CometChatMessageList
              group={group}
              hideGroupActionMessages
              hideReceipts
              hideStickyDate
              hideDateSeparator
            />
          ) : (
            <div className="bc-list-pending" role="status">Connecting to CometChat…</div>
          )}
          <CometChatMessageComposer
            group={group}
            onSendButtonClick={onSend}
            placeholder="Ask the files… e.g. who broke login?"
            hideAttachmentButton
            hideEmojiKeyboardButton
            hideVoiceRecordingButton
            hideStickersButton
            hideLiveReaction
          />
        </div>
      </CometChatProvider>
      <Evidence id={EVIDENCE_ID} onClose={evidenceOpen ? () => setEvidenceOpen(false) : undefined} />
    </div>
  );
}

const EVIDENCE_ID = "bc-evidence";

// Below 760px the Evidence panel becomes a drawer; this button (hidden on wider screens) opens it.
function EvidenceToggle({ open, controls, onToggle }: { open: boolean; controls: string; onToggle: () => void }) {
  return (
    <button type="button" className="bc-evidence-toggle" aria-expanded={open} aria-controls={controls} onClick={onToggle}>
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3 3.5h10M3 8h10M3 12.5h6" /></svg>
      Evidence
    </button>
  );
}
