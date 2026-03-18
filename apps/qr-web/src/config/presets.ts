import type { GraphicConfig, LogoLibraryChoice } from '../types/qr';

export const STYLE_MODE_VALUES: GraphicConfig['style_mode'][] = [
  'black_bg_safe',
  'full_dark_artistic',
  'white_clean',
];

export const MODULE_SHAPE_VALUES: GraphicConfig['module_shape'][] = ['square', 'rounded', 'dot'];
export const FINDER_SHAPE_VALUES: GraphicConfig['finder_shape'][] = ['square', 'rounded', 'dot'];

export const DEFAULT_GRAPHIC_CONFIG: GraphicConfig = {
  style_mode: 'black_bg_safe',

  background_rgba: [8, 10, 14, 255],
  plate_color_rgba: [255, 255, 255, 255],
  transparent_output: false,

  gradient_start_rgb: [16, 72, 62],
  gradient_end_rgb: [36, 92, 132],
  gradient_mix_base_rgb: [16, 21, 28],
  gradient_mix_ratio: 0.55,
  module_shape: 'square',
  module_scale: 1.0,
  module_corner_ratio: 0.35,

  finder_outer_rgb: [16, 21, 28],
  finder_center_rgb: [26, 130, 118],
  finder_shape: 'square',
  finder_scale: 1.0,
  finder_corner_ratio: 0.32,

  light_module_start_rgb: [214, 240, 236],
  light_module_end_rgb: [90, 180, 200],
  full_dark_finder_outer_rgb: [232, 248, 245],
  full_dark_finder_center_rgb: [170, 220, 228],

  logo_scale: 0.145,
  logo_remove_dark_bg: true,
  logo_dark_bg_threshold: 18,
  recolor_logo: true,
  logo_keep_original: false,
  recolor_logo_start_rgb: [38, 170, 150],
  recolor_logo_end_rgb: [70, 120, 165],

  medallion_enabled: true,
  medallion_padding_ratio: 0.018,
  medallion_fill_rgba: [250, 251, 252, 255],
  medallion_outline_rgba: [228, 232, 238, 255],
  medallion_outline_width: 2,
  medallion_corner_ratio: 0.22,
  medallion_highlight_enabled: false,
  medallion_highlight_rgba: [255, 255, 255, 36],
  medallion_highlight_height_ratio: 0.42,

  dark_medallion_fill_rgba: [18, 24, 30, 245],
  dark_medallion_outline_rgba: [210, 232, 230, 180],

  outer_plate_enabled: true,
  outer_plate_margin: 56,

  shadow_enabled: true,
  shadow_color_rgba: [0, 0, 0, 90],
  shadow_blur_radius: 14,
  shadow_offset: [20, 24],
  shadow_canvas_padding: 40,

  glow_enabled: false,
  glow_fill_rgba: [40, 130, 120, 18],
  glow_blur_radius: 40,
  glow_inset: 80,
};

export const PRESET_OVERRIDES: Record<string, Partial<GraphicConfig>> = {
  black_bg_safe: {
    style_mode: 'black_bg_safe',
    background_rgba: [8, 10, 14, 255],
    plate_color_rgba: [255, 255, 255, 255],
    outer_plate_enabled: true,
    shadow_enabled: true,
    glow_enabled: false,
    recolor_logo: true,
    medallion_enabled: true,
    medallion_fill_rgba: [250, 251, 252, 255],
    medallion_outline_rgba: [228, 232, 238, 255],
    medallion_highlight_enabled: false,
  },
  full_dark_artistic: {
    style_mode: 'full_dark_artistic',
    background_rgba: [8, 10, 14, 255],
    gradient_start_rgb: [214, 240, 236],
    gradient_end_rgb: [90, 180, 200],
    finder_outer_rgb: [232, 248, 245],
    finder_center_rgb: [170, 220, 228],
    outer_plate_enabled: false,
    shadow_enabled: false,
    glow_enabled: true,
    recolor_logo: false,
    medallion_enabled: true,
    dark_medallion_fill_rgba: [18, 24, 30, 245],
    dark_medallion_outline_rgba: [210, 232, 230, 180],
  },
  white_clean: {
    style_mode: 'white_clean',
    background_rgba: [255, 255, 255, 255],
    outer_plate_enabled: false,
    shadow_enabled: false,
    glow_enabled: false,
    recolor_logo: true,
    medallion_enabled: true,
    medallion_fill_rgba: [250, 251, 252, 255],
    medallion_outline_rgba: [228, 232, 238, 255],
  },
  luxury: {
    style_mode: 'black_bg_safe',
    background_rgba: [12, 10, 8, 255],
    plate_color_rgba: [247, 239, 225, 255],
    gradient_start_rgb: [123, 88, 25],
    gradient_end_rgb: [197, 152, 67],
    gradient_mix_base_rgb: [40, 28, 11],
    gradient_mix_ratio: 0.4,
    finder_outer_rgb: [65, 48, 20],
    finder_center_rgb: [209, 167, 85],
    recolor_logo: true,
    recolor_logo_start_rgb: [150, 112, 41],
    recolor_logo_end_rgb: [220, 183, 97],
    medallion_fill_rgba: [253, 247, 236, 255],
    medallion_outline_rgba: [216, 184, 124, 255],
    shadow_enabled: true,
    glow_enabled: false,
  },
  pena_psychologue: {
    style_mode: 'white_clean',
    background_rgba: [246, 240, 233, 255],
    gradient_start_rgb: [98, 118, 107],
    gradient_end_rgb: [177, 144, 121],
    gradient_mix_base_rgb: [58, 65, 60],
    gradient_mix_ratio: 0.45,
    finder_outer_rgb: [77, 88, 82],
    finder_center_rgb: [165, 124, 100],
    recolor_logo: false,
    logo_keep_original: true,
    recolor_logo_start_rgb: [108, 135, 122],
    recolor_logo_end_rgb: [175, 139, 114],
    medallion_fill_rgba: [252, 248, 243, 255],
    medallion_outline_rgba: [220, 202, 187, 255],
    shadow_enabled: false,
    shadow_color_rgba: [35, 35, 35, 55],
    shadow_blur_radius: 10,
    shadow_offset: [8, 10],
    shadow_canvas_padding: 22,
  },
};

