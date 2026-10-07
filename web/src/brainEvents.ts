import { useSyncExternalStore } from "react";
import { BRAIN_URL } from "./config";

// The brain's step stream (GET /events, Server-Sent Events). One EventSource for the page; the
// browser's own EventSource reconnect handles a restarted brain. Push only, no polling.
// Each connection starts with "hello" (take, tinyshop HEAD), replays this take's history, then
// sends "replayed"; everything after that marker is live.

export type BrainEvent = {
  seq: number;
  ts: string; // HH:MM:SS, the same stamp as the brain's terminal log line
  take: number | null;
  kind: string;
  text: string;
  refs: Record<string, any>;
};

export type RoomStatus = "culprit" | "changed-not-run" | "ran" | "bystander" | "green" | "unknown";
export type RoomMember = { file: string; status: RoomStatus; line?: number | null; commit?: string | null };

export type BrainState = {
  connected: boolean;
  replayed: boolean;
  take: number | null;
  head: string | null;
  events: BrainEvent[];
  room: RoomMember[] | null;
};

/** replay: the event came from the history replay, not live. firstConnection: this page's first replay. */
export type BrainEventInfo = { event: BrainEvent; replay: boolean; firstConnection: boolean };

let state: BrainState = { connected: false, replayed: false, take: null, head: null, events: [], room: null };
let source: EventSource | null = null;
let connections = 0;
const viewers = new Set<() => void>();
const handlers = new Set<(info: BrainEventInfo) => void>();

function set(next: Partial<BrainState>) {
  state = { ...state, ...next };
  viewers.forEach((v) => v());
}

function apply(event: BrainEvent) {
  // A new take (reset_take.py) starts from an empty panel.
  const fresh = state.take !== null && event.take !== null && event.take !== state.take;
  const events = fresh ? [event] : [...state.events, event];
  const next: Partial<BrainState> = { events, take: event.take ?? state.take };
  if (fresh) next.room = null;
  if (event.kind === "room") next.room = event.refs.members;
  if (event.kind === "commit" && event.refs.commit) next.head = event.refs.commit;
  set(next);
}

function open() {
  if (source) return;
  source = new EventSource(`${BRAIN_URL}/events`);
  source.addEventListener("hello", (m) => {
    const hello = JSON.parse((m as MessageEvent).data);
    connections += 1;
    // The brain replays its whole history after every hello, so rebuild from it.
    set({ connected: true, replayed: false, take: hello.take, head: hello.head, events: [], room: null });
  });
  source.addEventListener("replayed", () => set({ replayed: true }));
  source.onmessage = (m) => {
    const event: BrainEvent = { ...JSON.parse(m.data), seq: Number(m.lastEventId) };
    const replay = !state.replayed;
    apply(event);
    const info = { event, replay, firstConnection: connections === 1 };
    handlers.forEach((h) => h(info));
  };
  source.onerror = () => set({ connected: false });
}

function subscribe(onChange: () => void) {
  open();
  viewers.add(onChange);
  return () => viewers.delete(onChange);
}

export function useBrain(): BrainState {
  return useSyncExternalStore(subscribe, () => state);
}

/** Called for every event, replayed or live. Returns an unsubscribe function. */
export function onBrainEvent(handler: (info: BrainEventInfo) => void) {
  open();
  handlers.add(handler);
  return () => {
    handlers.delete(handler);
  };
}
