import { mixColor3 } from './color';
import type { Color3, GraphicConfig } from '../types/qr';

interface Bucket {
  count: number;
  weightedCount: number;
  r: number;
  g: number;
  b: number;
  sat: number;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function clamp8(value: number): number {
  return Math.round(Math.max(0, Math.min(255, value)));
}

function luminance(color: Color3): number {
  const [r, g, b] = color;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

function saturation(color: Color3): number {
  const [r, g, b] = color.map((c) => c / 255) as [number, number, number];
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  if (max === min) return 0;
  const l = (max + min) / 2;
  const d = max - min;
  return l > 0.5 ? d / (2 - max - min) : d / (max + min);
}

function distance(a: Color3, b: Color3): number {
  const dr = a[0] - b[0];
  const dg = a[1] - b[1];
  const db = a[2] - b[2];
  return Math.sqrt(dr * dr + dg * dg + db * db);
}

function darken(color: Color3, amount: number): Color3 {
  return mixColor3(color, [0, 0, 0], clamp01(amount));
}

function lighten(color: Color3, amount: number): Color3 {
  return mixColor3(color, [255, 255, 255], clamp01(amount));
}

function withAlpha(color: Color3, alpha: number): [number, number, number, number] {
  return [color[0], color[1], color[2], clamp8(alpha)];
}

function cloneGraphic(base: GraphicConfig): GraphicConfig {
  return JSON.parse(JSON.stringify(base)) as GraphicConfig;
}

function getBucketKey(r: number, g: number, b: number): string {
  return `${r >> 5}-${g >> 5}-${b >> 5}`;
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const width = img.naturalWidth || img.width;
      const height = img.naturalHeight || img.height;
      if (width <= 0 || height <= 0) {
        reject(new Error(`Logo chargé mais dimensions invalides pour analyse: ${url}`));
        return;
      }
      resolve(img);
    };
    img.onerror = () => reject(new Error(`Impossible de charger le logo pour analyse: ${url}`));
    img.src = url;
  });
}

