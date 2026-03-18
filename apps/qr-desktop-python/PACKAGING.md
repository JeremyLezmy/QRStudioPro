# Packaging Desktop (Windows + macOS)

## 1) Prerequisites

Installe les dépendances dans ton environnement Python (sur chaque OS):

```bash
pip install -r requirements.txt
```

## 2) Icône de l'application

- Le fichier source est `../../shared/assets/app_icon.png`.
- Si besoin, remplace-le par ton logo.
- Génération des formats d'icône:

```bash
python scripts/make_icons.py --source ../../shared/assets/app_icon.png
```

Ce script crée:
- `../../shared/assets/app_icon.ico` (Windows)
- `../../shared/assets/app_icon.icns` (macOS, seulement si `iconutil` est disponible, donc sur Mac)

Les logos intégrés utilisés par le GUI sont dans:
- `../../shared/assets/logos/logo_phusis.png`
- `../../shared/assets/logos/logo-romane-pena.webp`

## 3) Build Windows (.exe)

Dans PowerShell:

```powershell
./scripts/build_windows.ps1
```

Sortie:
- `dist/QRStudioPro.exe`

## 4) Build macOS (.app)

Sur macOS:

```bash
./scripts/build_macos.sh
```

Sortie:
- `dist/QRStudioPro.app`
- `dist/QRStudioPro-macos.dmg`

## 5) Notes importantes

- Le binaire est construit pour l'OS courant.  
  Exemple: pour un vrai `.exe`, build sur Windows; pour un vrai `.app`, build sur macOS.
- Sur macOS, pour distribuer publiquement, il faut ensuite signer/notariser l'app.
- L'icône de fenêtre est aussi chargée au runtime depuis le bundle `assets` généré par PyInstaller.
- En mode source (non packagé), l'app cherche d'abord dans `assets/` local puis fallback sur `../../shared/assets`.
- Priorité:
  - `assets/app_icon.ico` (prioritaire)
  - sinon `assets/app_icon.png`
  - sinon `assets/logos/logo_phusis.png`
- Le champ logo du GUI accepte aussi les tokens `builtin:*` (ex: `builtin:phusis`) au lieu d'exposer les chemins internes.

## 6) GitHub Actions (build auto)

Workflow inclus: `.github/workflows/desktop-build-release.yml`

- `workflow_dispatch`: build manuel Windows + macOS avec artifacts.
- `push` de tag `v*`: build puis création d'une GitHub Release avec:
  - `QRStudioPro.exe`
  - `QRStudioPro-macos.dmg`

Note: GitHub ajoute toujours automatiquement `Source code (zip)` et `Source code (tar.gz)` dans chaque release.
