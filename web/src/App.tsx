import { useEffect, useState } from "react";
import { CometChat } from "@cometchat/chat-sdk-javascript";
import {
  CometChatProvider,
  CometChatMessageHeader,
  CometChatMessageList,
  CometChatMessageComposer,
} from "@cometchat/chat-uikit-react";
import { BRAIN_URL } from "./config";

export default function App() {
  const [group, setGroup] = useState<CometChat.Group>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${BRAIN_URL}/session`);
        const { guid } = await res.json();
        if (!guid) throw new Error("brain has no group yet: run `python reset_take.py`");
        setGroup(await CometChat.getGroup(guid));
      } catch (e) {
        setError(String((e as Error)?.message ?? e));
      }
    })();
  }, []);

  // Plan B trigger: the composer only fires this for MY sends, never for bot messages.
  const onSend = (message: CometChat.BaseMessage, mode?: "send" | "edit") => {
    if (mode === "edit" || !group) return;
    const text = (message as CometChat.TextMessage).getText?.() ?? "";
    if (!text.trim()) return;
    fetch(`${BRAIN_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, guid: group.getGuid() }),
    }).catch((e) => console.error("/ask failed", e));
  };

  if (error) return <pre style={{ padding: 24 }}>{error}</pre>;
  if (!group) return <div style={{ padding: 24 }}>Loading BlameChat…</div>;

  return (
    <CometChatProvider>
      <div className="chat">
        <CometChatMessageHeader group={group} />
        <CometChatMessageList group={group} />
        <CometChatMessageComposer group={group} onSendButtonClick={onSend} hideVoiceRecordingButton hideStickersButton />
      </div>
    </CometChatProvider>
  );
}
