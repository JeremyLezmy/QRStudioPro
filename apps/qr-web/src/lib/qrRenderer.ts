import jsQR from 'jsqr';
import qrcode from 'qrcode-generator';
import { clamp, clamp01, clamp8, color3ToCss, color4ToCss, mixColor3 } from './color';
import type { Color3, GraphicConfig, OutputFormat } from '../types/qr';

export interface LogoAsset {
  kind: 'none' | 'url';
  url?: string;
}

export interface RenderRequest {
  url: string;
  boxSize: number;
  border: number;
  graphic: GraphicConfig;
  logo: LogoAsset;
  decodeCheck: boolean;
  quietLogs: boolean;
}

export interface RenderResult {
  canvas: HTMLCanvasElement;
  decodedText: string | null;
  modulesCount: number;
}

interface QRMatrixInfo {
  matrix: boolean[][];
  modules: number;
  cell: number;
  border: number;
  width: number;
  height: number;
  offset: number;
}

function createCanvas(width: number, height: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(width));
  canvas.height = Math.max(1, Math.round(height));
  return canvas;
}

function getReadbackContext(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null {
  // Hint the browser that this 2D context is read frequently via getImageData.
  // This reduces expensive GPU readback paths on some engines.
  return (
    canvas.getContext(
      '2d',
      { willReadFrequently: true } as unknown as CanvasRenderingContext2DSettings,
    ) ?? canvas.getContext('2d')
  );
}

function buildMatrixInfo(url: string, boxSize: number, border: number): QRMatrixInfo {
  const qr = qrcode(0, 'H');
  qr.addData(url);
  qr.make();

  const modules = qr.getModuleCount();
  const matrix: boolean[][] = Array.from({ length: modules }, (_, y) =>
    Array.from({ length: modules }, (_, x) => qr.isDark(y, x)),
  );

  const cell = Math.max(1, Math.round(boxSize));
  const offset = Math.round(border) * cell;
  const width = (modules + 2 * Math.round(border)) * cell;
  const height = width;

  return {
    matrix,
    modules,
    cell,
    border: Math.round(border),
    width,
    height,
    offset,
  };
}

function gradientColorAt(
  x: number,
  y: number,
  width: number,
  height: number,
  start: Color3,
  end: Color3,
  mixBase: Color3 | null,
  mixRatio: number,
): Color3 {
  const t = clamp01((x + y) / Math.max(1, width + height));
  const grad = mixColor3(start, end, t);
  if (!mixBase) return grad;
  const ratio = clamp01(mixRatio);
  return [
    clamp8(ratio * mixBase[0] + (1 - ratio) * grad[0]),
    clamp8(ratio * mixBase[1] + (1 - ratio) * grad[1]),
    clamp8(ratio * mixBase[2] + (1 - ratio) * grad[2]),
  ];
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  radius: number,
): void {
  const r = Math.max(0, Math.min(radius, Math.min(w, h) / 2));
  ctx.beginPath();
  drawRoundedRectPath(ctx, x, y, w, h, r);
  ctx.closePath();
}

function drawRoundedRectPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  radius: number,
): void {
  const r = Math.max(0, Math.min(radius, Math.min(w, h) / 2));
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
}

function drawModuleShape(
  ctx: CanvasRenderingContext2D,
  shape: GraphicConfig['module_shape'],
  x: number,
  y: number,
  size: number,
  cornerRatio: number,
): void {
  if (shape === 'dot') {
    ctx.beginPath();
    ctx.ellipse(x + size / 2, y + size / 2, size / 2, size / 2, 0, 0, Math.PI * 2);
    ctx.fill();
    return;
  }

  if (shape === 'rounded') {
    const radius = Math.max(1, (size / 2) * clamp01(cornerRatio));
    drawRoundedRect(ctx, x, y, size, size, radius);
    ctx.fill();
    return;
  }

  ctx.fillRect(x, y, size, size);
}

function traceFinderShapePath(
  ctx: CanvasRenderingContext2D,
  shape: GraphicConfig['finder_shape'],
  x: number,
  y: number,
  size: number,
  cornerRatio: number,
): void {
  if (shape === 'dot') {
    ctx.moveTo(x + size, y + size / 2);
    ctx.ellipse(x + size / 2, y + size / 2, size / 2, size / 2, 0, 0, Math.PI * 2);
    ctx.closePath();
    return;
  }

  if (shape === 'rounded') {
    const radius = Math.max(1, (size / 2) * clamp01(cornerRatio));
    drawRoundedRectPath(ctx, x, y, size, size, radius);
    ctx.closePath();
    return;
  }

  ctx.rect(x, y, size, size);
  ctx.closePath();
}

