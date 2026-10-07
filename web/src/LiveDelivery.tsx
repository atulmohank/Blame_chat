import { useEffect, useRef } from "react";
import { CometChat } from "@cometchat/chat-sdk-javascript";
import { usePublishEvent } from "@cometchat/chat-uikit-react";
import { onBrainEvent } from "./brainEvents";

// Fallback for CometChat not pushing REST-posted (onBehalfOf) messages over the WebSocket: they
// are stored, but no message frame arrives. The brain announces every post on /events with the
// CometChat message id; we fetch that exact message and hand it to the kit's own event bus as
// "message/text-received", the event the kit's socket listener emits. The message list then runs
// its normal received path (MESSAGE_RECEIVED), which matches by message id: if CometChat's push
// starts working again, the same message replaces itself in place instead of showing twice.
//
// Must render inside CometChatProvider (it owns the event bus).

type ReceivedEvent = { type: "message/text-received"; message: CometChat.TextMessage };

export function LiveDelivery({ guid }: { guid: string }) {
  // usePublishEvent is typed for the kit's ui:* events; the bus itself carries SDK events too.
  const publish = usePublishEvent() as unknown as (event: ReceivedEvent) => void;
  const seen = useRef(new Set<string>());
  const chain = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => onBrainEvent(({ event, replay, firstConnection }) => {
    if (event.kind !== "posted" || event.refs.guid !== guid || event.refs.id == null) return;
    // The first replay is already in the list's history fetch; after a reconnect, replay catches up.
    if (replay && firstConnection) return;
    const id = String(event.refs.id);
    if (seen.current.has(id)) return;
    seen.current.add(id);
    // One at a time, so messages land in the order the brain posted them.
    chain.current = chain.current.then(() =>
      CometChat.getMessageDetails(id)
        .then((message) => publish({ type: "message/text-received", message: message as CometChat.TextMessage }))
        .catch((e) => {
          seen.current.delete(id);
          console.error(`live delivery: message ${id} not fetched`, e);
        }),
    );
  }), [guid, publish]);

  return null;
}
