/**
 * Client-Side Prediction, Server Reconciliation, and Snapshot Interpolation.
 * Ensures 0ms local input feel and smooth 60 FPS remote entity motion.
 */

import { CHASMA_CONFIG, TuningConfig } from "../config/generated_config";
import { LocalInputState } from "./input";

export interface RenderPlayer {
  slot: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  angle: number;
  thrust: number;
  lives: number;
  alive: boolean;
  spiraling: boolean;
  isAi: boolean;
  name: string;
}

export interface RenderProjectile {
  id: number;
  ownerSlot: number;
  x: number;
  y: number;
  angle: number;
}

export interface RenderHollowstar {
  x: number;
  y: number;
  spinAngle: number;
}

export interface RenderWorldState {
  tick: number;
  phase: string;
  countdown: number;
  winner: number | null;
  hollowstar: RenderHollowstar;
  players: RenderPlayer[];
  projectiles: RenderProjectile[];
}

export interface ServerStatePacket {
  t: "s";
  tick: number;
  ack: number;
  phase: string;
  cd: number;
  winner: number | null;
  hs: [number, number, number];
  p: [
    number, // 0: slot
    number, // 1: x
    number, // 2: y
    number, // 3: vx
    number, // 4: vy
    number, // 5: angle
    number, // 6: thrust
    number, // 7: lives
    number, // 8: alive (0|1)
    number, // 9: spiraling (0|1)
    number, // 10: is_ai (0|1)
    string  // 11: name
  ][];
  proj: [number, number, number, number, number][];
  ev: string[];
}

interface BufferedSnapshot {
  timestamp: number;
  state: RenderWorldState;
}

interface PendingInput {
  seq: number;
  input: LocalInputState;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpAngleDeg(a: number, b: number, t: number): number {
  const diff = (((b - a) % 360) + 540) % 360 - 180;
  return (a + diff * t + 360) % 360;
}

export class WorldStatePredictor {
  public mySlot: number = -1;
  public tuning: TuningConfig = { ...CHASMA_CONFIG.tuning };

  private snapshots: BufferedSnapshot[] = [];
  private pendingInputs: PendingInput[] = [];
  private seqCounter: number = 0;

  // Predicted local player state + visual smoothing error offset
  private predictedLocal: RenderPlayer | null = null;
  private visualErrorX: number = 0;
  private visualErrorY: number = 0;

  // Interpolation delay (45ms ~ 2.7 ticks at 60Hz)
  private readonly interpDelayMs = 45;

  public reset(slot: number, serverTuning?: Partial<TuningConfig>): void {
    this.mySlot = slot;
    if (serverTuning) {
      this.tuning = { ...this.tuning, ...serverTuning };
    }
    this.snapshots = [];
    this.pendingInputs = [];
    this.predictedLocal = null;
    this.visualErrorX = 0;
    this.visualErrorY = 0;
  }

  public recordAndPredictLocalInput(input: LocalInputState): number {
    this.seqCounter += 1;
    const seq = this.seqCounter;

    if (this.mySlot >= 0 && this.predictedLocal && this.predictedLocal.alive && !this.predictedLocal.spiraling) {
      this.pendingInputs.push({ seq, input: { ...input } });
      if (this.pendingInputs.length > 120) {
        this.pendingInputs.shift();
      }
      const hs = this.snapshots.length > 0
        ? this.snapshots[this.snapshots.length - 1].state.hollowstar
        : { x: 960, y: 540, spinAngle: 0 };
      this.stepShipPhysics(this.predictedLocal, input, hs);
    }

    // Decay visual reconciliation error smoothly
    this.visualErrorX *= 0.8;
    this.visualErrorY *= 0.8;
    if (Math.abs(this.visualErrorX) < 0.05) this.visualErrorX = 0;
    if (Math.abs(this.visualErrorY) < 0.05) this.visualErrorY = 0;

    return seq;
  }

