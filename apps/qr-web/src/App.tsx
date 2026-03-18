import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';
import {
  BUILTIN_LOGOS,
  DEFAULT_GRAPHIC_CONFIG,
  FINDER_SHAPE_VALUES,
  LOGO_RECOMMENDED_PRESET,
  MODULE_SHAPE_VALUES,
  applyGraphicOverrides,
  getPresetDisplayName,
  getPresetGraphicConfig,
  listPresetNames,
} from './config/presets';
import { FIELD_SPECS, GROUP_ORDER } from './config/metadata';
import { clamp, color3ToHex, hexToColor3 } from './lib/color';
import {
  loadCustomPresets,
  makeUniquePresetName,
  normalizePresetName,
  parsePresetFileContent,
  saveCustomPresets,
  toPresetFile,
  validateOverrides,
  type CustomPresetMap,
} from './lib/presetsIO';
import { buildAdaptiveGraphicFromLogo } from './lib/logoAdaptivePreset';
import { exportRenderedQRCode, renderStyledQRCode, type LogoAsset } from './lib/qrRenderer';
import type {
  Color3,
  Color4,
  FieldGroup,
  FieldSpec,
  GraphicConfig,
  GraphicPresetFile,
  LogoLibraryChoice,
  OutputFormat,
} from './types/qr';

interface PreviewMeta {
  width: number;
  height: number;
  modules: number;
  decodedText: string | null;
  renderMs: number;
}

type StatusTone = 'info' | 'success' | 'error';

interface StatusState {
  text: string;
  tone: StatusTone;
}

type EditorTab = 'Project' | 'Logo' | 'Output' | 'Graphic';

const BUILTIN_PRESET_NAMES = listPresetNames();
const DEFAULT_URL = 'https://phusis.io/';
const DEFAULT_PRESET_NAME = 'white_clean';
const AUTO_LOGO_PRESET_NAME = 'auto_logo_dynamic';
const OUTPUT_FORMATS: OutputFormat[] = ['auto', 'png', 'webp', 'jpeg', 'svg'];
const PRESET_RECOMMENDED_LOGO: Partial<Record<string, Exclude<LogoLibraryChoice, 'Custom'>>> = {
  full_dark_artistic: 'Phusis',
  luxury: 'Phusis',
  pena_psychologue: 'Romane Pena',
};

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function extForFormat(fmt: OutputFormat): string {
  if (fmt === 'png') return '.png';
  if (fmt === 'webp') return '.webp';
  if (fmt === 'jpeg') return '.jpg';
  if (fmt === 'svg') return '.svg';
  return '';
}

function withExtension(filename: string, ext: string): string {
  const trimmed = filename.trim() || 'qr_output.png';
  const dotIndex = trimmed.lastIndexOf('.');
  if (dotIndex <= 0) return `${trimmed}${ext}`;
  return `${trimmed.slice(0, dotIndex)}${ext}`;
}

function resolveAssetUrl(path: string): string {
  if (/^(https?:|data:|blob:)/i.test(path)) {
    return path;
  }
  const base = import.meta.env.BASE_URL ?? '/';
  const prefix = base.endsWith('/') ? base : `${base}/`;
  const clean = path.replace(/^\/+/, '');
  return `${prefix}${clean}`;
}

function resolvePresetGraphicConfig(name: string, customPresets: CustomPresetMap): GraphicConfig {
  if (BUILTIN_PRESET_NAMES.includes(name)) {
    return getPresetGraphicConfig(name);
  }

  const custom = customPresets[name];
  if (!custom) {
    return getPresetGraphicConfig(DEFAULT_PRESET_NAME);
  }

  return applyGraphicOverrides(DEFAULT_GRAPHIC_CONFIG, custom);
}

function graphicToOverrides(graphic: GraphicConfig): Record<string, unknown> {
  return deepClone(graphic) as unknown as Record<string, unknown>;
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(`Impossible de lire ${file.name}`));
    reader.onload = () => {
      if (typeof reader.result !== 'string') {
        reject(new Error(`Lecture invalide pour ${file.name}`));
        return;
      }
      resolve(reader.result);
    };
    reader.readAsDataURL(file);
  });
}

