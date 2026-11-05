/**
 * HTML5 Canvas2D Vector Renderer (1920x1080 logical space).
 * Replicates `chasma/core/arena.py`, `chasma/entities/hollowstar.py`,
 * `chasma/entities/player.py`, `chasma/entities/projectile.py`, and `chasma/systems/debug_tuner.py`.
 */

import { CHASMA_CONFIG, TuningConfig } from "../config/generated_config";
import {
  RenderHollowstar,
  RenderPlayer,
  RenderProjectile,
  RenderWorldState,
} from "./prediction";

function rgbCss(rgb: readonly [number, number, number] | number[], alpha = 1.0): string {
  if (alpha < 1.0) {
    return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
  }
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

export class ArenaRenderer {
  private readonly width = CHASMA_CONFIG.screen.SCREEN_WIDTH;
  private readonly height = CHASMA_CONFIG.screen.SCREEN_HEIGHT;

  // Convert Python Arcade Y (0 at bottom, 1080 at top) to Canvas2D Y (0 at top, 1080 at bottom)
  private cy(worldY: number): number {
    return this.height - worldY;
  }

  private warpPoint(
    px: number,
    py: number,
    hx: number,
    hy: number,
    tuning: TuningConfig
  ): [number, number] {
    const dx = px - hx;
    const dy = py - hy;
    const dist = Math.max(Math.hypot(dx, dy), 1);
    const warp = tuning.GRID_WARP_STRENGTH / (dist + tuning.GRID_WARP_FALLOFF);
    return [px - (dx / dist) * warp, py - (dy / dist) * warp];
  }

  public render(
    ctx: CanvasRenderingContext2D,
    world: RenderWorldState | null,
    mySlot: number,
    tuning: TuningConfig,
    showDebug: boolean,
    pingMs: number
  ): void {
    ctx.clearRect(0, 0, this.width, this.height);
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, this.width, this.height);

    const hs: RenderHollowstar = world?.hollowstar ?? {
      x: this.width / 2,
      y: this.height / 2,
      spinAngle: 0,
    };

    // 1. Warped Spacetime Grid & Arena Border
    this.drawArena(ctx, hs.x, hs.y, tuning);

    // 2. Hollowstar
    this.drawHollowstar(ctx, hs);

    if (world) {
      // 3. Projectiles
      for (const proj of world.projectiles) {
        this.drawProjectile(ctx, proj);
      }

      // 4. Player Ships
      for (const player of world.players) {
        this.drawPlayer(ctx, player, player.slot === mySlot, tuning);
      }
    }

    // 5. Optional F1 Debug Gravity Rings & Network Telemetry
    if (showDebug) {
      this.drawDebugOverlay(ctx, hs, tuning, world?.tick ?? 0, pingMs);
    }
  }

  private drawArena(
    ctx: CanvasRenderingContext2D,
    hx: number,
    hy: number,
    tuning: TuningConfig
  ): void {
    const {
      ARENA_LEFT: left,
      ARENA_RIGHT: right,
      ARENA_BOTTOM: bottom,
      ARENA_TOP: top,
      GRID_SPACING: spacing,
      WALL_THICKNESS: wallThickness,
      GRID_WARP_SEGMENTS: segments,
    } = CHASMA_CONFIG.arena;

    ctx.strokeStyle = rgbCss(CHASMA_CONFIG.colors.GRID_BLUE, 0.72);
    ctx.lineWidth = 1;

    // Vertical grid lines
    for (let x = left; x <= right; x += spacing) {
      this.drawWarpedLine(ctx, x, bottom, x, top, hx, hy, segments, tuning);
    }

    // Horizontal grid lines
    for (let y = bottom; y <= top; y += spacing) {
      this.drawWarpedLine(ctx, left, y, right, y, hx, hy, segments, tuning);
    }

    // Outer unwarped walls
    ctx.strokeStyle = rgbCss(CHASMA_CONFIG.colors.GRID_BLUE, 1.0);
    ctx.lineWidth = wallThickness;
    ctx.strokeRect(left, this.cy(top), right - left, top - bottom);
  }

  private drawWarpedLine(
    ctx: CanvasRenderingContext2D,
    x1: number,
    y1: number,
    x2: number,
    y2: number,
    hx: number,
    hy: number,
    segments: number,
    tuning: TuningConfig
  ): void {
    ctx.beginPath();
    const [startX, startY] = this.warpPoint(x1, y1, hx, hy, tuning);
    ctx.moveTo(startX, this.cy(startY));

    for (let i = 1; i <= segments; i++) {
      const t = i / segments;
      const px = x1 + (x2 - x1) * t;
      const py = y1 + (y2 - y1) * t;
      const [wx, wy] = this.warpPoint(px, py, hx, hy, tuning);
      ctx.lineTo(wx, this.cy(wy));
    }
    ctx.stroke();
  }

  private drawHollowstar(ctx: CanvasRenderingContext2D, hs: RenderHollowstar): void {
    const vis = CHASMA_CONFIG.visual;
    const cx = hs.x;
    const cy = this.cy(hs.y);

    const discA = vis.HOLLOWSTAR_DISC_OUTER;
    const discB = Math.floor(vis.HOLLOWSTAR_DISC_OUTER * 0.55);
    const tiltRad = (-hs.spinAngle * Math.PI) / 180;

    // 1. Accretion disc — warm amber rotated ellipse
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, discA, discB, tiltRad, 0, Math.PI * 2);
    ctx.fillStyle = rgbCss(CHASMA_CONFIG.colors.HOLLOWSTAR_DISC);
    ctx.fill();
    ctx.restore();

    // 2. Event horizon — black circle
    ctx.beginPath();
    ctx.arc(cx, cy, vis.HOLLOWSTAR_DISC_INNER, 0, Math.PI * 2);
    ctx.fillStyle = "#000000";
    ctx.fill();

    // 3. Glow ring — cold blue-white outline
    ctx.beginPath();
    ctx.arc(cx, cy, vis.HOLLOWSTAR_GLOW_RADIUS, 0, Math.PI * 2);
    ctx.strokeStyle = rgbCss(CHASMA_CONFIG.colors.HOLLOWSTAR_GLOW);
    ctx.lineWidth = 2;
    ctx.stroke();

    // 4. Singularity — pure black center
    ctx.beginPath();
    ctx.arc(cx, cy, vis.HOLLOWSTAR_SINGULARITY, 0, Math.PI * 2);
    ctx.fillStyle = "#000000";
    ctx.fill();
  }

  private drawProjectile(ctx: CanvasRenderingContext2D, proj: RenderProjectile): void {
    const phys = CHASMA_CONFIG.physics;
    const slotColor =
      CHASMA_CONFIG.colors.PLAYER_SLOTS[proj.ownerSlot] ??
      CHASMA_CONFIG.colors.PLAYER1_YELLOW;

    const angleRad = (proj.angle * Math.PI) / 180;
    const halfLen = phys.BLASTER_LENGTH / 2;
    const dx = Math.sin(angleRad) * halfLen;
    const dy = Math.cos(angleRad) * halfLen;

    const x1 = proj.x - dx;
    const y1 = proj.y - dy;
    const x2 = proj.x + dx;
    const y2 = proj.y + dy;

    ctx.beginPath();
    ctx.moveTo(x1, this.cy(y1));
    ctx.lineTo(x2, this.cy(y2));
    ctx.strokeStyle = rgbCss(slotColor);
    ctx.lineWidth = phys.BLASTER_WIDTH;
    ctx.lineCap = "round";
    ctx.stroke();
  }

  private drawPlayer(
    ctx: CanvasRenderingContext2D,
    player: RenderPlayer,
    isMe: boolean,
    tuning: TuningConfig
  ): void {
    if (!player.alive) return;

    const s = tuning.SHIP_SCALE;
    const angleRad = (player.angle * Math.PI) / 180;
    const cosA = Math.cos(angleRad);
    const sinA = Math.sin(angleRad);

    // Exact local-to-world transform from `chasma/entities/player.py`
    const toWorld = (lx: number, ly: number): [number, number] => [
      player.x + lx * cosA + ly * sinA,
      this.cy(player.y - lx * sinA + ly * cosA),
    ];

    const slotColor =
      CHASMA_CONFIG.colors.PLAYER_SLOTS[player.slot] ??
      CHASMA_CONFIG.colors.PLAYER1_YELLOW;

    // Subtle local player ring so you immediately spot your ship in 4-player chaos
    if (isMe) {
      ctx.beginPath();
      ctx.arc(player.x, this.cy(player.y), 24 * s, 0, Math.PI * 2);
      ctx.strokeStyle = rgbCss(slotColor, 0.3);
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // 1. Main ship gray hull polygon: ((-10s, -10s), (10s, -10s), (0, 20s))
    const [h1x, h1y] = toWorld(-10 * s, -10 * s);
    const [h2x, h2y] = toWorld(10 * s, -10 * s);
    const [h3x, h3y] = toWorld(0, 20 * s);

    ctx.beginPath();
    ctx.moveTo(h1x, h1y);
    ctx.lineTo(h2x, h2y);
    ctx.lineTo(h3x, h3y);
    ctx.closePath();
    ctx.fillStyle = rgbCss(CHASMA_CONFIG.colors.SHIP_GRAY);
    ctx.fill();

    // 2. Player colored rear chevron polygon: ((-10s, -10s), (10s, -10s), (0, -3s))
    const [c1x, c1y] = toWorld(-10 * s, -10 * s);
    const [c2x, c2y] = toWorld(10 * s, -10 * s);
    const [c3x, c3y] = toWorld(0, -3 * s);

    ctx.beginPath();
    ctx.moveTo(c1x, c1y);
    ctx.lineTo(c2x, c2y);
    ctx.lineTo(c3x, c3y);
    ctx.closePath();
    ctx.fillStyle = rgbCss(slotColor);
    ctx.fill();

    // 3. Thrust Flame
    if (player.thrust > 0) {
      const vis = CHASMA_CONFIG.visual;
      const phys = CHASMA_CONFIG.physics;
      const thrustRatio = Math.min(1.0, player.thrust / phys.THRUST_FORCE);
      const flameLen =
        (vis.FLAME_MIN_LENGTH +
          thrustRatio * (vis.FLAME_MAX_LENGTH - vis.FLAME_MIN_LENGTH)) *
        (s / 2.0);
      const flameHalfW =
        (vis.FLAME_WIDTH / 2.0) * (0.5 + 0.5 * thrustRatio) * (s / 2.0);
      const backY = -10.0 * s;

      const [f1x, f1y] = toWorld(-flameHalfW, backY);
      const [f2x, f2y] = toWorld(flameHalfW, backY);
      const [f3x, f3y] = toWorld(0, backY - flameLen);

      ctx.beginPath();
      ctx.moveTo(f1x, f1y);
      ctx.lineTo(f2x, f2y);
      ctx.lineTo(f3x, f3y);
      ctx.closePath();
      ctx.fillStyle = "#ff2222";
      ctx.fill();
    }

    // 4. Callsign / AI tag below ship
    ctx.font = "bold 12px Consolas, monospace";
    ctx.textAlign = "center";
    ctx.fillStyle = rgbCss(slotColor, 0.85);
    const tag = isMe ? `${player.name} (YOU)` : player.name;
    ctx.fillText(tag, player.x, this.cy(player.y) + 26 * s);
  }

  private drawDebugOverlay(
    ctx: CanvasRenderingContext2D,
    hs: RenderHollowstar,
    tuning: TuningConfig,
    tick: number,
    pingMs: number
  ): void {
    const cx = hs.x;
    const cy = this.cy(hs.y);

    // Outer gravity boundary (Cyan)
    ctx.beginPath();
    ctx.arc(cx, cy, tuning.GRAVITY_OUTER_RADIUS, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(0, 255, 255, 0.45)";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 2x, 4x, 8x gravity contour rings
    for (const mult of [2, 4, 8]) {
      const r = tuning.GRAVITY_OUTER_RADIUS / Math.sqrt(mult);
      if (r > tuning.GRAVITY_INNER_RADIUS) {
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(0, 255, 255, 0.18)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // Inner event horizon capture boundary (Red)
    ctx.beginPath();
    ctx.arc(cx, cy, tuning.GRAVITY_INNER_RADIUS, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255, 60, 60, 0.75)";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Telemetry box
    ctx.fillStyle = "rgba(5, 10, 22, 0.82)";
    ctx.fillRect(265, 955, 340, 100);
    ctx.strokeStyle = "rgba(0, 255, 255, 0.4)";
    ctx.strokeRect(265, 955, 340, 100);

    ctx.fillStyle = "#7ff0ff";
    ctx.font = "13px Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText(`[F1 DEBUG] Server Tick: ${tick} | RTT: ${pingMs} ms`, 278, 978);
    ctx.fillText(
      `GRAVITY: ${tuning.GRAVITY_STRENGTH} (Outer: ${tuning.GRAVITY_OUTER_RADIUS}px, Inner: ${tuning.GRAVITY_INNER_RADIUS}px)`,
      278,
      1000
    );
    ctx.fillText(
      `SHIP_SCALE: ${tuning.SHIP_SCALE} | COLLISION: ${tuning.SHIP_COLLISION_STRENGTH}`,
      278,
      1022
    );
    ctx.fillText(
      `GRID_WARP: ${tuning.GRID_WARP_STRENGTH} (Falloff: ${tuning.GRID_WARP_FALLOFF})`,
      278,
      1044
    );
  }
}