  public onServerSnapshot(pkt: ServerStatePacket): void {
    const now = performance.now();

    const parsedPlayers: RenderPlayer[] = pkt.p.map((tuple) => ({
      slot: tuple[0],
      x: tuple[1],
      y: tuple[2],
      vx: tuple[3],
      vy: tuple[4],
      angle: tuple[5],
      thrust: tuple[6],
      lives: tuple[7],
      alive: tuple[8] === 1,
      spiraling: tuple[9] === 1,
      isAi: tuple[10] === 1,
      name: tuple[11],
    }));

    const parsedProjectiles: RenderProjectile[] = pkt.proj.map((tuple) => ({
      id: tuple[0],
      ownerSlot: tuple[1],
      x: tuple[2],
      y: tuple[3],
      angle: tuple[4],
    }));

    const parsedHollowstar: RenderHollowstar = {
      x: pkt.hs[0],
      y: pkt.hs[1],
      spinAngle: pkt.hs[2],
    };

    const worldState: RenderWorldState = {
      tick: pkt.tick,
      phase: pkt.phase,
      countdown: pkt.cd ?? 0,
      winner: pkt.winner,
      hollowstar: parsedHollowstar,
      players: parsedPlayers,
      projectiles: parsedProjectiles,
    };

    this.snapshots.push({ timestamp: now, state: worldState });
    if (this.snapshots.length > 30) {
      this.snapshots.shift();
    }

    // Reconcile local player prediction against server authoritative ack
    if (this.mySlot >= 0 && this.mySlot < parsedPlayers.length) {
      const serverMe = parsedPlayers[this.mySlot];
      this.pendingInputs = this.pendingInputs.filter((item) => item.seq > pkt.ack);

      if (!serverMe.alive || serverMe.spiraling || !this.predictedLocal) {
        this.predictedLocal = { ...serverMe };
        this.visualErrorX = 0;
        this.visualErrorY = 0;
      } else {
        const prevRenderX = this.predictedLocal.x + this.visualErrorX;
        const prevRenderY = this.predictedLocal.y + this.visualErrorY;

        const reconciled: RenderPlayer = { ...serverMe };
        for (const pending of this.pendingInputs) {
          this.stepShipPhysics(reconciled, pending.input, parsedHollowstar);
        }

        const errX = prevRenderX - reconciled.x;
        const errY = prevRenderY - reconciled.y;
        const errDist = Math.hypot(errX, errY);

        this.predictedLocal = reconciled;
        // Smoothly blend small/medium drift; snap if teleported (e.g. respawn)
        if (errDist < 140) {
          this.visualErrorX = errX;
          this.visualErrorY = errY;
        } else {
          this.visualErrorX = 0;
          this.visualErrorY = 0;
        }
      }
    }
  }

  private stepShipPhysics(ship: RenderPlayer, input: LocalInputState, hs: RenderHollowstar): void {
    const phys = CHASMA_CONFIG.physics;
    const arena = CHASMA_CONFIG.arena;

    // 1. Hollowstar gravity pull
    const dx = hs.x - ship.x;
    const dy = hs.y - ship.y;
    const dist = Math.hypot(dx, dy);
    if (dist < this.tuning.GRAVITY_OUTER_RADIUS && dist > 0) {
      const clampedDist = Math.max(dist, this.tuning.GRAVITY_MIN_DIST);
      const force = this.tuning.GRAVITY_STRENGTH / (clampedDist * clampedDist);
      ship.vx += (dx / dist) * force;
      ship.vy += (dy / dist) * force;
    }

    // 2. Rotation & Thrust
    const changeAngle = input.rotation * phys.ROTATION_SPEED;
    ship.angle = (ship.angle + changeAngle + 360) % 360;
    ship.thrust = input.thrust * phys.THRUST_FORCE;

    if (ship.thrust > 0) {
      const rad = (ship.angle * Math.PI) / 180;
      ship.vx += Math.sin(rad) * ship.thrust;
      ship.vy += Math.cos(rad) * ship.thrust;
    }

    // 3. Drag & Position Step
    ship.vx *= phys.DRAG_COEFFICIENT;
    ship.vy *= phys.DRAG_COEFFICIENT;
    ship.x += ship.vx;
    ship.y += ship.vy;

    // 4. Arena Wall Bounce (dampening = 0.5)
    if (ship.x < arena.ARENA_LEFT) {
      ship.x = arena.ARENA_LEFT;
      ship.vx *= -0.5;
    } else if (ship.x > arena.ARENA_RIGHT) {
      ship.x = arena.ARENA_RIGHT;
      ship.vx *= -0.5;
    }
    if (ship.y < arena.ARENA_BOTTOM) {
      ship.y = arena.ARENA_BOTTOM;
      ship.vy *= -0.5;
    } else if (ship.y > arena.ARENA_TOP) {
      ship.y = arena.ARENA_TOP;
      ship.vy *= -0.5;
    }
  }

