import { applyGraphicOverrides, DEFAULT_GRAPHIC_CONFIG } from '../config/presets';
import type { GraphicConfig, GraphicPresetFile } from '../types/qr';

const CUSTOM_PRESETS_STORAGE_KEY = 'qr-studio-pro-custom-presets-v1';

export type CustomPresetMap = Record<string, Record<string, unknown>>;

export function loadCustomPresets(): CustomPresetMap {
  try {
    const raw = localStorage.getItem(CUSTOM_PRESETS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed as CustomPresetMap;
  } catch {
    return {};
  }
}

export function saveCustomPresets(map: CustomPresetMap): void {
  localStorage.setItem(CUSTOM_PRESETS_STORAGE_KEY, JSON.stringify(map));
}

export function normalizePresetName(raw: string): string {
  const cleaned = raw
    .trim()
    .replace(/[^a-zA-Z0-9_-]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return cleaned || 'custom_preset';
}

export function makeUniquePresetName(baseName: string, existingNames: string[]): string {
  const existing = new Set(existingNames);
  if (!existing.has(baseName)) return baseName;
  let idx = 2;
  while (existing.has(`${baseName}_${idx}`)) idx += 1;
  return `${baseName}_${idx}`;
}

export function toPresetFile(name: string, overrides: Record<string, unknown>, basePreset?: string): GraphicPresetFile {
  return {
    format_version: 1,
    name,
    base_preset: basePreset,
    graphic_overrides: overrides,
  };
}

export function parsePresetFileContent(content: string): { name?: string; overrides: Record<string, unknown> } {
  const parsed = JSON.parse(content) as GraphicPresetFile | Record<string, unknown>;
  if (!parsed || typeof parsed !== 'object') {
    throw new Error('Le fichier preset doit contenir un objet JSON');
  }

  if ('graphic_overrides' in parsed) {
    const file = parsed as GraphicPresetFile;
    if (!file.graphic_overrides || typeof file.graphic_overrides !== 'object') {
      throw new Error("'graphic_overrides' doit être un objet JSON");
    }
    return {
      name: file.name,
      overrides: file.graphic_overrides,
    };
  }

  return {
    overrides: parsed as Record<string, unknown>,
  };
}

export function validateOverrides(overrides: Record<string, unknown>): GraphicConfig {
  return applyGraphicOverrides(DEFAULT_GRAPHIC_CONFIG, overrides);
}