function drawFinderRing(
  ctx: CanvasRenderingContext2D,
  shape: GraphicConfig['finder_shape'],
  x: number,
  y: number,
  outerSize: number,
  cornerRatio: number,
): void {
  const ringThickness = outerSize / 7;
  const innerSize = Math.max(1, outerSize - 2 * ringThickness);
  const innerX = x + ringThickness;
  const innerY = y + ringThickness;

  ctx.beginPath();
  traceFinderShapePath(ctx, shape, x, y, outerSize, cornerRatio);
  traceFinderShapePath(ctx, shape, innerX, innerY, innerSize, cornerRatio);
  ctx.fill('evenodd');
}

function isFinderModule(mx: number, my: number, modules: number): boolean {
  const topLeft = mx >= 0 && mx < 7 && my >= 0 && my < 7;
  const topRight = mx >= modules - 7 && mx < modules && my >= 0 && my < 7;
  const bottomLeft = mx >= 0 && mx < 7 && my >= modules - 7 && my < modules;
  return topLeft || topRight || bottomLeft;
}

function drawFinderPatterns(
  ctx: CanvasRenderingContext2D,
  info: QRMatrixInfo,
  cfg: GraphicConfig,
  outerColor: Color3,
  centerColor: Color3,
): void {
  const scale = clamp(cfg.finder_scale, 0.65, 1.5);
  const size = 7 * info.cell * scale;
  const centerSize = (3 * size) / 7;
  const ringThickness = size / 7;

  const finderPositions: Array<{ x: number; y: number }> = [
    { x: info.offset, y: info.offset },
    { x: info.width - info.offset - 7 * info.cell, y: info.offset },
    { x: info.offset, y: info.height - info.offset - 7 * info.cell },
  ];

  ctx.fillStyle = color3ToCss(outerColor);
  for (const finder of finderPositions) {
    const baseX = finder.x + (7 * info.cell - size) / 2;
    const baseY = finder.y + (7 * info.cell - size) / 2;
    drawFinderRing(ctx, cfg.finder_shape, baseX, baseY, size, cfg.finder_corner_ratio);
  }

  ctx.fillStyle = color3ToCss(centerColor);
  for (const finder of finderPositions) {
    const baseX = finder.x + (7 * info.cell - size) / 2;
    const baseY = finder.y + (7 * info.cell - size) / 2;
    const centerX = baseX + 2 * ringThickness;
    const centerY = baseY + 2 * ringThickness;
    drawModuleShape(
      ctx,
      cfg.finder_shape,
      centerX,
      centerY,
      centerSize,
      cfg.finder_corner_ratio,
    );
  }
}

function drawDataModules(
  ctx: CanvasRenderingContext2D,
  info: QRMatrixInfo,
  cfg: GraphicConfig,
  gradientStart: Color3,
  gradientEnd: Color3,
  gradientMixBase: Color3 | null,
  gradientMixRatio: number,
): void {
  const scale = clamp(cfg.module_scale, 0.2, 1.25);
  const drawSize = info.cell * scale;
  const pad = (info.cell - drawSize) / 2;

  for (let my = 0; my < info.modules; my += 1) {
    for (let mx = 0; mx < info.modules; mx += 1) {
      if (!info.matrix[my][mx]) continue;
      if (isFinderModule(mx, my, info.modules)) continue;

      const x0 = info.offset + mx * info.cell + pad;
      const y0 = info.offset + my * info.cell + pad;
      const cx = Math.round(x0 + drawSize / 2);
      const cy = Math.round(y0 + drawSize / 2);

      const color = gradientColorAt(
        cx,
        cy,
        info.width,
        info.height,
        gradientStart,
        gradientEnd,
        gradientMixBase,
        gradientMixRatio,
      );

      ctx.fillStyle = color3ToCss(color);
      drawModuleShape(ctx, cfg.module_shape, x0, y0, drawSize, cfg.module_corner_ratio);
    }
  }
}

