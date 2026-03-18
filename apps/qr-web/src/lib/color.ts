import type { Color3, Color4 } from '../types/qr';

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function clamp01(v: number): number {
  return clamp(v, 0, 1);
}

export function clamp8(v: number): number {
  return Math.round(clamp(v, 0, 255));
}

export function color3ToCss(c: Color3): string {
  return `rgb(${clamp8(c[0])} ${clamp8(c[1])} ${clamp8(c[2])})`;
}

export function color4ToCss(c: Color4): string {
  return `rgba(${clamp8(c[0])}, ${clamp8(c[1])}, ${clamp8(c[2])}, ${clamp01(c[3] / 255)})`;
}

export function color3ToHex(c: Color3): string {
  return `#${clamp8(c[0]).toString(16).padStart(2, '0')}${clamp8(c[1]).toString(16).padStart(2, '0')}${clamp8(c[2])
    .toString(16)
    .padStart(2, '0')}`;
}

export function hexToColor3(hex: string): Color3 {
  const normalized = hex.replace('#', '');
  if (normalized.length !== 6) return [128, 128, 128];
  return [
    parseInt(normalized.slice(0, 2), 16),
    parseInt(normalized.slice(2, 4), 16),
    parseInt(normalized.slice(4, 6), 16),
  ];
}

export function mixColor3(a: Color3, b: Color3, t: number): Color3 {
  const tt = clamp01(t);
  return [
    clamp8((1 - tt) * a[0] + tt * b[0]),
    clamp8((1 - tt) * a[1] + tt * b[1]),
    clamp8((1 - tt) * a[2] + tt * b[2]),
  ];
}
