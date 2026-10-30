import type { Event } from '../types';

export interface WebSocketMessage {
  type: string;
  action?: string;
  event?: Event;
  message?: string;
}

type EventCallback = (event: Event, action: string) => void;
type StatusCallback = (connected: boolean) => void;

class RealtimeWebSocketService {
  private socket: WebSocket | null = null;
  private eventCallbacks: Set<EventCallback> = new Set();
  private statusCallbacks: Set<StatusCallback> = new Set();
  private pingInterval: any = null;
  private reconnectTimeout: any = null;
  private isExplicitlyClosed = false;
  private reconnectAttempts = 0;
  private readonly minReconnectDelayMs = 2000; // 2s initial delay
  private readonly maxReconnectDelayMs = 30000; // 30s ceiling

  private getWebSocketUrl(): string {
    const wsEnv = (
      import.meta.env.VITE_WS_URL ||
      import.meta.env.VITE_API_URL ||
      'wss://threatatlas-backend.onrender.com'
    ).trim();

    let formatted = wsEnv.replace(/\/+$/, '');
    if (formatted.startsWith('http://')) {
      formatted = 'ws://' + formatted.slice(7);
    } else if (formatted.startsWith('https://')) {
      formatted = 'wss://' + formatted.slice(8);
    } else if (!formatted.startsWith('ws://') && !formatted.startsWith('wss://')) {
      const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
      formatted = `${isSecure ? 'wss' : 'ws'}://${formatted}`;
    }

    if (!formatted.includes('/api/v1/ws/events')) {
      formatted = formatted.replace(/\/api\/v1\/?$/, '');
      return `${formatted}/api/v1/ws/events`;
    }
    return formatted;
  }

  public connect(): void {
    this.isExplicitlyClosed = false;
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const url = this.getWebSocketUrl();
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log('[WebSocket] Real-time event stream connected.');
        this.reconnectAttempts = 0;
        this.notifyStatus(true);
        this.startHeartbeat();
      };

      this.socket.onmessage = (msg: MessageEvent) => {
        try {
          const data: WebSocketMessage = JSON.parse(msg.data);
          const type = (data.type || '').toUpperCase();
          if (type.startsWith('EVENT_') || data.event) {
            const rawEvent = data.event;
            if (rawEvent) {
              const normalizedEvent: Event = {
                ...rawEvent,
                id: String(rawEvent.id || (rawEvent as any)._id || ''),
              };
              const action = data.action || (type === 'EVENT_CREATED' ? 'created' : 'updated');
              this.notifyEvent(normalizedEvent, action);
            }
          }
        } catch (err) {
          console.warn('[WebSocket] Error parsing message:', err);
        }
      };

      this.socket.onerror = (err) => {
        console.warn('[WebSocket] Real-time stream error:', err);
      };

      this.socket.onclose = () => {
        console.log('[WebSocket] Real-time stream disconnected.');
        this.notifyStatus(false);
        this.stopHeartbeat();

        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect();
        }
      };
    } catch (err) {
      console.warn('[WebSocket] Failed to initialize WebSocket connection:', err);
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.reconnectAttempts = 0;
    this.stopHeartbeat();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.notifyStatus(false);
  }

  public subscribe(onEvent: EventCallback, onStatus?: StatusCallback): () => void {
    this.eventCallbacks.add(onEvent);
    if (onStatus) this.statusCallbacks.add(onStatus);

    // Auto-connect on first subscriber
    if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
      this.connect();
    }

    return () => {
      this.eventCallbacks.delete(onEvent);
      if (onStatus) this.statusCallbacks.delete(onStatus);
    };
  }

  private notifyEvent(event: Event, action: string): void {
    this.eventCallbacks.forEach((cb) => cb(event, action));
  }

  private notifyStatus(connected: boolean): void {
    this.statusCallbacks.forEach((cb) => cb(connected));
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send('ping');
      }
    }, 15000);
  }

  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout || this.isExplicitlyClosed) return;

    // Exponential backoff: min(maxDelay, minDelay * 2^attempts) e.g. 2s, 4s, 8s, 16s, up to 30s
    const delay = Math.min(
      this.maxReconnectDelayMs,
      this.minReconnectDelayMs * Math.pow(2, this.reconnectAttempts)
    );
    this.reconnectAttempts += 1;

    console.log(`[WebSocket] Scheduling reconnect attempt #${this.reconnectAttempts} in ${delay}ms...`);
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      console.log('[WebSocket] Reconnecting to real-time event stream...');
      this.connect();
    }, delay);
  }
}

export const wsService = new RealtimeWebSocketService();