function applyGlow(base: HTMLCanvasElement, cfg: GraphicConfig): HTMLCanvasElement {
  if (!cfg.glow_enabled) return base;
  const out = createCanvas(base.width, base.height);
  const ctx = out.getContext('2d');
  const glow = createCanvas(base.width, base.height);
  const gctx = glow.getContext('2d');
  if (!ctx || !gctx) return base;

  const inset = Math.max(0, cfg.glow_inset);
  gctx.filter = `blur(${Math.max(0, cfg.glow_blur_radius)}px)`;
  gctx.fillStyle = color4ToCss(cfg.glow_fill_rgba);
  gctx.beginPath();
  gctx.ellipse(
    base.width / 2,
    base.height / 2,
    Math.max(1, (base.width - 2 * inset) / 2),
    Math.max(1, (base.height - 2 * inset) / 2),
    0,
    0,
    Math.PI * 2,
  );
  gctx.fill();
  gctx.filter = 'none';

  ctx.drawImage(base, 0, 0);
  ctx.drawImage(glow, 0, 0);
  return out;
}

function applyShadow(base: HTMLCanvasElement, cfg: GraphicConfig): HTMLCanvasElement {
  if (!cfg.shadow_enabled) return base;

  const pad = Math.max(0, cfg.shadow_canvas_padding);
  const out = createCanvas(base.width + pad, base.height + pad);
  const ctx = out.getContext('2d');
  if (!ctx) return base;

  const dx = cfg.shadow_offset[0];
  const dy = cfg.shadow_offset[1];

  const px = Math.floor(pad / 2);
  const py = Math.floor(pad / 2);

  ctx.shadowColor = color4ToCss(cfg.shadow_color_rgba);
  ctx.shadowBlur = Math.max(0, cfg.shadow_blur_radius);
  ctx.shadowOffsetX = dx;
  ctx.shadowOffsetY = dy;
  ctx.drawImage(base, px, py);

  ctx.shadowColor = 'transparent';
  ctx.shadowBlur = 0;
  ctx.shadowOffsetX = 0;
  ctx.shadowOffsetY = 0;
  ctx.drawImage(base, px, py);
  return out;
}

function composeOnBackground(base: HTMLCanvasElement, cfg: GraphicConfig): HTMLCanvasElement {
  if (cfg.transparent_output) return base;
  const out = createCanvas(base.width, base.height);
  const ctx = out.getContext('2d');
  if (!ctx) return base;
  ctx.fillStyle = color4ToCss(cfg.background_rgba);
  ctx.fillRect(0, 0, out.width, out.height);
  ctx.drawImage(base, 0, 0);
  return out;
}

function composeBlackBgSafe(qr: HTMLCanvasElement, cfg: GraphicConfig): HTMLCanvasElement {
  if (!cfg.outer_plate_enabled) {
    const withShadow = cfg.shadow_enabled ? applyShadow(qr, cfg) : qr;
    return composeOnBackground(withShadow, cfg);
  }

  const margin = Math.max(0, cfg.outer_plate_margin);
  const plate = createCanvas(qr.width + 2 * margin, qr.height + 2 * margin);
  const pctx = plate.getContext('2d');
  if (!pctx) return qr;

  pctx.fillStyle = color4ToCss(cfg.plate_color_rgba);
  pctx.fillRect(0, 0, plate.width, plate.height);
  pctx.drawImage(qr, margin, margin);

  const withShadow = cfg.shadow_enabled ? applyShadow(plate, cfg) : plate;
  if (cfg.transparent_output) return withShadow;

  const out = createCanvas(withShadow.width, withShadow.height);
  const octx = out.getContext('2d');
  if (!octx) return withShadow;

  octx.fillStyle = color4ToCss(cfg.background_rgba);
  octx.fillRect(0, 0, out.width, out.height);
  octx.drawImage(withShadow, 0, 0);
  return out;
}

function renderDarkGradientQR(info: QRMatrixInfo, cfg: GraphicConfig): HTMLCanvasElement {
  const out = createCanvas(info.width, info.height);
  const ctx = out.getContext('2d');
  if (!ctx) return out;

  if (!cfg.transparent_output) {
    ctx.fillStyle = 'rgb(255 255 255)';
    ctx.fillRect(0, 0, out.width, out.height);
  }

  drawDataModules(
    ctx,
    info,
    cfg,
    cfg.gradient_start_rgb,
    cfg.gradient_end_rgb,
    cfg.gradient_mix_base_rgb,
    cfg.gradient_mix_ratio,
  );
  drawFinderPatterns(ctx, info, cfg, cfg.finder_outer_rgb, cfg.finder_center_rgb);
  return out;
}

