/**
 * WebSocket Client for Chasma Online.
 * Connects to `/ws/{roomCode}`, streams 60Hz inputs, and dispatches state snapshots & sound events.
 */

import { TuningConfig } from "../config/generated_config";
import { LocalInputState } from "../game/input";
import { ServerStatePacket } from "../game/prediction";

export interface WelcomePacket {
  t: "welcome";
  room: string;
  slot: number;
  tuning: Partial<TuningConfig>;
}

export class ChasmaSocketClient {
  private ws: WebSocket | null = null;
  private pingTimer: number | null = null;
  public connected: boolean = false;
  public pingMs: number = 0;

  constructor(
    private callbacks: {
      onWelcome: (pkt: WelcomePacket) => void;
      onState: (pkt: ServerStatePacket) => void;
      onDisconnect: () => void;
    }
  ) {}

  public connect(roomCode: string, callsign: string): void {
    this.disconnect();

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const cleanCode = encodeURIComponent(roomCode.trim().toUpperCase());
    const cleanName = encodeURIComponent(callsign.trim().slice(0, 12));
    const url = `${proto}//${window.location.host}/ws/${cleanCode}?name=${cleanName}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.connected = true;
      this.startPingLoop();
    };

    this.ws.onmessage = (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.t === "welcome") {
          this.callbacks.onWelcome(data as WelcomePacket);
        } else if (data.t === "s") {
          this.callbacks.onState(data as ServerStatePacket);
        } else if (data.t === "pong") {
          this.pingMs = Math.max(0, Math.round(performance.now() - Number(data.ts)));
        }
      } catch {
        // Ignore malformed packets
      }
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.stopPingLoop();
      this.callbacks.onDisconnect();
    };
  }

  public sendInput(seq: number, input: LocalInputState): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(
      JSON.stringify({
        t: "i",
        seq,
        rot: Number(input.rotation.toFixed(2)),
        thr: Number(input.thrust.toFixed(2)),
        fire: input.fire ? 1 : 0,
      })
    );
  }

  public sendCommand(action: string, extra?: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ t: "cmd", action, ...extra }));
  }

  public disconnect(): void {
    this.stopPingLoop();
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }

  private startPingLoop(): void {
    this.stopPingLoop();
    this.pingTimer = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ t: "cmd", action: "ping", ts: performance.now() }));
      }
    }, 2000);
  }

  private stopPingLoop(): void {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
}
