const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type RealtimeEvent = {
  type: string;
  channel?: string;
  message?: ChatLiveMessage;
  message_id?: string;
  user?: { id: string; display_name: string };
  user_ids?: string[];
  code?: number;
};

export type ChatLiveMessage = {
  id: string;
  channel_id: string;
  author_id: string;
  body: string;
  created_at: string;
  author?: { id: string; display_name: string; email: string; role_key: string; avatar_url?: string | null } | null;
};

type Handler = (event: RealtimeEvent) => void;

let socket: WebSocket | null = null;
let handlers = new Set<Handler>();
let wanted = new Set<string>();
let pingTimer: number | null = null;

function wsUrl() {
  return API.replace(/^http/, "ws") + "/api/v1/chat/ws";
}

function open() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return socket;
  }
  socket = new WebSocket(wsUrl());
  socket.onopen = () => {
    wanted.forEach((ch) => socket?.send(JSON.stringify({ type: "subscribe", channel: ch })));
    if (pingTimer) window.clearInterval(pingTimer);
    pingTimer = window.setInterval(() => {
      if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "ping" }));
    }, 20000);
  };
  socket.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data) as RealtimeEvent;
      handlers.forEach((h) => h(data));
    } catch {
      /* ignore */
    }
  };
  socket.onclose = () => {
    socket = null;
    if (pingTimer) window.clearInterval(pingTimer);
    pingTimer = null;
    if (handlers.size) window.setTimeout(open, 1500);
  };
  return socket;
}

export function subscribeRealtime(channel: string, handler: Handler) {
  wanted.add(channel);
  handlers.add(handler);
  const ws = open();
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "subscribe", channel }));
  }
  return () => {
    handlers.delete(handler);
    wanted.delete(channel);
    if (!handlers.size && socket) {
      socket.close();
      socket = null;
    }
  };
}

export function sendTyping(channel: string) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "typing", channel }));
  }
}

export function sendHeartbeat(channel: string) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "heartbeat", channel }));
  }
}