function renderFullDarkQR(info: QRMatrixInfo, cfg: GraphicConfig): HTMLCanvasElement {
  const out = createCanvas(info.width, info.height);
  const ctx = out.getContext('2d');
  if (!ctx) return out;

  ctx.fillStyle = color4ToCss(cfg.background_rgba);
  ctx.fillRect(0, 0, out.width, out.height);

  drawDataModules(
    ctx,
    info,
    cfg,
    cfg.gradient_start_rgb,
    cfg.gradient_end_rgb,
    null,
    0,
  );
  drawFinderPatterns(ctx, info, cfg, cfg.finder_outer_rgb, cfg.finder_center_rgb);
  return out;
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    // Allow CORS-enabled remote logos and keep built-in assets/data URLs working.
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const width = img.naturalWidth || img.width;
      const height = img.naturalHeight || img.height;
      if (width <= 0 || height <= 0) {
        reject(new Error(`Logo chargé mais dimensions invalides: ${url}`));
        return;
      }
      resolve(img);
    };
    img.onerror = () => reject(new Error(`Impossible de charger le logo: ${url}`));
    img.src = url;
  });
}

function cropAlphaBounds(canvas: HTMLCanvasElement): HTMLCanvasElement {
  const ctx = getReadbackContext(canvas);
  if (!ctx) return canvas;
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height);

  let minX = canvas.width;
  let minY = canvas.height;
  let maxX = -1;
  let maxY = -1;

  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      const a = data.data[(y * canvas.width + x) * 4 + 3];
      if (a <= 0) continue;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }

  if (maxX < minX || maxY < minY) return canvas;

  const out = createCanvas(maxX - minX + 1, maxY - minY + 1);
  const octx = out.getContext('2d');
  if (!octx) return canvas;
  octx.drawImage(canvas, minX, minY, out.width, out.height, 0, 0, out.width, out.height);
  return out;
}

function recolorLogo(canvas: HTMLCanvasElement, cfg: GraphicConfig): HTMLCanvasElement {
  const ctx = getReadbackContext(canvas);
  if (!ctx) return canvas;
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height);

  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      const i = (y * canvas.width + x) * 4;
      const a = data.data[i + 3];
      if (a === 0) continue;
      const t = clamp01((x + y) / Math.max(1, canvas.width + canvas.height));
      const c = mixColor3(cfg.recolor_logo_start_rgb, cfg.recolor_logo_end_rgb, t);
      data.data[i] = c[0];
      data.data[i + 1] = c[1];
      data.data[i + 2] = c[2];
    }
  }

  ctx.putImageData(data, 0, 0);
  return canvas;
}

function removeDarkLogoBackground(canvas: HTMLCanvasElement, cfg: GraphicConfig): HTMLCanvasElement {
  const ctx = getReadbackContext(canvas);
  if (!ctx) return canvas;
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const threshold = clamp8(cfg.logo_dark_bg_threshold);

  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      const i = (y * canvas.width + x) * 4;
      const maxRgb = Math.max(data.data[i], data.data[i + 1], data.data[i + 2]);
      if (maxRgb < threshold) {
        data.data[i + 3] = 0;
      }
    }
  }

  ctx.putImageData(data, 0, 0);
  return canvas;
}

function resizeKeepRatio(canvas: HTMLCanvasElement, targetW: number): HTMLCanvasElement {
  const longest = Math.max(canvas.width, canvas.height);
  const scale = targetW / Math.max(1, longest);
  const nextW = Math.max(1, Math.round(canvas.width * scale));
  const nextH = Math.max(1, Math.round(canvas.height * scale));
  const out = createCanvas(nextW, nextH);
  const ctx = out.getContext('2d');
  if (!ctx) return canvas;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(canvas, 0, 0, nextW, nextH);
  return out;
}

function buildMedallion(
  logo: HTMLCanvasElement,
  canvasWidth: number,
  cfg: GraphicConfig,
  darkVariant: boolean,
): HTMLCanvasElement {
  const pad = Math.max(0, Math.round(canvasWidth * cfg.medallion_padding_ratio));
  const bw = logo.width + 2 * pad;
  const bh = logo.height + 2 * pad;
  const out = createCanvas(bw, bh);
  const ctx = out.getContext('2d');
  if (!ctx) return logo;

  const radius = Math.max(18, Math.round(Math.min(bw, bh) * cfg.medallion_corner_ratio));
  const fill = darkVariant ? cfg.dark_medallion_fill_rgba : cfg.medallion_fill_rgba;
  const outline = darkVariant ? cfg.dark_medallion_outline_rgba : cfg.medallion_outline_rgba;

  ctx.fillStyle = color4ToCss(fill);
  drawRoundedRect(ctx, 0, 0, bw, bh, radius);
  ctx.fill();

  if (cfg.medallion_outline_width > 0) {
    ctx.strokeStyle = color4ToCss(outline);
    ctx.lineWidth = cfg.medallion_outline_width;
    drawRoundedRect(ctx, 1, 1, bw - 2, bh - 2, radius);
    ctx.stroke();
  }

  if (cfg.medallion_highlight_enabled && !darkVariant) {
    const hh = Math.max(1, Math.round(bh * cfg.medallion_highlight_height_ratio));
    ctx.fillStyle = color4ToCss(cfg.medallion_highlight_rgba);
    drawRoundedRect(ctx, 2, 2, bw - 4, hh, radius);
    ctx.fill();
  }

  ctx.drawImage(logo, Math.round((bw - logo.width) / 2), Math.round((bh - logo.height) / 2));
  return out;
}

