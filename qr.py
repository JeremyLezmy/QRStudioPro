from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from qr_presets import list_presets, load_graphic_overrides

DEFAULT_OUTPUT_PATH = Path("generated_qrcode/qr_output.png")


def _parse_logo_path(raw_logo: Optional[str]) -> Optional[Path]:
    if raw_logo is None:
        return None

    normalized = raw_logo.strip().lower()
    if normalized in {"none", "null", "no", "sans"}:
        return None

    return Path(raw_logo)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genere un QR code stylise avec presets graphiques."
    )
    parser.add_argument("--url", help="URL a encoder dans le QR code")
    parser.add_argument(
        "--preset",
        default="black_bg_safe",
        choices=list_presets(),
        help="Nom du preset graphique",
    )
    parser.add_argument(
        "--logo",
        default=None,
        help="Chemin du logo (utiliser 'none' pour ne pas mettre de logo)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Chemin de sortie de l'image generee",
    )
    parser.add_argument(
        "--graphic-config",
        default=None,
        help="Chemin vers un JSON d'overrides graphiques",
    )
    parser.add_argument(
        "--no-decode-check",
        action="store_true",
        help="Desactive la verification OpenCV du QR genere",
    )
    parser.add_argument(
        "--logo-keep-original",
        action="store_true",
        help="Conserve le logo tel quel (pas de recolor / pas de suppression de fond)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Desactive les logs de generation",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Affiche la liste des presets disponibles",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_presets:
        print("Presets disponibles:")
        for preset_name in list_presets():
            print(f"- {preset_name}")
        return 0

    if not args.url:
        parser.error("--url est obligatoire (sauf avec --list-presets)")

    logo_path = _parse_logo_path(args.logo)

    graphic_overrides = None
    if args.graphic_config:
        graphic_overrides = load_graphic_overrides(Path(args.graphic_config))
    if args.logo_keep_original:
        if graphic_overrides is None:
            graphic_overrides = {}
        graphic_overrides["logo_keep_original"] = True

    from generate_qrcode import BrandedQRGenerator, create_qr_config

    cfg = create_qr_config(
        url=args.url,
        preset_name=args.preset,
        logo_path=logo_path,
        output_path=Path(args.output),
        graphic_overrides=graphic_overrides,
        run_decode_check=not args.no_decode_check,
        verbose=not args.quiet,
    )

    BrandedQRGenerator(cfg).save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
