# QR Studio Pro Webapp

Webapp SPA (React + Vite + TypeScript) pour générer des QR codes stylisés avec les mêmes capacités que la version Python desktop.

## Features

- Presets intégrés: `black_bg_safe`, `full_dark_artistic`, `white_clean`, `luxury`, `pena_psychologue`
- Presets personnalisés: sauvegarde locale, import/export JSON
- Logos intégrés: Phusis, Romane Pena
- Logo custom: drag & drop, sélection fichier, URL
- Édition exhaustive des paramètres graphiques (couleurs, formes, fond, FX, medallion, logo)
- Preview live (option auto preview) + decode check
- Export `png`, `webp`, `jpeg`, `svg`
- Responsive, single page

## Start

```bash
cd webapp
npm install
npm run dev
```

## Build

```bash
cd webapp
npm run build
npm run preview
```

## Notes

- Le rendu SVG exporté est un SVG QR vectoriel propre (sans effets raster), fidèle au comportement Python.
- Les logos intégrés passent par `public/logos/*`.