function getReadbackContext(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null {
  return (
    canvas.getContext(
      '2d',
      { willReadFrequently: true } as unknown as CanvasRenderingContext2DSettings,
    ) ?? canvas.getContext('2d')
  );
}

function extractDominants(imageData: ImageData): { primary: Color3; secondary: Color3 } {
  const buckets = new Map<string, Bucket>();
  const data = imageData.data;
  const pixelCount = imageData.width * imageData.height;

  for (let i = 0; i < pixelCount; i += 1) {
    const idx = i * 4;
    const a = data[idx + 3];
    if (a < 36) continue;

    const r = data[idx];
    const g = data[idx + 1];
    const b = data[idx + 2];
    const color: Color3 = [r, g, b];
    const sat = saturation(color);
    const lum = luminance(color);
    const key = getBucketKey(r, g, b);

    const whiteOrBlackPenalty = lum < 0.06 || lum > 0.96 ? 0.3 : 1;
    const satBoost = 0.55 + sat * 0.9;
    const alphaWeight = a / 255;
    const weight = alphaWeight * satBoost * whiteOrBlackPenalty;

    const existing = buckets.get(key);
    if (!existing) {
      buckets.set(key, {
        count: 1,
        weightedCount: weight,
        r: r * weight,
        g: g * weight,
        b: b * weight,
        sat: sat * weight,
      });
    } else {
      existing.count += 1;
      existing.weightedCount += weight;
      existing.r += r * weight;
      existing.g += g * weight;
      existing.b += b * weight;
      existing.sat += sat * weight;
    }
  }

  if (buckets.size === 0) {
    throw new Error("Aucun pixel exploitable trouvé dans le logo.");
  }

  const ranked = Array.from(buckets.values())
    .filter((b) => b.weightedCount > 0)
    .map((bucket) => {
      const w = Math.max(1e-6, bucket.weightedCount);
      const avg: Color3 = [
        clamp8(bucket.r / w),
        clamp8(bucket.g / w),
        clamp8(bucket.b / w),
      ];
      return {
        color: avg,
        weightedCount: bucket.weightedCount,
        sat: bucket.sat / w,
      };
    })
    .sort((a, b) => b.weightedCount - a.weightedCount);

  const primary = ranked[0]?.color ?? ([24, 96, 88] as Color3);
  const primarySat = saturation(primary);

  let secondary = primary;
  let bestScore = -1;
  for (const item of ranked.slice(1, 16)) {
    const d = distance(primary, item.color);
    const satBonus = 1 + item.sat * 0.6 + primarySat * 0.25;
    const score = d * satBonus;
    if (score > bestScore) {
      bestScore = score;
      secondary = item.color;
    }
  }

  if (bestScore < 0) {
    // Fallback: generate a contrasting sibling.
    secondary = lighten(darken(primary, 0.2), 0.35);
  }

  return { primary, secondary };
}

function downscaleForAnalysis(img: HTMLImageElement): ImageData {
  const longest = Math.max(img.width, img.height);
  const targetLongest = 140;
  const scale = longest > targetLongest ? targetLongest / longest : 1;
  const w = Math.max(8, Math.round(img.width * scale));
  const h = Math.max(8, Math.round(img.height * scale));

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = getReadbackContext(canvas);
  if (!ctx) {
    throw new Error('Canvas context indisponible pour analyser le logo.');
  }

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(img, 0, 0, w, h);
  return ctx.getImageData(0, 0, w, h);
}

export async function buildAdaptiveGraphicFromLogo(
  logoUrl: string,
  baseGraphic: GraphicConfig,
): Promise<GraphicConfig> {
  const img = await loadImage(logoUrl);
  const imageData = downscaleForAnalysis(img);
  const { primary, secondary } = extractDominants(imageData);

  const next = cloneGraphic(baseGraphic);

  const deepPrimary = darken(primary, 0.58);
  const deepSecondary = darken(secondary, 0.5);
  const deepBase = darken(mixColor3(primary, secondary, 0.45), 0.7);
  const softBg = lighten(mixColor3(primary, secondary, 0.35), 0.94);
  const finderCore = lighten(primary, 0.08);
  const logoA = lighten(primary, 0.02);
  const logoB = lighten(secondary, 0.03);
  const medFill = lighten(mixColor3(primary, secondary, 0.25), 0.93);
  const medOutline = lighten(mixColor3(primary, secondary, 0.7), 0.82);

  next.gradient_start_rgb = deepPrimary;
  next.gradient_end_rgb = deepSecondary;
  next.gradient_mix_base_rgb = deepBase;
  next.gradient_mix_ratio = 0.42;
  next.finder_outer_rgb = darken(deepBase, 0.18);
  next.finder_center_rgb = finderCore;
  next.recolor_logo_start_rgb = logoA;
  next.recolor_logo_end_rgb = logoB;
  next.medallion_fill_rgba = withAlpha(medFill, 255);
  next.medallion_outline_rgba = withAlpha(medOutline, 255);
  next.plate_color_rgba = withAlpha(lighten(softBg, 0.05), 255);
  next.shadow_color_rgba = withAlpha(darken(deepBase, 0.2), 75);

  if (next.style_mode === 'full_dark_artistic') {
    const darkBg = darken(mixColor3(primary, secondary, 0.5), 0.88);
    next.background_rgba = withAlpha(darkBg, 255);
    next.light_module_start_rgb = lighten(primary, 0.64);
    next.light_module_end_rgb = lighten(secondary, 0.52);
    next.full_dark_finder_outer_rgb = lighten(mixColor3(primary, secondary, 0.45), 0.9);
    next.full_dark_finder_center_rgb = lighten(primary, 0.42);
    next.dark_medallion_fill_rgba = withAlpha(darken(mixColor3(primary, secondary, 0.4), 0.72), 245);
    next.dark_medallion_outline_rgba = withAlpha(lighten(primary, 0.4), 180);
  } else {
    next.background_rgba = withAlpha(softBg, 255);
    next.light_module_start_rgb = lighten(primary, 0.56);
    next.light_module_end_rgb = lighten(secondary, 0.48);
    next.full_dark_finder_outer_rgb = lighten(mixColor3(primary, secondary, 0.45), 0.88);
    next.full_dark_finder_center_rgb = lighten(primary, 0.36);
  }

  return next;
}