const HIDDEN_PRESET_NAMES = new Set<string>(['black_bg_safe']);

const BUILTIN_PRESET_LABELS: Record<string, string> = {
  black_bg_safe: 'Noir sécurisé',
  full_dark_artistic: 'Dark artistique',
  white_clean: 'Blanc épuré',
  luxury: 'Luxe',
  pena_psychologue: 'Pena Psychologue',
  auto_logo_dynamic: 'Adapté au logo',
};

function toTitleCase(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getPresetDisplayName(name: string): string {
  return BUILTIN_PRESET_LABELS[name] ?? toTitleCase(name);
}

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function applyGraphicOverrides(
  base: GraphicConfig,
  overrides: Record<string, unknown>,
): GraphicConfig {
  const normalizedOverrides: Record<string, unknown> = { ...overrides };

  // Backward compatibility for V1/V2 saved presets:
  // finder_outer_shape + finder_center_shape -> finder_shape
  if (!('finder_shape' in normalizedOverrides)) {
    const legacyOuter = normalizedOverrides.finder_outer_shape;
    const legacyCenter = normalizedOverrides.finder_center_shape;
    if (typeof legacyOuter === 'string') {
      normalizedOverrides.finder_shape = legacyOuter;
    } else if (typeof legacyCenter === 'string') {
      normalizedOverrides.finder_shape = legacyCenter;
    }
  }
  delete normalizedOverrides.finder_outer_shape;
  delete normalizedOverrides.finder_center_shape;
  // Removed in UI V3: fixed finder placement + mandatory 3 finders.
  delete normalizedOverrides.finder_offset;
  delete normalizedOverrides.finder_top_left_enabled;
  delete normalizedOverrides.finder_top_right_enabled;
  delete normalizedOverrides.finder_bottom_left_enabled;

  // Legacy full-dark color fields are now centralized in Modules.
  if (!('gradient_start_rgb' in normalizedOverrides) && 'light_module_start_rgb' in normalizedOverrides) {
    normalizedOverrides.gradient_start_rgb = normalizedOverrides.light_module_start_rgb;
  }
  if (!('gradient_end_rgb' in normalizedOverrides) && 'light_module_end_rgb' in normalizedOverrides) {
    normalizedOverrides.gradient_end_rgb = normalizedOverrides.light_module_end_rgb;
  }
  if (!('finder_outer_rgb' in normalizedOverrides) && 'full_dark_finder_outer_rgb' in normalizedOverrides) {
    normalizedOverrides.finder_outer_rgb = normalizedOverrides.full_dark_finder_outer_rgb;
  }
  if (!('finder_center_rgb' in normalizedOverrides) && 'full_dark_finder_center_rgb' in normalizedOverrides) {
    normalizedOverrides.finder_center_rgb = normalizedOverrides.full_dark_finder_center_rgb;
  }

  const next = deepClone(base);
  for (const [key, value] of Object.entries(normalizedOverrides)) {
    if (!(key in next)) {
      throw new Error(`Unknown graphic field: ${key}`);
    }
    (next as unknown as Record<string, unknown>)[key] = value;
  }
  return next;
}

export function getPresetGraphicConfig(presetName?: string | null): GraphicConfig {
  const base = deepClone(DEFAULT_GRAPHIC_CONFIG);
  if (!presetName) return base;
  const ov = PRESET_OVERRIDES[presetName];
  if (!ov) {
    throw new Error(`Unknown preset: ${presetName}`);
  }
  return applyGraphicOverrides(base, ov as Record<string, unknown>);
}

export function listPresetNames(): string[] {
  return Object.keys(PRESET_OVERRIDES)
    .filter((name) => !HIDDEN_PRESET_NAMES.has(name))
    .sort();
}

export const BUILTIN_LOGOS: Record<Exclude<LogoLibraryChoice, 'Custom'>, string | null> = {
  'No logo': null,
  Phusis: 'logos/logo_phusis.png',
  'Romane Pena': 'logos/logo-romane-pena.webp',
};

export const LOGO_RECOMMENDED_PRESET: Partial<Record<LogoLibraryChoice, string>> = {
  Phusis: 'full_dark_artistic',
  'Romane Pena': 'pena_psychologue',
};
