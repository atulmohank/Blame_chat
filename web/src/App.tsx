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
    <CometChatProvider theme="dark" plugins={PLUGINS}>
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
          trailingView={<TestPill status={tests} />}
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
  );
}