async function processLogo(
  logoUrl: string,
  targetWidth: number,
  cfg: GraphicConfig,
): Promise<HTMLCanvasElement> {
  const img = await loadImage(logoUrl);

  const original = createCanvas(img.width, img.height);
  const octx = original.getContext('2d');
  if (!octx) return original;
  octx.drawImage(img, 0, 0);

  if (cfg.logo_keep_original) {
    return resizeKeepRatio(original, targetWidth);
  }

  let work = original;
  if (cfg.logo_remove_dark_bg) {
    work = removeDarkLogoBackground(work, cfg);
  }

  work = cropAlphaBounds(work);

  if (cfg.recolor_logo) {
    work = recolorLogo(work, cfg);
  }

  return resizeKeepRatio(work, targetWidth);
}

async function addCenterLogo(
  base: HTMLCanvasElement,
  cfg: GraphicConfig,
  logo: LogoAsset,
  darkMedallion: boolean,
  quietLogs: boolean,
): Promise<HTMLCanvasElement> {
  if (logo.kind === 'none' || !logo.url) return base;

  try {
    const out = createCanvas(base.width, base.height);
    const ctx = out.getContext('2d');
    if (!ctx) return base;
    ctx.drawImage(base, 0, 0);

    const targetW = Math.max(1, Math.round(base.width * cfg.logo_scale));
    const logoCanvas = await processLogo(logo.url, targetW, cfg);
    const centerAsset = cfg.medallion_enabled
      ? buildMedallion(logoCanvas, base.width, cfg, darkMedallion)
      : logoCanvas;

    ctx.drawImage(
      centerAsset,
      Math.round((base.width - centerAsset.width) / 2),
      Math.round((base.height - centerAsset.height) / 2),
    );
    return out;
  } catch (err) {
    if (!quietLogs) {
      console.warn(err);
    }
    return base;
  }
}

function drawForDecode(input: HTMLCanvasElement, cfg: GraphicConfig): HTMLCanvasElement {
  const out = createCanvas(input.width, input.height);
  const ctx = out.getContext('2d');
  if (!ctx) return input;

  ctx.fillStyle = color3ToCss([cfg.background_rgba[0], cfg.background_rgba[1], cfg.background_rgba[2]]);
  ctx.fillRect(0, 0, out.width, out.height);
  ctx.drawImage(input, 0, 0);
  return out;
}

function scaleCanvasForDecode(
  source: HTMLCanvasElement,
  scale: number,
  smoothing: boolean,
): HTMLCanvasElement {
  const width = Math.max(1, Math.round(source.width * scale));
  const height = Math.max(1, Math.round(source.height * scale));
  const out = createCanvas(width, height);
  const ctx = out.getContext('2d');
  if (!ctx) return source;
  ctx.imageSmoothingEnabled = smoothing;
  ctx.imageSmoothingQuality = smoothing ? 'high' : 'low';
  ctx.drawImage(source, 0, 0, width, height);
  return out;
}

function thresholdCanvasForDecode(source: HTMLCanvasElement, threshold: number): HTMLCanvasElement {
  const out = createCanvas(source.width, source.height);
  const ctx = getReadbackContext(out);
  const sourceCtx = getReadbackContext(source);
  if (!ctx || !sourceCtx) return source;

  const src = sourceCtx.getImageData(0, 0, source.width, source.height);
  const dst = ctx.createImageData(source.width, source.height);
  for (let i = 0; i < src.data.length; i += 4) {
    const lum = Math.round(0.299 * src.data[i] + 0.587 * src.data[i + 1] + 0.114 * src.data[i + 2]);
    const value = lum >= threshold ? 255 : 0;
    dst.data[i] = value;
    dst.data[i + 1] = value;
    dst.data[i + 2] = value;
    dst.data[i + 3] = 255;
  }

  ctx.putImageData(dst, 0, 0);
  return out;
}

