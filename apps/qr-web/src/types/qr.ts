export type Color3 = [number, number, number];
export type Color4 = [number, number, number, number];

export type StyleMode = 'black_bg_safe' | 'full_dark_artistic' | 'white_clean';
export type ModuleShape = 'square' | 'rounded' | 'dot';
export type FinderShape = 'square' | 'rounded' | 'dot';

export interface GraphicConfig {
  style_mode: StyleMode;

  background_rgba: Color4;
  plate_color_rgba: Color4;
  transparent_output: boolean;

  gradient_start_rgb: Color3;
  gradient_end_rgb: Color3;
  gradient_mix_base_rgb: Color3 | null;
  gradient_mix_ratio: number;
  module_shape: ModuleShape;
  module_scale: number;
  module_corner_ratio: number;

  finder_outer_rgb: Color3;
  finder_center_rgb: Color3;
  finder_shape: FinderShape;
  finder_scale: number;
  finder_corner_ratio: number;
  finder_offset: [number, number];
  finder_top_left_enabled: boolean;
  finder_top_right_enabled: boolean;
  finder_bottom_left_enabled: boolean;

  light_module_start_rgb: Color3;
  light_module_end_rgb: Color3;
  full_dark_finder_outer_rgb: Color3;
  full_dark_finder_center_rgb: Color3;

  logo_scale: number;
  logo_remove_dark_bg: boolean;
  logo_dark_bg_threshold: number;
  recolor_logo: boolean;
  logo_keep_original: boolean;
  recolor_logo_start_rgb: Color3;
  recolor_logo_end_rgb: Color3;

  medallion_enabled: boolean;
  medallion_padding_ratio: number;
  medallion_fill_rgba: Color4;
  medallion_outline_rgba: Color4;
  medallion_outline_width: number;
  medallion_corner_ratio: number;
  medallion_highlight_enabled: boolean;
  medallion_highlight_rgba: Color4;
  medallion_highlight_height_ratio: number;

  dark_medallion_fill_rgba: Color4;
  dark_medallion_outline_rgba: Color4;

  outer_plate_enabled: boolean;
  outer_plate_margin: number;

  shadow_enabled: boolean;
  shadow_color_rgba: Color4;
  shadow_blur_radius: number;
  shadow_offset: [number, number];
  shadow_canvas_padding: number;

  glow_enabled: boolean;
  glow_fill_rgba: Color4;
  glow_blur_radius: number;
  glow_inset: number;
}

export interface QRConfig {
  url: string;
  boxSize: number;
  border: number;
  graphic: GraphicConfig;
}

export type OutputFormat = 'auto' | 'png' | 'webp' | 'jpeg' | 'svg';

export type LogoLibraryChoice = 'Custom' | 'No logo' | 'Phusis' | 'Romane Pena';

export interface RenderOptions {
  decodeCheck: boolean;
  quietLogs: boolean;
}

export type FieldGroup = 'General' | 'Modules' | 'Full Dark' | 'Logo' | 'Medallion' | 'FX';
export type FieldType =
  | 'style_mode'
  | 'module_shape'
  | 'finder_shape'
  | 'boolean'
  | 'int'
  | 'float'
  | 'color3'
  | 'color4'
  | 'optional_color3'
  | 'offset2';

export interface FieldSpec {
  key: keyof GraphicConfig;
  label: string;
  description: string;
  group: FieldGroup;
  type: FieldType;
  min?: number;
  max?: number;
  step?: number;
}

export interface GraphicPresetFile {
  format_version?: number;
  name?: string;
  base_preset?: string;
  graphic_overrides?: Record<string, unknown>;
}
