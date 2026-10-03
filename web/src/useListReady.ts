import { useEffect, useSyncExternalStore } from "react";
import { CometChat } from "@cometchat/chat-sdk-javascript";

// UI Kit 7.2.3 race (chunk-DOHC2DJR.js, useMessageListInit + the "connection/connected" case):
// the list's first load runs `initialize()` with a captured `gen`. If the WebSocket connects while
// that load is still in flight, the connected handler sees zero messages, bumps generationRef,
// RESETs and calls initializeRef.current(), which is the same closure, still holding the old
// `gen`. Both the original load and the "retry" then fail their `generationRef.current !== gen`
// check and return, so the list stays empty with no error. Mounting the list only once the socket
// is connected means that handler can't fire mid-load. No timers: this is driven by the SDK's own
// connection status and listener.
const LISTENER_ID = "blamechat-socket-status";

function subscribe(onChange: () => void) {
  CometChat.addConnectionListener(LISTENER_ID, new CometChat.ConnectionListener({
    onConnected: onChange,
    onDisconnected: onChange,
  }));
  return () => CometChat.removeConnectionListener(LISTENER_ID);
}

const connected = () => CometChat.getConnectionStatus() === CometChat.CONNECTION_STATUS.CONNECTED;

export function useListReady(): boolean {
  // Once mounted, the list stays mounted: later reconnects take the kit's own catch-up path,
  // which is safe because by then it has messages.
  return useSyncExternalStore(subscribe, connected);
}

// The kit scrolls to the newest message once on load; with a short history its top sentinel is
// visible, it tries to load older messages and restores scroll by the height difference, leaving
// the newest messages (the confession) below the fold. Pin the list to the bottom whenever its
// content grows, until the viewer scrolls or types themselves. Event-driven (Mutation/Resize
// observers), no timers.
export function useStartAtNewest(mounted: boolean) {
  useEffect(() => {
    if (!mounted) return;
    let list: HTMLElement | null = null;
    let resize: ResizeObserver | undefined;
    const stop = () => {
      resize?.disconnect();
      mutation.disconnect();
      for (const e of ["wheel", "touchstart", "keydown", "pointerdown"]) list?.removeEventListener(e, stop);
    };
    const attach = () => {
      list = document.querySelector<HTMLElement>(".cometchat-message-list__scroll-container");
      const messages = list?.querySelector(".cometchat-message-list__messages");
      if (!list || !messages) return false;
      const el = list;
      resize = new ResizeObserver(() => { el.scrollTop = el.scrollHeight; });
      resize.observe(messages);
      for (const e of ["wheel", "touchstart", "keydown", "pointerdown"]) el.addEventListener(e, stop, { passive: true });
      return true;
    };
    const mutation = new MutationObserver(() => { if (attach()) mutation.disconnect(); });
    if (!attach()) mutation.observe(document.body, { childList: true, subtree: true });
    return stop;
  }, [mounted]);
}