function grayscaleCanvasForDecode(source: HTMLCanvasElement, normalize: boolean): HTMLCanvasElement {
  const out = createCanvas(source.width, source.height);
  const ctx = getReadbackContext(out);
  const sourceCtx = getReadbackContext(source);
  if (!ctx || !sourceCtx) return source;

  const src = sourceCtx.getImageData(0, 0, source.width, source.height);
  const dst = ctx.createImageData(source.width, source.height);

  let minLum = 255;
  let maxLum = 0;
  if (normalize) {
    for (let i = 0; i < src.data.length; i += 4) {
      const lum = Math.round(0.299 * src.data[i] + 0.587 * src.data[i + 1] + 0.114 * src.data[i + 2]);
      if (lum < minLum) minLum = lum;
      if (lum > maxLum) maxLum = lum;
    }
  }
  const range = Math.max(1, maxLum - minLum);

  for (let i = 0; i < src.data.length; i += 4) {
    let lum = Math.round(0.299 * src.data[i] + 0.587 * src.data[i + 1] + 0.114 * src.data[i + 2]);
    if (normalize) {
      lum = Math.round(((lum - minLum) * 255) / range);
    }
    dst.data[i] = lum;
    dst.data[i + 1] = lum;
    dst.data[i + 2] = lum;
    dst.data[i + 3] = 255;
  }

  ctx.putImageData(dst, 0, 0);
  return out;
}

function decodeWithJsQr(source: HTMLCanvasElement): string | null {
  try {
    const ctx = getReadbackContext(source);
    if (!ctx) return null;
    const data = ctx.getImageData(0, 0, source.width, source.height);

    const decode = jsQR as unknown as (
      input: Uint8ClampedArray,
      width: number,
      height: number,
      options?: { inversionAttempts?: 'dontInvert' | 'onlyInvert' | 'attemptBoth' | 'invertFirst' },
    ) => { data?: string } | null;

    const direct = decode(data.data, source.width, source.height, { inversionAttempts: 'attemptBoth' });
    if (direct?.data) return direct.data;

    const invertOnly = decode(data.data, source.width, source.height, { inversionAttempts: 'onlyInvert' });
    return invertOnly?.data ?? null;
  } catch {
    return null;
  }
}

function normalizeForCompare(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return '';

  try {
    const parsed = new URL(trimmed);
    const protocol = parsed.protocol.toLowerCase();
    const host = parsed.hostname.toLowerCase();
    const isDefaultPort =
      (protocol === 'http:' && parsed.port === '80') ||
      (protocol === 'https:' && parsed.port === '443');
    const port = parsed.port && !isDefaultPort ? `:${parsed.port}` : '';
    const path = parsed.pathname === '/' ? '' : parsed.pathname;
    return `${protocol}//${host}${port}${path}${parsed.search}${parsed.hash}`;
  } catch {
    return trimmed;
  }
}

function isDecodedEquivalent(expectedRaw: string, decoded: string | null): boolean {
  if (!decoded) return false;
  const expected = normalizeForCompare(expectedRaw);
  const actual = normalizeForCompare(decoded);
  return expected !== '' && actual !== '' && expected === actual;
}

async function decodeWithBarcodeDetector(source: HTMLCanvasElement): Promise<string | null> {
  type BarcodeDetectorResult = { rawValue?: string };
  type BarcodeDetectorInstance = { detect: (input: CanvasImageSource) => Promise<BarcodeDetectorResult[]> };
  type BarcodeDetectorStatic = {
    new (options?: { formats?: string[] }): BarcodeDetectorInstance;
    getSupportedFormats?: () => Promise<string[]>;
  };

  const detectorCtor = (globalThis as { BarcodeDetector?: BarcodeDetectorStatic }).BarcodeDetector;
  if (!detectorCtor) return null;

  try {
    const getSupportedFormats = detectorCtor.getSupportedFormats?.bind(detectorCtor);
    if (getSupportedFormats) {
      const supported = await getSupportedFormats();
      if (!supported.includes('qr_code')) return null;
    }

    const detector = new detectorCtor({ formats: ['qr_code'] });
    const results = await detector.detect(source);
    return results[0]?.rawValue ?? null;
  } catch {
    return null;
  }
}

