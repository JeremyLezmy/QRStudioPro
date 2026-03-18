# QR Studio Pro Desktop (Python)

Générateur de QR codes stylisés avec:
- une CLI (`qr.py`) pour automatiser la génération,
- une GUI CustomTkinter (`qr_gui.py`) pour designer visuellement les QR,
- des presets graphiques, des logos intégrés, et des exports desktop (Windows/macOS).

## Fonctionnalités

- Génération QR avec logo central (ou sans logo).
- Presets graphiques:
  - `black_bg_safe`
  - `full_dark_artistic`
  - `white_clean`
  - `luxury`
  - `pena_psychologue`
- Personnalisation des modules QR:
  - forme (`square`, `rounded`, `dot`)
  - échelle
  - arrondi
- GUI avec aperçu live, palette couleurs, import/export de preset JSON.
- Logos intégrés:
  - Phusis
  - Romane Pena
- Auto-preset par logo intégré:
  - Phusis -> `full_dark_artistic`
  - Romane Pena -> `pena_psychologue`
- Export image (PNG/JPEG/WEBP/SVG selon mode).

## Installation

Pré-requis: Python 3.11 recommandé.

```bash
pip install -r requirements.txt
```

## Utilisation rapide

### GUI

```bash
python qr_gui.py
```

### CLI

Lister les presets:

```bash
python qr.py --list-presets
```

Exemple:

```bash
python qr.py --url "https://phusis.io" --preset luxury --logo none --output generated_qrcode/qr_luxury.png
```

## Build desktop

Voir [PACKAGING.md](PACKAGING.md).

Windows:

```powershell
./scripts/build_windows.ps1
```

macOS:

```bash
./scripts/build_macos.sh
```

Sorties:
- Windows: `dist/QRStudioPro.exe`
- macOS: `dist/QRStudioPro.app` et `dist/QRStudioPro-macos.dmg`

## CI/CD GitHub

Workflow: `/.github/workflows/desktop-build-release.yml`

- Build manuel: `workflow_dispatch`
- Release auto: push d'un tag `v*`
- Assets de release:
  - `QRStudioPro.exe`
  - `QRStudioPro-macos.dmg`
