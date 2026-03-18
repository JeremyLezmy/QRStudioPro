# QR Studio Pro Monorepo

Monorepo contenant deux applications:

- `apps/qr-desktop-python`: application desktop Python (CLI + GUI CustomTkinter + packaging Windows/macOS)
- `apps/qr-web`: web app React + Vite + TypeScript

## Structure

```txt
apps/
  qr-desktop-python/
  qr-web/
shared/
  assets/
  presets/
```

## Quick Start

### Desktop Python

```bash
cd apps/qr-desktop-python
pip install -r requirements.txt
python qr_gui.py
```

### Web App

```bash
cd apps/qr-web
npm install
npm run dev
```

## CI/CD

- Build/release desktop: `.github/workflows/desktop-build-release.yml`

## Documentation

- Desktop: [`apps/qr-desktop-python/README.md`](apps/qr-desktop-python/README.md)
- Packaging desktop: [`apps/qr-desktop-python/PACKAGING.md`](apps/qr-desktop-python/PACKAGING.md)
- Web: [`apps/qr-web/README.md`](apps/qr-web/README.md)
