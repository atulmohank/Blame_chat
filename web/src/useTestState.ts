import { useCallback, useEffect, useState } from "react";
import { CometChat } from "@cometchat/chat-sdk-javascript";
import { BRAIN_URL, MY_UID } from "./config";

export type TestState = "unknown" | "failing" | "passing";
export type TestStatus = {
  state: TestState;
  failed: number | null;
  passed: number | null;
  failing_test: string | null;
  head: string | null;
  checked_at: string | null;
};

const UNKNOWN: TestStatus = { state: "unknown", failed: null, passed: null, failing_test: null, head: null, checked_at: null };

// The brain caches its last pytest result (startup, /ask, /commit); GET /status only reads that
// cache. The pill asks once on load and again whenever a file posts, because the brain updates the
// cache before it posts. No polling, and nothing here can make the brain run pytest.
export function useTestState(guid: string): TestStatus {
  const [status, setStatus] = useState<TestStatus>(UNKNOWN);

  const refresh = useCallback(() => {
    fetch(`${BRAIN_URL}/status`)
      .then((r) => r.json())
      .then((s: TestStatus) => setStatus({ ...UNKNOWN, ...s }))
      .catch((e) => console.error("GET /status failed", e));
  }, []);

  useEffect(() => {
    refresh();
    const listenerId = `blamechat-tests-${guid}`;
    CometChat.addMessageListener(listenerId, new CometChat.MessageListener({
      onTextMessageReceived: (message: CometChat.TextMessage) => {
        if (message.getReceiverId() === guid && message.getSender()?.getUid() !== MY_UID) refresh();
      },
    }));
    return () => CometChat.removeMessageListener(listenerId);
  }, [guid, refresh]);

  return status;
}