  public getRenderState(): RenderWorldState | null {
    if (this.snapshots.length === 0) return null;

    const latest = this.snapshots[this.snapshots.length - 1].state;
    const renderTime = performance.now() - this.interpDelayMs;

    let snapA = this.snapshots[0];
    let snapB = this.snapshots[this.snapshots.length - 1];

    for (let i = 0; i < this.snapshots.length - 1; i++) {
      if (
        this.snapshots[i].timestamp <= renderTime &&
        renderTime <= this.snapshots[i + 1].timestamp
      ) {
        snapA = this.snapshots[i];
        snapB = this.snapshots[i + 1];
        break;
      }
    }

    const span = snapB.timestamp - snapA.timestamp;
    const alpha = span > 0.001 ? Math.max(0, Math.min(1, (renderTime - snapA.timestamp) / span)) : 1.0;

    // Interpolate Hollowstar
    const hollowstar: RenderHollowstar = {
      x: lerp(snapA.state.hollowstar.x, snapB.state.hollowstar.x, alpha),
      y: lerp(snapA.state.hollowstar.y, snapB.state.hollowstar.y, alpha),
      spinAngle: lerpAngleDeg(snapA.state.hollowstar.spinAngle, snapB.state.hollowstar.spinAngle, alpha),
    };

    // Interpolate remote players; use predicted state for local player
    const players: RenderPlayer[] = snapB.state.players.map((pB, idx) => {
      if (idx === this.mySlot && this.predictedLocal && pB.alive && !pB.spiraling) {
        return {
          ...this.predictedLocal,
          x: this.predictedLocal.x + this.visualErrorX,
          y: this.predictedLocal.y + this.visualErrorY,
          lives: pB.lives,
          name: pB.name,
          isAi: pB.isAi,
        };
      }
      const pA = snapA.state.players[idx];
      if (!pA || pA.alive !== pB.alive) return { ...pB };
      // Avoid interpolating across a respawn teleport across the arena
      if (Math.hypot(pB.x - pA.x, pB.y - pA.y) > 250) return { ...pB };

      return {
        ...pB,
        x: lerp(pA.x, pB.x, alpha),
        y: lerp(pA.y, pB.y, alpha),
        angle: lerpAngleDeg(pA.angle, pB.angle, alpha),
      };
    });

    // Interpolate projectiles matched by id
    const projMapA = new Map<number, RenderProjectile>();
    for (const pr of snapA.state.projectiles) {
      projMapA.set(pr.id, pr);
    }

    const projectiles: RenderProjectile[] = snapB.state.projectiles.map((prB) => {
      const prA = projMapA.get(prB.id);
      if (!prA || Math.hypot(prB.x - prA.x, prB.y - prA.y) > 150) {
        return { ...prB };
      }
      return {
        ...prB,
        x: lerp(prA.x, prB.x, alpha),
        y: lerp(prA.y, prB.y, alpha),
        angle: lerpAngleDeg(prA.angle, prB.angle, alpha),
      };
    });

    return {
      tick: latest.tick,
      phase: latest.phase,
      countdown: latest.countdown,
      winner: latest.winner,
      hollowstar,
      players,
      projectiles,
    };
  }
}