function downloadJson(filename: string, payload: unknown): void {
  const json = `${JSON.stringify(payload, null, 2)}\n`;
  const blob = new Blob([json], { type: 'application/json;charset=utf-8' });
  const link = document.createElement('a');
  const href = URL.createObjectURL(blob);
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

function parseNumberInput(raw: string): number | null {
  if (raw.trim() === '') return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function channelClamp(raw: number): number {
  return Math.round(clamp(raw, 0, 255));
}

function qualityClamp(raw: number): number {
  return Math.round(clamp(raw, 1, 100));
}

function normalizeUrlForCompare(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

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

function isDecodedMatch(expected: string, decoded: string | null): boolean {
  if (!decoded) return false;
  const left = normalizeUrlForCompare(expected);
  const right = normalizeUrlForCompare(decoded);
  return left !== null && right !== null && left === right;
}

function decodeBadgeClass(expected: string, decoded: string | null): 'decode-ok' | 'decode-fail' | 'decode-unknown' {
  if (decoded === null) return 'decode-unknown';
  return isDecodedMatch(expected, decoded) ? 'decode-ok' : 'decode-fail';
}

export default function App() {
  const initialLogoChoice: LogoLibraryChoice = BUILTIN_LOGOS.Phusis ? 'Phusis' : 'No logo';
  const initialPreset =
    LOGO_RECOMMENDED_PRESET[initialLogoChoice] &&
    BUILTIN_PRESET_NAMES.includes(LOGO_RECOMMENDED_PRESET[initialLogoChoice] as string)
      ? (LOGO_RECOMMENDED_PRESET[initialLogoChoice] as string)
      : DEFAULT_PRESET_NAME;

  const [customPresets, setCustomPresets] = useState<CustomPresetMap>(() => loadCustomPresets());

  const [url, setUrl] = useState(DEFAULT_URL);
  const [presetName, setPresetName] = useState(initialPreset);
  const [graphic, setGraphic] = useState<GraphicConfig>(() => getPresetGraphicConfig(initialPreset));

  const [logoChoice, setLogoChoice] = useState<LogoLibraryChoice>(initialLogoChoice);
  const [customLogoDataUrl, setCustomLogoDataUrl] = useState<string | null>(null);
  const [customLogoUrl, setCustomLogoUrl] = useState('');
  const [customLogoName, setCustomLogoName] = useState('');

  const [boxSize, setBoxSize] = useState(22);
  const [border, setBorder] = useState(4);

  const [autoPreview, setAutoPreview] = useState(true);
  const [decodeCheck, setDecodeCheck] = useState(true);
  const [quietLogs, setQuietLogs] = useState(false);
  const [autoAdaptFromLogo, setAutoAdaptFromLogo] = useState(true);
  const [isAutoAdaptingLogo, setIsAutoAdaptingLogo] = useState(false);

  const [outputFormat, setOutputFormat] = useState<OutputFormat>('auto');
  const [outputFilename, setOutputFilename] = useState('qr_output.png');
  const [outputQuality, setOutputQuality] = useState(92);
  const [outputMaxWidth, setOutputMaxWidth] = useState('');

  const [activeEditorTab, setActiveEditorTab] = useState<EditorTab>('Project');
  const [activeGraphicGroup, setActiveGraphicGroup] = useState<FieldGroup>('General');
  const [mobilePreviewOpen, setMobilePreviewOpen] = useState(false);

  const [isRendering, setIsRendering] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<string>('');
  const [previewMeta, setPreviewMeta] = useState<PreviewMeta | null>(null);
  const [status, setStatus] = useState<StatusState>({ text: 'Ready', tone: 'info' });
  const [dragActive, setDragActive] = useState(false);

  const logoInputRef = useRef<HTMLInputElement | null>(null);
  const importPresetInputRef = useRef<HTMLInputElement | null>(null);

  const renderSequenceRef = useRef(0);
  const renderedCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const renderedSignatureRef = useRef('');

  const customPresetNames = useMemo(() => Object.keys(customPresets).sort(), [customPresets]);
  const allPresetNames = useMemo(
    () => [...BUILTIN_PRESET_NAMES, ...customPresetNames],
    [customPresetNames],
  );

  const groupedSpecs = useMemo(() => {
    const map: Record<FieldGroup, FieldSpec[]> = {
      General: [],
      Modules: [],
      'Full Dark': [],
      Logo: [],
      Medallion: [],
      FX: [],
    };
    for (const spec of FIELD_SPECS) {
      map[spec.group].push(spec);
    }
    return map;
  }, []);

  const renderSignature = useMemo(
    () =>
      JSON.stringify({
        url,
        boxSize,
        border,
        logoChoice,
        customLogoDataUrl,
        customLogoUrl,
        decodeCheck,
        quietLogs,
        graphic,
      }),
    [url, boxSize, border, logoChoice, customLogoDataUrl, customLogoUrl, decodeCheck, quietLogs, graphic],
  );

  useEffect(() => {
    saveCustomPresets(customPresets);
  }, [customPresets]);

  useEffect(() => {
    if (!allPresetNames.includes(presetName)) {
      const fallback = allPresetNames.includes(DEFAULT_PRESET_NAME)
        ? DEFAULT_PRESET_NAME
        : allPresetNames[0] ?? DEFAULT_PRESET_NAME;
      setPresetName(fallback);
      setGraphic(resolvePresetGraphicConfig(fallback, customPresets));
    }
  }, [allPresetNames, customPresets, presetName]);

  const setGraphicField = useCallback(<K extends keyof GraphicConfig>(key: K, value: GraphicConfig[K]) => {
    setGraphic((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resolveLogoAsset = useCallback((): LogoAsset => {
    if (logoChoice === 'Custom') {
      if (customLogoDataUrl) {
        return { kind: 'url', url: customLogoDataUrl };
      }
      if (customLogoUrl.trim()) {
        return { kind: 'url', url: customLogoUrl.trim() };
      }
      return { kind: 'none' };
    }

    if (logoChoice === 'No logo') {
      return { kind: 'none' };
    }

    const path = BUILTIN_LOGOS[logoChoice as Exclude<LogoLibraryChoice, 'Custom'>];
    if (!path) {
      return { kind: 'none' };
    }
    return { kind: 'url', url: resolveAssetUrl(path) };
  }, [customLogoDataUrl, customLogoUrl, logoChoice]);

  const runRender = useCallback(
    async (showErrorAlert: boolean): Promise<HTMLCanvasElement | null> => {
      const trimmedUrl = url.trim();
      if (!trimmedUrl) {
        setStatus({ text: 'URL requise pour générer le QR.', tone: 'error' });
        return null;
      }

      const effectiveBoxSize = Math.max(1, Math.round(boxSize));
      const effectiveBorder = Math.max(1, Math.round(border));

      const sequence = ++renderSequenceRef.current;
      setIsRendering(true);
      const started = performance.now();

      try {
        const result = await renderStyledQRCode({
          url: trimmedUrl,
          boxSize: effectiveBoxSize,
          border: effectiveBorder,
          graphic,
          logo: resolveLogoAsset(),
          decodeCheck,
          quietLogs,
        });

        if (sequence !== renderSequenceRef.current) {
          return null;
        }

        renderedCanvasRef.current = result.canvas;
        renderedSignatureRef.current = renderSignature;
        setPreviewSrc(result.canvas.toDataURL('image/png'));

        setPreviewMeta({
          width: result.canvas.width,
          height: result.canvas.height,
          modules: result.modulesCount,
          decodedText: result.decodedText,
          renderMs: performance.now() - started,
        });

        const decodeMatches = isDecodedMatch(trimmedUrl, result.decodedText);

        if (!decodeCheck) {
          setStatus({ text: 'Preview updated.', tone: 'success' });
        } else if (decodeMatches) {
          setStatus({ text: 'Preview updated. Decode check: OK', tone: 'success' });
        } else if (result.decodedText === null) {
          setStatus({
            text: 'Preview updated. Decode check: inconclusif (le scan mobile peut rester valide).',
            tone: 'info',
          });
        } else {
          setStatus({ text: 'Preview updated. Decode check: mismatch.', tone: 'error' });
        }

        return result.canvas;
      } catch (err) {
        if (sequence !== renderSequenceRef.current) {
          return null;
        }

        const message = err instanceof Error ? err.message : String(err);
        setStatus({ text: `Preview error: ${message}`, tone: 'error' });
        if (showErrorAlert) {
          window.alert(`Preview error:\n${message}`);
        }
        return null;
      } finally {
        if (sequence === renderSequenceRef.current) {
          setIsRendering(false);
        }
      }
    },
    [border, boxSize, decodeCheck, graphic, quietLogs, renderSignature, resolveLogoAsset, url],
  );

  useEffect(() => {
    if (!autoPreview) return;
    const timeoutId = window.setTimeout(() => {
      void runRender(false);
    }, 240);
    return () => window.clearTimeout(timeoutId);
  }, [autoPreview, runRender]);

  useEffect(() => {
    if (!mobilePreviewOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mobilePreviewOpen]);

  useEffect(() => {
    if (!mobilePreviewOpen) return;
    const onKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobilePreviewOpen(false);
      }
    };
    window.addEventListener('keydown', onKeydown);
    return () => window.removeEventListener('keydown', onKeydown);
  }, [mobilePreviewOpen]);

  const onPresetSelected = useCallback(
    (name: string) => {
      setPresetName(name);
      try {
        setGraphic(resolvePresetGraphicConfig(name, customPresets));

        const recommendedLogo = PRESET_RECOMMENDED_LOGO[name];
        if (recommendedLogo && recommendedLogo !== logoChoice) {
          setLogoChoice(recommendedLogo);
          setCustomLogoUrl('');
          setCustomLogoDataUrl(null);
          setCustomLogoName('');
          setStatus({
            text: `Preset loaded: ${getPresetDisplayName(name)}. Logo appliqué: ${recommendedLogo}.`,
            tone: 'info',
          });
          return;
        }

        setStatus({ text: `Preset loaded: ${getPresetDisplayName(name)}`, tone: 'info' });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setStatus({ text: `Impossible de charger le preset: ${message}`, tone: 'error' });
      }
    },
    [customPresets, logoChoice],
  );

  const onApplyLogoAdaptivePreset = useCallback(
    async (logoUrl: string, sourceLabel?: string) => {
      const target = logoUrl.trim();
      if (!target) {
        setStatus({ text: "Aucun logo disponible pour l'adaptation automatique.", tone: 'error' });
        return;
      }

      setIsAutoAdaptingLogo(true);
      try {
        const adaptedGraphic = await buildAdaptiveGraphicFromLogo(target, graphic);
        const overrides = graphicToOverrides(adaptedGraphic);
        setGraphic(adaptedGraphic);
        setCustomPresets((prev) => ({ ...prev, [AUTO_LOGO_PRESET_NAME]: overrides }));
        setPresetName(AUTO_LOGO_PRESET_NAME);
        setStatus({
          text: `Preset adapté automatiquement depuis ${sourceLabel ?? 'le logo'}.`,
          tone: 'success',
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setStatus({ text: `Adaptation auto impossible: ${message}`, tone: 'error' });
      } finally {
        setIsAutoAdaptingLogo(false);
      }
    },
    [graphic],
  );

  const onLogoChoiceChanged = useCallback(
    (choice: LogoLibraryChoice) => {
      setLogoChoice(choice);

      if (choice !== 'Custom') {
        setCustomLogoUrl('');
        setCustomLogoDataUrl(null);
        setCustomLogoName('');
      }

      const recommended = LOGO_RECOMMENDED_PRESET[choice];
      if (recommended && allPresetNames.includes(recommended)) {
        onPresetSelected(recommended);
        setStatus({
          text: `Logo ${choice}: preset recommandé ${getPresetDisplayName(recommended)} appliqué.`,
          tone: 'info',
        });
      }

      if (autoAdaptFromLogo && choice !== 'Custom' && choice !== 'No logo') {
        const path = BUILTIN_LOGOS[choice as Exclude<LogoLibraryChoice, 'Custom'>];
        if (path) {
          void onApplyLogoAdaptivePreset(resolveAssetUrl(path), choice);
        }
      }
    },
    [allPresetNames, autoAdaptFromLogo, onApplyLogoAdaptivePreset, onPresetSelected],
  );

  const onOutputFormatChanged = useCallback((format: OutputFormat) => {
    setOutputFormat(format);
    if (format === 'auto') return;
    setOutputFilename((prev) => withExtension(prev, extForFormat(format)));
  }, []);

  const handleLogoFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setStatus({ text: `Fichier ignoré (pas une image): ${file.name}`, tone: 'error' });
      return;
    }

    try {
      const dataUrl = await fileToDataUrl(file);
      setLogoChoice('Custom');
      setCustomLogoDataUrl(dataUrl);
      setCustomLogoName(file.name);
      setCustomLogoUrl('');
      setStatus({ text: `Logo chargé: ${file.name}`, tone: 'success' });
      if (autoAdaptFromLogo) {
        await onApplyLogoAdaptivePreset(dataUrl, file.name);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setStatus({ text: `Erreur logo: ${message}`, tone: 'error' });
    }
  }, [autoAdaptFromLogo, onApplyLogoAdaptivePreset]);

  const onSaveCustomPreset = useCallback(() => {
    const suggested = normalizePresetName(presetName || 'custom_preset');
    const raw = window.prompt('Nom du preset personnalisé', suggested);
    if (!raw) return;

    const normalized = normalizePresetName(raw);
    const unique = makeUniquePresetName(normalized, allPresetNames);
    const overrides = graphicToOverrides(graphic);

    try {
      validateOverrides(overrides);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setStatus({ text: `Preset invalide: ${message}`, tone: 'error' });
      return;
    }

    setCustomPresets((prev) => ({ ...prev, [unique]: overrides }));
    setPresetName(unique);
    setStatus({ text: `Preset sauvegardé: ${getPresetDisplayName(unique)}`, tone: 'success' });
  }, [allPresetNames, graphic, presetName]);

  const onExportPresetJson = useCallback(() => {
    const basePreset = BUILTIN_PRESET_NAMES.includes(presetName) ? presetName : undefined;
    const payload: GraphicPresetFile = toPresetFile(
      normalizePresetName(presetName || 'preset'),
      graphicToOverrides(graphic),
      basePreset,
    );
    const filename = `${normalizePresetName(presetName || 'preset')}.json`;
    downloadJson(filename, payload);
    setStatus({ text: `Preset exporté: ${filename}`, tone: 'success' });
  }, [graphic, presetName]);

  const onDeleteSelectedCustomPreset = useCallback(() => {
    if (!customPresets[presetName]) {
      return;
    }

    const ok = window.confirm(`Supprimer le preset personnalisé '${presetName}' ?`);
    if (!ok) return;

    setCustomPresets((prev) => {
      const next = { ...prev };
      delete next[presetName];
      return next;
    });

    const fallback = BUILTIN_PRESET_NAMES.includes(DEFAULT_PRESET_NAME)
      ? DEFAULT_PRESET_NAME
      : BUILTIN_PRESET_NAMES[0] ?? DEFAULT_PRESET_NAME;
    onPresetSelected(fallback);
    setStatus({ text: `Preset supprimé: ${presetName}`, tone: 'info' });
  }, [customPresets, onPresetSelected, presetName]);

  const onImportPresetFileChange = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      try {
        const content = await file.text();
        const parsed = parsePresetFileContent(content);
        const validatedConfig = validateOverrides(parsed.overrides);

        const baseName = parsed.name ? normalizePresetName(parsed.name) : normalizePresetName(file.name.replace(/\.json$/i, ''));
        const uniqueName = makeUniquePresetName(baseName, allPresetNames);

        setCustomPresets((prev) => ({ ...prev, [uniqueName]: deepClone(parsed.overrides) }));
        setPresetName(uniqueName);
        setGraphic(validatedConfig);
        setStatus({ text: `Preset importé: ${getPresetDisplayName(uniqueName)}`, tone: 'success' });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setStatus({ text: `Import preset impossible: ${message}`, tone: 'error' });
      } finally {
        event.target.value = '';
      }
    },
    [allPresetNames],
  );

  const onPreviewClick = useCallback(() => {
    void runRender(true);
  }, [runRender]);

  const onResetAll = useCallback(() => {
    const resetPreset = BUILTIN_PRESET_NAMES.includes(initialPreset) ? initialPreset : DEFAULT_PRESET_NAME;

    setUrl(DEFAULT_URL);
    setPresetName(resetPreset);
    setGraphic(getPresetGraphicConfig(resetPreset));

    setLogoChoice(initialLogoChoice);
    setCustomLogoDataUrl(null);
    setCustomLogoUrl('');
    setCustomLogoName('');

    setBoxSize(22);
    setBorder(4);

    setAutoPreview(true);
    setDecodeCheck(true);
    setQuietLogs(false);
    setAutoAdaptFromLogo(true);
    setIsAutoAdaptingLogo(false);

    setOutputFormat('auto');
    setOutputFilename('qr_output.png');
    setOutputQuality(92);
    setOutputMaxWidth('');

    setActiveEditorTab('Project');
    setActiveGraphicGroup('General');
    setMobilePreviewOpen(false);

    setPreviewSrc('');
    setPreviewMeta(null);
    setIsRendering(false);
    renderSequenceRef.current += 1;
    renderedCanvasRef.current = null;
    renderedSignatureRef.current = '';

    setStatus({ text: 'Paramètres réinitialisés.', tone: 'info' });
  }, [initialLogoChoice, initialPreset]);

  const onOpenMobilePreview = useCallback(() => {
    setMobilePreviewOpen(true);
    if (!renderedCanvasRef.current || renderedSignatureRef.current !== renderSignature) {
      void runRender(false);
    }
  }, [renderSignature, runRender]);

  const onExportClick = useCallback(async () => {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) {
      setStatus({ text: 'URL requise pour exporter.', tone: 'error' });
      return;
    }

    let canvas = renderedCanvasRef.current;
    if (!canvas || renderedSignatureRef.current !== renderSignature) {
      const rendered = await runRender(true);
      if (!rendered) return;
      canvas = rendered;
    }

    const maxWidthRaw = outputMaxWidth.trim();
    let maxWidth: number | undefined;
    if (maxWidthRaw) {
      const parsed = parseNumberInput(maxWidthRaw);
      if (parsed === null || parsed <= 0) {
        setStatus({ text: 'Max width doit être un entier positif.', tone: 'error' });
        return;
      }
      maxWidth = Math.round(parsed);
    }

    const filename = outputFilename.trim() || 'qr_output.png';

    try {
      const exported = await exportRenderedQRCode({
        renderedCanvas: canvas,
        url: trimmedUrl,
        boxSize: Math.max(1, Math.round(boxSize)),
        border: Math.max(1, Math.round(border)),
        outputFormat,
        filename,
        quality: Math.round(clamp(outputQuality, 1, 100)),
        maxWidth,
      });
      setOutputFilename(exported.filename);
      setStatus({ text: `Export terminé: ${exported.filename}`, tone: 'success' });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setStatus({ text: `Export impossible: ${message}`, tone: 'error' });
    }
  }, [
    border,
    boxSize,
    outputFilename,
    outputFormat,
    outputMaxWidth,
    outputQuality,
    renderSignature,
    runRender,
    url,
  ]);

  const currentLogoAsset = resolveLogoAsset();
  const hasLogoForAdaptation = currentLogoAsset.kind === 'url' && Boolean(currentLogoAsset.url);

  const onApplyAdaptationFromCurrentLogo = useCallback(() => {
    if (currentLogoAsset.kind !== 'url' || !currentLogoAsset.url) {
      setStatus({ text: "Aucun logo actif pour l'adaptation.", tone: 'error' });
      return;
    }
    const label = logoChoice === 'Custom' ? customLogoName || 'logo personnalisé' : logoChoice;
    void onApplyLogoAdaptivePreset(currentLogoAsset.url, label);
  }, [currentLogoAsset, customLogoName, logoChoice, onApplyLogoAdaptivePreset]);

  const isFullDarkMode = graphic.style_mode === 'full_dark_artistic';
  const qualityDisabled = outputFormat === 'png' || outputFormat === 'svg';
  const maxWidthDisabled = outputFormat === 'svg';
  const selectedPresetIsCustom = Boolean(customPresets[presetName]);
  const editorTabs: EditorTab[] = ['Project', 'Logo', 'Output', 'Graphic'];
  const activeGroupSpecs = groupedSpecs[activeGraphicGroup] ?? [];
  const activeGroupDisabled = activeGraphicGroup === 'Full Dark' && !isFullDarkMode;

  const renderNumericField = (spec: FieldSpec) => {
    const key = spec.key;
    const rawValue = graphic[key];
    const numericValue = typeof rawValue === 'number' ? rawValue : 0;
    const isInt = spec.type === 'int';
    const step = spec.step ?? (isInt ? 1 : 0.01);

    const updateFromString = (nextRaw: string) => {
      const parsed = parseNumberInput(nextRaw);
      if (parsed === null) return;

      let next = parsed;
      if (typeof spec.min === 'number') next = Math.max(spec.min, next);
      if (typeof spec.max === 'number') next = Math.min(spec.max, next);
      if (isInt) next = Math.round(next);

      setGraphicField(key, next as GraphicConfig[typeof key]);
    };

    const showRange = typeof spec.min === 'number' && typeof spec.max === 'number';

    return (
      <div className="field-control number-control">
        {showRange ? (
          <input
            type="range"
            min={spec.min}
            max={spec.max}
            step={step}
            value={numericValue}
            onChange={(event) => updateFromString(event.target.value)}
          />
        ) : null}
        <input
          type="number"
          min={spec.min}
          max={spec.max}
          step={step}
          value={numericValue}
          onChange={(event) => updateFromString(event.target.value)}
        />
      </div>
    );
  };

  const renderColor3Control = (key: keyof GraphicConfig, value: Color3) => {
    const onHexChanged = (hex: string) => {
      setGraphicField(key, hexToColor3(hex) as GraphicConfig[typeof key]);
    };

    const setChannel = (index: number, raw: string) => {
      const parsed = parseNumberInput(raw);
      if (parsed === null) return;
      const next = [...value] as Color3;
      next[index] = channelClamp(parsed);
      setGraphicField(key, next as GraphicConfig[typeof key]);
    };

    return (
      <div className="field-control color-control">
        <input type="color" value={color3ToHex(value)} onChange={(event) => onHexChanged(event.target.value)} />
        <div className="channels">
          <input type="number" min={0} max={255} value={value[0]} onChange={(event) => setChannel(0, event.target.value)} />
          <input type="number" min={0} max={255} value={value[1]} onChange={(event) => setChannel(1, event.target.value)} />
          <input type="number" min={0} max={255} value={value[2]} onChange={(event) => setChannel(2, event.target.value)} />
        </div>
      </div>
    );
  };

  const renderColor4Control = (key: keyof GraphicConfig, value: Color4) => {
    const rgb: Color3 = [value[0], value[1], value[2]];

    const onRgbChanged = (nextRgb: Color3) => {
      const next: Color4 = [nextRgb[0], nextRgb[1], nextRgb[2], value[3]];
      setGraphicField(key, next as GraphicConfig[typeof key]);
    };

    const setAlpha = (raw: string) => {
      const parsed = parseNumberInput(raw);
      if (parsed === null) return;
      const next: Color4 = [value[0], value[1], value[2], channelClamp(parsed)];
      setGraphicField(key, next as GraphicConfig[typeof key]);
    };

    const setRgbChannel = (index: 0 | 1 | 2, raw: string) => {
      const parsed = parseNumberInput(raw);
      if (parsed === null) return;
      const nextRgb: Color3 = [rgb[0], rgb[1], rgb[2]];
      nextRgb[index] = channelClamp(parsed);
      onRgbChanged(nextRgb);
    };

    return (
      <div className="field-control color-control alpha-color-control">
        <div className="rgb-block">
          <input
            type="color"
            value={color3ToHex(rgb)}
            onChange={(event) => onRgbChanged(hexToColor3(event.target.value))}
          />
          <div className="channels">
            <input
              type="number"
              min={0}
              max={255}
              value={rgb[0]}
              onChange={(event) => setRgbChannel(0, event.target.value)}
            />
            <input
              type="number"
              min={0}
              max={255}
              value={rgb[1]}
              onChange={(event) => setRgbChannel(1, event.target.value)}
            />
            <input
              type="number"
              min={0}
              max={255}
              value={rgb[2]}
              onChange={(event) => setRgbChannel(2, event.target.value)}
            />
          </div>
        </div>
        <div className="alpha-block">
          <input type="range" min={0} max={255} value={value[3]} onChange={(event) => setAlpha(event.target.value)} />
          <input type="number" min={0} max={255} value={value[3]} onChange={(event) => setAlpha(event.target.value)} />
        </div>
      </div>
    );
  };

  const renderFieldControl = (spec: FieldSpec) => {
    const key = spec.key;
    const value = graphic[key];

    if (spec.type === 'module_shape') {
      return (
        <select
          value={graphic.module_shape}
          onChange={(event) => setGraphicField('module_shape', event.target.value as GraphicConfig['module_shape'])}
        >
          {MODULE_SHAPE_VALUES.map((shape) => (
            <option key={shape} value={shape}>
              {shape}
            </option>
          ))}
        </select>
      );
    }

    if (spec.type === 'finder_shape') {
      const current = value as GraphicConfig['finder_shape'];
      return (
        <select value={current} onChange={(event) => setGraphicField(key, event.target.value as GraphicConfig[typeof key])}>
          {FINDER_SHAPE_VALUES.map((shape) => (
            <option key={shape} value={shape}>
              {shape}
            </option>
          ))}
        </select>
      );
    }

    if (spec.type === 'boolean') {
      return (
        <label className="switch">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(event) => setGraphicField(key, event.target.checked as GraphicConfig[typeof key])}
          />
          <span>{Boolean(value) ? 'On' : 'Off'}</span>
        </label>
      );
    }

    if (spec.type === 'int' || spec.type === 'float') {
      return renderNumericField(spec);
    }

    if (spec.type === 'color3') {
      return renderColor3Control(key, value as Color3);
    }

    if (spec.type === 'color4') {
      return renderColor4Control(key, value as Color4);
    }

    if (spec.type === 'optional_color3') {
      const enabled = Array.isArray(value);
      const activeColor = (value as Color3 | null) ?? ([128, 128, 128] as Color3);
      return (
        <div className="field-control optional-color-control">
          <label className="switch compact">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(event) =>
                setGraphicField(key, (event.target.checked ? activeColor : null) as GraphicConfig[typeof key])
              }
            />
            <span>{enabled ? 'Active' : 'None'}</span>
          </label>
          <div className="optional-color-body" aria-disabled={!enabled}>
            {renderColor3Control(key, activeColor)}
          </div>
        </div>
      );
    }

    if (spec.type === 'offset2') {
      const tuple = value as [number, number];
      const setOffset = (index: 0 | 1, raw: string) => {
        const parsed = parseNumberInput(raw);
        if (parsed === null) return;
        const next: [number, number] = [tuple[0], tuple[1]];
        next[index] = Math.round(parsed);
        setGraphicField(key, next as GraphicConfig[typeof key]);
      };

      return (
        <div className="field-control offset-control">
          <input type="number" value={tuple[0]} onChange={(event) => setOffset(0, event.target.value)} />
          <input type="number" value={tuple[1]} onChange={(event) => setOffset(1, event.target.value)} />
        </div>
      );
    }

    return <span className="unsupported">Unsupported field</span>;
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>QR Studio Pro Web</h1>
          <p>Single-page editor for branded QR codes with full preset and rendering controls.</p>
        </div>
        <div className="topbar-actions">
          <label className="switch compact">
            <input type="checkbox" checked={autoPreview} onChange={(event) => setAutoPreview(event.target.checked)} />
            <span>Auto preview</span>
          </label>
          <label className="switch compact">
            <input type="checkbox" checked={decodeCheck} onChange={(event) => setDecodeCheck(event.target.checked)} />
            <span>Decode check</span>
          </label>
          <label className="switch compact">
            <input type="checkbox" checked={quietLogs} onChange={(event) => setQuietLogs(event.target.checked)} />
            <span>Quiet logs</span>
          </label>
          <button type="button" className="reset-btn" onClick={onResetAll}>
            Reset
          </button>
        </div>
      </header>

      <main className="content-grid desktop-layout">
        <section className="left-column">
          <article className="card section-tabs-card">
            <div className="section-tabs" role="tablist" aria-label="Sections de paramétrage">
              {editorTabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={`section-tab ${activeEditorTab === tab ? 'active' : ''}`}
                  onClick={() => setActiveEditorTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
          </article>

          {activeEditorTab === 'Project' ? (
            <article className="card">
              <h2>Project</h2>
              <div className="form-grid basic-grid">
                <label className="field wide">
                  <span>URL / Content</span>
                  <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com" />
                </label>

                <label className="field">
                  <span>Preset visuel</span>
                  <select value={presetName} onChange={(event) => onPresetSelected(event.target.value)}>
                    {BUILTIN_PRESET_NAMES.map((name) => (
                      <option key={name} value={name}>
                        {getPresetDisplayName(name)}
                      </option>
                    ))}
                    {customPresetNames.length > 0 ? <option disabled>──────────</option> : null}
                    {customPresetNames.map((name) => (
                      <option key={name} value={name}>
                        {getPresetDisplayName(name)} (Custom)
                      </option>
                    ))}
                  </select>
                </label>

                <div className="field field-buttons">
                  <span>Preset IO</span>
                  <div className="row-buttons">
                    <button type="button" onClick={() => importPresetInputRef.current?.click()}>
                      Import JSON
                    </button>
                    <button type="button" onClick={onSaveCustomPreset}>
                      Save as preset
                    </button>
                    <button type="button" onClick={onExportPresetJson}>
                      Export preset
                    </button>
                    <button
                      type="button"
                      onClick={onDeleteSelectedCustomPreset}
                      disabled={!selectedPresetIsCustom}
                      className="danger"
                    >
                      Delete custom
                    </button>
                  </div>
                </div>
              </div>
              <input
                ref={importPresetInputRef}
                type="file"
                accept="application/json,.json"
                hidden
                onChange={onImportPresetFileChange}
              />
            </article>
          ) : null}

          {activeEditorTab === 'Logo' ? (
            <article className="card">
              <h2>Logo</h2>
              <div className="form-grid">
                <label className="field">
                  <span>Source</span>
                  <select
                    value={logoChoice}
                    onChange={(event) => onLogoChoiceChanged(event.target.value as LogoLibraryChoice)}
                  >
                    <option value="Custom">Custom</option>
                    <option value="No logo">No logo</option>
                    <option value="Phusis">Phusis</option>
                    <option value="Romane Pena">Romane Pena</option>
                  </select>
                </label>

                <label className="field wide">
                  <span>Custom logo URL (optional)</span>
                  <input
                    value={customLogoUrl}
                    onChange={(event) => {
                      setLogoChoice('Custom');
                      setCustomLogoDataUrl(null);
                      setCustomLogoUrl(event.target.value);
                      if (event.target.value.trim()) {
                        setCustomLogoName('URL');
                      }
                    }}
                    placeholder="https://.../logo.png"
                  />
                </label>

                <div className="field field-buttons">
                  <span>Adaptation design</span>
                  <div className="row-buttons">
                    <label className="switch compact">
                      <input
                        type="checkbox"
                        checked={autoAdaptFromLogo}
                        onChange={(event) => setAutoAdaptFromLogo(event.target.checked)}
                      />
                      <span>Auto adapter au logo</span>
                    </label>
                    <button
                      type="button"
                      onClick={onApplyAdaptationFromCurrentLogo}
                      disabled={!hasLogoForAdaptation || isAutoAdaptingLogo}
                    >
                      {isAutoAdaptingLogo ? 'Analyse logo...' : 'Adapter le preset au logo'}
                    </button>
                  </div>
                </div>

                <div
                  className={`drop-zone ${dragActive ? 'active' : ''}`}
                  onDragEnter={(event) => {
                    event.preventDefault();
                    setDragActive(true);
                  }}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragActive(true);
                  }}
                  onDragLeave={(event) => {
                    event.preventDefault();
                    setDragActive(false);
                  }}
                  onDrop={async (event) => {
                    event.preventDefault();
                    setDragActive(false);
                    const file = event.dataTransfer.files?.[0];
                    if (!file) return;
                    await handleLogoFile(file);
                  }}
                >
                  <div>
                    <strong>Drag & drop logo here</strong>
                    <span>{customLogoName ? `Loaded: ${customLogoName}` : 'PNG, JPG, WEBP, SVG ...'}</span>
                  </div>
                  <button type="button" onClick={() => logoInputRef.current?.click()}>
                    Browse logo
                  </button>
                </div>

                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/*"
                  hidden
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    if (file) {
                      await handleLogoFile(file);
                    }
                    event.target.value = '';
                  }}
                />
              </div>
            </article>
          ) : null}

          {activeEditorTab === 'Output' ? (
            <article className="card">
              <h2>Output</h2>
              <div className="form-grid">
                <label className="field wide">
                  <span>Filename</span>
                  <input value={outputFilename} onChange={(event) => setOutputFilename(event.target.value)} />
                </label>

                <label className="field">
                  <span>Format</span>
                  <select
                    value={outputFormat}
                    onChange={(event) => onOutputFormatChanged(event.target.value as OutputFormat)}
                  >
                    {OUTPUT_FORMATS.map((format) => (
                      <option key={format} value={format}>
                        {format}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Quality</span>
                  <div className="inline-number">
                    <input
                      type="range"
                      min={1}
                      max={100}
                      value={outputQuality}
                      onChange={(event) => setOutputQuality(qualityClamp(Number(event.target.value)))}
                      disabled={qualityDisabled}
                    />
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={outputQuality}
                      onChange={(event) => {
                        const parsed = parseNumberInput(event.target.value);
                        if (parsed === null) return;
                        setOutputQuality(qualityClamp(parsed));
                      }}
                      disabled={qualityDisabled}
                    />
                  </div>
                </label>

                <label className="field">
                  <span>Max width (px)</span>
                  <input
                    value={outputMaxWidth}
                    onChange={(event) => setOutputMaxWidth(event.target.value)}
                    placeholder="empty = full size"
                    disabled={maxWidthDisabled}
                  />
                </label>

                <label className="field">
                  <span>Box size</span>
                  <input
                    type="number"
                    min={1}
                    value={boxSize}
                    onChange={(event) => {
                      const parsed = parseNumberInput(event.target.value);
                      if (parsed === null) return;
                      setBoxSize(Math.max(1, Math.round(parsed)));
                    }}
                  />
                </label>

                <label className="field">
                  <span>Border</span>
                  <input
                    type="number"
                    min={1}
                    value={border}
                    onChange={(event) => {
                      const parsed = parseNumberInput(event.target.value);
                      if (parsed === null) return;
                      setBorder(Math.max(1, Math.round(parsed)));
                    }}
                  />
                </label>
              </div>
            </article>
          ) : null}

          {activeEditorTab === 'Graphic' ? (
            <article className="card">
              <h2>Graphic Config</h2>
              <div className="group-tabs" role="tablist" aria-label="Sections graphiques">
                {GROUP_ORDER.map((group) => (
                  <button
                    key={group}
                    type="button"
                    className={`group-tab ${activeGraphicGroup === group ? 'active' : ''}`}
                    onClick={() => setActiveGraphicGroup(group)}
                  >
                    {group}
                  </button>
                ))}
              </div>

              <div className="groups-stack">
                <section className={`group-card ${activeGroupDisabled ? 'disabled' : ''}`}>
                  <div className="group-head">
                    <h3>{activeGraphicGroup}</h3>
                    {activeGraphicGroup === 'Full Dark' ? (
                      <span className={`group-pill ${activeGroupDisabled ? 'warn' : 'ok'}`}>
                        {activeGroupDisabled ? 'Active only in full_dark_artistic' : 'Active'}
                      </span>
                    ) : null}
                  </div>

                  <fieldset disabled={activeGroupDisabled}>
                    {activeGroupSpecs.map((spec) => (
                      <div className="param-row" key={String(spec.key)}>
                        <label title={spec.description}>
                          <span>{spec.label}</span>
                          <small>ⓘ</small>
                        </label>
                        {renderFieldControl(spec)}
                      </div>
                    ))}
                  </fieldset>
                </section>
              </div>
            </article>
          ) : null}
        </section>

        <aside className="right-column">
          <article className="card sticky preview-card">
            <div className="preview-header">
              <h2>Live Preview</h2>
            </div>

            <button type="button" onClick={onPreviewClick} disabled={isRendering} className="preview-line-btn">
              {isRendering ? 'Rendering...' : 'Preview'}
            </button>
            <button
              type="button"
              onClick={onExportClick}
              className="primary preview-line-btn"
              disabled={isRendering}
            >
              Export QR
            </button>

            <div className="preview-width-note">
              Preview width fixed at 30%
            </div>

            <div className={`preview-stage ${previewSrc ? 'has-image' : 'is-empty'}`}>
              {previewSrc ? <img src={previewSrc} alt="QR preview" /> : <div className="placeholder">No preview yet</div>}
            </div>

            <div className="preview-meta">
              {previewMeta ? (
                <>
                  <span>
                    Canvas: {previewMeta.width} x {previewMeta.height}
                  </span>
                  <span>Modules: {previewMeta.modules}</span>
                  <span>Render: {previewMeta.renderMs.toFixed(1)} ms</span>
                  {decodeCheck ? (
                    <span className={decodeBadgeClass(url, previewMeta.decodedText)}>
                      Decode: {previewMeta.decodedText === null ? 'none' : previewMeta.decodedText}
                    </span>
                  ) : null}
                </>
              ) : (
                <span>Waiting for first preview render...</span>
              )}
            </div>

            <div className={`status ${status.tone}`}>{status.text}</div>
          </article>
        </aside>
      </main>

      <button
        type="button"
        className={`mobile-preview-fab ${mobilePreviewOpen ? 'is-hidden' : ''}`}
        onClick={onOpenMobilePreview}
      >
        Preview
      </button>

      <div
        className={`mobile-preview-modal ${mobilePreviewOpen ? 'open' : ''}`}
        onClick={() => setMobilePreviewOpen(false)}
      >
        <div className="mobile-preview-dialog" onClick={(event) => event.stopPropagation()}>
          <div className="mobile-preview-header">
            <h2>Live Preview</h2>
            <button
              type="button"
              className="mobile-preview-close"
              onClick={() => setMobilePreviewOpen(false)}
            >
              Close
            </button>
          </div>

          <div className={`preview-stage mobile ${previewSrc ? 'has-image' : 'is-empty'}`}>
            {previewSrc ? <img src={previewSrc} alt="QR preview" /> : <div className="placeholder">No preview yet</div>}
          </div>

          <div className="preview-actions mobile">
            <button type="button" onClick={onPreviewClick} disabled={isRendering}>
              {isRendering ? 'Rendering...' : 'Preview'}
            </button>
            <button type="button" onClick={onExportClick} className="primary" disabled={isRendering}>
              Export QR
            </button>
          </div>

          <div className="preview-meta">
            {previewMeta ? (
              <>
                <span>
                  Canvas: {previewMeta.width} x {previewMeta.height}
                </span>
                <span>Modules: {previewMeta.modules}</span>
                <span>Render: {previewMeta.renderMs.toFixed(1)} ms</span>
                {decodeCheck ? (
                  <span className={decodeBadgeClass(url, previewMeta.decodedText)}>
                    Decode: {previewMeta.decodedText === null ? 'none' : previewMeta.decodedText}
                  </span>
                ) : null}
              </>
            ) : (
              <span>Waiting for first preview render...</span>
            )}
          </div>

          <div className={`status ${status.tone}`}>{status.text}</div>
        </div>
      </div>
    </div>
  );
}