async function decodeCanvas(
  canvas: HTMLCanvasElement,
  cfg: GraphicConfig,
  expectedRaw?: string,
): Promise<string | null> {
  const source = drawForDecode(canvas, cfg);
  const candidates: HTMLCanvasElement[] = [source];
  const expected = expectedRaw?.trim() ?? '';
  let firstDecoded: string | null = null;
  const mismatchVotes = new Map<string, { count: number; sample: string }>();

  if (Math.max(source.width, source.height) < 1200) {
    candidates.push(scaleCanvasForDecode(source, 1.5, false));
    candidates.push(scaleCanvasForDecode(source, 2, false));
  }

  const normalizedGray = grayscaleCanvasForDecode(source, true);
  const plainGray = grayscaleCanvasForDecode(source, false);

  candidates.push(normalizedGray);
  candidates.push(plainGray);
  candidates.push(thresholdCanvasForDecode(source, 128));
  candidates.push(thresholdCanvasForDecode(source, 160));
  candidates.push(thresholdCanvasForDecode(normalizedGray, 112));
  candidates.push(thresholdCanvasForDecode(normalizedGray, 144));

  for (const candidate of candidates) {
    const decoded = decodeWithJsQr(candidate);
    if (!decoded) continue;
    if (firstDecoded === null) firstDecoded = decoded;
    if (!expected || isDecodedEquivalent(expected, decoded)) {
      return decoded;
    }
    const key = normalizeForCompare(decoded);
    const vote = mismatchVotes.get(key);
    if (!vote) {
      mismatchVotes.set(key, { count: 1, sample: decoded });
    } else {
      vote.count += 1;
    }
  }

  for (const candidate of candidates) {
    const decoded = await decodeWithBarcodeDetector(candidate);
    if (!decoded) continue;
    if (firstDecoded === null) firstDecoded = decoded;
    if (!expected || isDecodedEquivalent(expected, decoded)) {
      return decoded;
    }
    const key = normalizeForCompare(decoded);
    const vote = mismatchVotes.get(key);
    if (!vote) {
      mismatchVotes.set(key, { count: 1, sample: decoded });
    } else {
      vote.count += 1;
    }
  }

  if (expected) {
    let best: { count: number; sample: string } | null = null;
    for (const vote of mismatchVotes.values()) {
      if (!best || vote.count > best.count) {
        best = vote;
      }
    }
    // Only report mismatch when at least two decode paths agree on the same wrong payload.
    if (best && best.count >= 2) {
      return best.sample;
    }
    return null;
  }

  return firstDecoded;
}

export async function renderStyledQRCode(req: RenderRequest): Promise<RenderResult> {
  const info = buildMatrixInfo(req.url, req.boxSize, req.border);
  const cfg = req.graphic;

  if (!req.quietLogs) {
    console.info(`[QR] Rendering style=${cfg.style_mode} modules=${info.modules} canvas=${info.width}x${info.height}`);
  }

  let qrCore: HTMLCanvasElement;
  let decodePrimary: HTMLCanvasElement | null = null;
  let decodeFallback: HTMLCanvasElement | null = null;

  if (cfg.style_mode === 'full_dark_artistic') {
    qrCore = renderFullDarkQR(info, cfg);
    if (cfg.glow_enabled) qrCore = applyGlow(qrCore, cfg);
    decodeFallback = qrCore;
    qrCore = await addCenterLogo(qrCore, cfg, req.logo, true, req.quietLogs);
    decodePrimary = qrCore;
    if (cfg.shadow_enabled) qrCore = applyShadow(qrCore, cfg);
  } else if (cfg.style_mode === 'white_clean') {
    qrCore = renderDarkGradientQR(info, cfg);
    if (cfg.glow_enabled) qrCore = applyGlow(qrCore, cfg);
    decodeFallback = qrCore;
    qrCore = await addCenterLogo(qrCore, cfg, req.logo, false, req.quietLogs);
    decodePrimary = qrCore;
    if (cfg.shadow_enabled) qrCore = applyShadow(qrCore, cfg);
    qrCore = composeOnBackground(qrCore, cfg);
  } else {
    qrCore = renderDarkGradientQR(info, cfg);
    if (cfg.glow_enabled) qrCore = applyGlow(qrCore, cfg);
    decodeFallback = qrCore;
    qrCore = await addCenterLogo(qrCore, cfg, req.logo, false, req.quietLogs);
    decodePrimary = qrCore;
    qrCore = composeBlackBgSafe(qrCore, cfg);
  }

  let decodedText: string | null = null;
  if (req.decodeCheck) {
    try {
      const candidates: HTMLCanvasElement[] = [];
      if (decodePrimary) candidates.push(decodePrimary);
      if (decodeFallback && decodeFallback !== decodePrimary) candidates.push(decodeFallback);
      if (cfg.style_mode !== 'black_bg_safe') {
        candidates.push(qrCore);
      }
      const expected = req.url.trim();

      for (const candidate of candidates) {
        const candidateDecoded = await decodeCanvas(candidate, cfg, expected);
        if (!candidateDecoded) continue;
        if (isDecodedEquivalent(expected, candidateDecoded)) {
          decodedText = candidateDecoded;
          break;
        }
        // decodeCanvas only returns mismatches when they are confirmed by multiple passes.
        decodedText = candidateDecoded;
      }
    } catch (err) {
      decodedText = null;
      if (!req.quietLogs) {
        console.warn('[QR] Decode check failed but render succeeded:', err);
      }
    }
  }

  return {
    canvas: qrCore,
    decodedText,
    modulesCount: info.modules,
  };
}

