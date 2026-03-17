# QR Studio Pro

Générateur de QR codes stylisés avec:
- une CLI (`qr.py`) pour automatiser la génération,
- une GUI CustomTkinter (`qr_gui.py`) pour designer visuellement les QR,
- des presets graphiques, des logos intégrés, et des exports desktop (Windows/macOS).

## Fonctionnalités

- Génération QR avec logo central (ou sans logo).
- Presets graphiques prêts à l'emploi:
  - `black_bg_safe`
  - `full_dark_artistic`
  - `white_clean`
  - `luxury`
  - `pena_psychologue`
- Personnalisation avancée des modules QR:
  - forme (`square`, `rounded`, `dot`)
  - échelle
  - arrondi
- GUI avec aperçu live, palette couleurs, import/export de preset JSON.
- Logos intégrés dans l'app:
  - Phusis
  - Romane Pena
- Auto-preset par logo intégré:
  - Phusis -> `full_dark_artistic`
  - Romane Pena -> `pena_psychologue`
- Export image (PNG/JPEG/WEBP/SVG selon mode).
- Packaging desktop:
  - `QRStudioPro.exe` (Windows)
  - `QRStudioPro-macos.dmg` + `.app` (macOS)

## Installation

Pré-requis:
- Python 3.11 recommandé

Installation:

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

Exemple simple:

```bash
python qr.py --url "https://phusis.io" --preset luxury --logo none --output generated_qrcode/qr_luxury.png
```

Exemple avec config graphique JSON:

```bash
python qr.py --url "https://phusis.io" --preset black_bg_safe --graphic-config my_preset.json
```

## Presets custom (GUI)

Dans l'application:
- `Preset IO > Save Preset` pour sauvegarder la config courante en JSON.
- `Preset IO > Import JSON` pour importer un preset et l'ajouter à la liste.

Format JSON supporté:
- format enveloppé versionné (`format_version`, `name`, `graphic_overrides`)
- format historique plat (compatibilité conservée)

## Build desktop

Voir [PACKAGING.md](PACKAGING.md).

Commandes principales:

```powershell
# Windows
./scripts/build_windows.ps1
```

```bash
# macOS
./scripts/build_macos.sh
```

Sorties:
- Windows: `dist/QRStudioPro.exe`
- macOS: `dist/QRStudioPro.app` et `dist/QRStudioPro-macos.dmg`

## CI/CD GitHub

Workflow inclus: `.github/workflows/desktop-build-release.yml`

- Build manuel: `workflow_dispatch`
- Release auto: push d'un tag `v*` (ex: `v1.0.2`)
- Assets de release:
  - `QRStudioPro.exe`
  - `QRStudioPro-macos.dmg`

Note: GitHub ajoute aussi automatiquement `Source code (zip)` et `Source code (tar.gz)`.

## Structure du projet

- `generate_qrcode.py`: moteur de génération/rendu QR.
- `qr_presets.py`: dataclass graphique + presets + import/export de config.
- `qr.py`: CLI.
- `qr_gui.py`: point d'entrée GUI.
- `qr_studio_gui/`: code interface (CustomTkinter).
- `scripts/`: build, packaging, génération d'icônes.
- `assets/`: icônes app et logos intégrés.
