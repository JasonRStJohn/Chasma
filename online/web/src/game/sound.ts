/**
 * Procedural Web Audio API Waveform Synthesizer for Chasma Online.
 * Exact browser port of `chasma/systems/sound.py` — zero external audio assets required.
 */

export type SoundName =
  | "fire"
  | "hit"
  | "death"
  | "bounce"
  | "menu_select"
  | "game_over"
  | "win"
  | "suck";

export class WebSoundManager {
  private ctx: AudioContext | null = null;
  public enabled: boolean = true;

  constructor() {
    const saved = localStorage.getItem("chasma_sound_enabled");
    if (saved !== null) {
      this.enabled = saved === "true";
    }
  }

  public unlock(): void {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
  }

  public toggleMute(): boolean {
    this.enabled = !this.enabled;
    localStorage.setItem("chasma_sound_enabled", String(this.enabled));
    return this.enabled;
  }

  public play(name: SoundName | string): void {
    if (!this.enabled) return;
    this.unlock();
    if (!this.ctx || this.ctx.state !== "running") return;

    switch (name) {
      case "fire":
        // Square wave, 880 Hz, 0.08s, LinearDecay(peak=0.3)
        this.playOscillator("square", 880, 0.08, { type: "linear", peak: 0.25 });
        break;
      case "hit":
        // Square wave, 220 Hz, 0.12s, LinearDecay(peak=0.4)
        this.playOscillator("square", 220, 0.12, { type: "linear", peak: 0.32 });
        break;
      case "death":
        // WhiteNoise, 0.4s, LinearDecay(peak=0.35)
        this.playWhiteNoise(0.4, 0.3);
        break;
      case "bounce":
        // Triangle, 600 Hz, 0.03s, LinearDecay(peak=0.15)
        this.playOscillator("triangle", 600, 0.03, { type: "linear", peak: 0.15 });
        break;
      case "menu_select":
        // Sine, 1200 Hz, 0.1s, ADSR(attack=0.01, decay=0.05, release=0.04, sustain=0.3)
        this.playOscillator("sine", 1200, 0.1, {
          type: "adsr",
          attack: 0.01,
          decay: 0.05,
          sustain: 0.25,
          release: 0.04,
          peak: 0.35,
        });
        break;
      case "game_over":
        // Sawtooth, 110 Hz, 0.8s, LinearDecay(peak=0.3)
        this.playOscillator("sawtooth", 110, 0.8, { type: "linear", peak: 0.25 });
        break;
      case "win":
        // Sine, 880 Hz, 0.3s, ADSR(attack=0.02, decay=0.1, release=0.15, sustain=0.3)
        this.playOscillator("sine", 880, 0.3, {
          type: "adsr",
          attack: 0.02,
          decay: 0.1,
          sustain: 0.25,
          release: 0.15,
          peak: 0.35,
        });
        break;
      case "suck":
        // Sine, 90 Hz, 0.6s, ADSR(attack=0.05, decay=0.2, release=0.3, sustain=0.25)
        this.playOscillator("sine", 90, 0.6, {
          type: "adsr",
          attack: 0.05,
          decay: 0.2,
          sustain: 0.22,
          release: 0.3,
          peak: 0.3,
        });
        break;
    }
  }

  private playOscillator(
    type: OscillatorType,
    frequency: number,
    duration: number,
    env:
      | { type: "linear"; peak: number }
      | { type: "adsr"; attack: number; decay: number; sustain: number; release: number; peak: number }
  ): void {
    if (!this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(frequency, now);

    if (env.type === "linear") {
      gain.gain.setValueAtTime(env.peak, now);
      gain.gain.linearRampToValueAtTime(0.0001, now + duration);
    } else {
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.linearRampToValueAtTime(env.peak, now + env.attack);
      gain.gain.linearRampToValueAtTime(env.sustain, now + env.attack + env.decay);
      const releaseStart = Math.max(now + env.attack + env.decay, now + duration - env.release);
      gain.gain.setValueAtTime(env.sustain, releaseStart);
      gain.gain.linearRampToValueAtTime(0.0001, now + duration);
    }

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(now);
    osc.stop(now + duration + 0.01);
  }

  private playWhiteNoise(duration: number, peak: number): void {
    if (!this.ctx) return;
    const now = this.ctx.currentTime;
    const bufferSize = Math.floor(this.ctx.sampleRate * duration);
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(peak, now);
    gain.gain.linearRampToValueAtTime(0.0001, now + duration);

    noise.connect(gain);
    gain.connect(this.ctx.destination);

    noise.start(now);
    noise.stop(now + duration + 0.01);
  }
}