export function inferFormat(outputFormat: OutputFormat, filename: string): Exclude<OutputFormat, 'auto'> {
  if (outputFormat !== 'auto') return outputFormat;
  const ext = filename.toLowerCase().split('.').pop();
  if (ext === 'webp') return 'webp';
  if (ext === 'jpg' || ext === 'jpeg') return 'jpeg';
  if (ext === 'svg') return 'svg';
  return 'png';
}

function scaleToMaxWidth(canvas: HTMLCanvasElement, maxWidth?: number): HTMLCanvasElement {
  if (!maxWidth || maxWidth <= 0 || canvas.width <= maxWidth) return canvas;
  const ratio = maxWidth / canvas.width;
  const targetH = Math.max(1, Math.round(canvas.height * ratio));
  const out = createCanvas(maxWidth, targetH);
  const ctx = out.getContext('2d');
  if (!ctx) return canvas;
  ctx.drawImage(canvas, 0, 0, out.width, out.height);
  return out;
}

function generateCleanSvg(url: string, boxSize: number, border: number): string {
  const info = buildMatrixInfo(url, boxSize, border);
  const size = info.width;
  const parts: string[] = [];

  parts.push(`<?xml version=\"1.0\" encoding=\"UTF-8\"?>`);
  parts.push(`<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"${size}\" height=\"${size}\" viewBox=\"0 0 ${size} ${size}\">`);
  parts.push(`<rect width=\"100%\" height=\"100%\" fill=\"white\"/>`);
  parts.push('<g fill="black">');

  for (let my = 0; my < info.modules; my += 1) {
    for (let mx = 0; mx < info.modules; mx += 1) {
      if (!info.matrix[my][mx]) continue;
      const x = info.offset + mx * info.cell;
      const y = info.offset + my * info.cell;
      parts.push(`<rect x=\"${x}\" y=\"${y}\" width=\"${info.cell}\" height=\"${info.cell}\"/>`);
    }
  }

  parts.push('</g></svg>');
  return parts.join('');
}

function triggerDownload(blob: Blob, filename: string): void {
  const a = document.createElement('a');
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function exportRenderedQRCode(params: {
  renderedCanvas: HTMLCanvasElement;
  url: string;
  boxSize: number;
  border: number;
  outputFormat: OutputFormat;
  filename: string;
  quality: number;
  maxWidth?: number;
}): Promise<{ actualFormat: string; filename: string }> {
  const actualFormat = inferFormat(params.outputFormat, params.filename);
  const baseName = params.filename.replace(/\.[^/.]+$/, '');

  if (actualFormat === 'svg') {
    const svg = generateCleanSvg(params.url, params.boxSize, params.border);
    triggerDownload(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }), `${baseName}.svg`);
    return { actualFormat: 'svg', filename: `${baseName}.svg` };
  }

  const canvas = scaleToMaxWidth(params.renderedCanvas, params.maxWidth);
  const mime =
    actualFormat === 'jpeg'
      ? 'image/jpeg'
      : actualFormat === 'webp'
        ? 'image/webp'
        : 'image/png';

  const quality = clamp01(params.quality / 100);
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, mime, quality);
  });

  if (!blob) throw new Error('Export blob generation failed');

  const ext = actualFormat === 'jpeg' ? 'jpg' : actualFormat;
  const filename = `${baseName}.${ext}`;
  triggerDownload(blob, filename);
  return { actualFormat, filename };
}
