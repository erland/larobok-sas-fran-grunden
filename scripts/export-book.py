#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parents[1]


def read_yaml(path: Path) -> dict:
    if yaml is None:
        raise SystemExit("PyYAML saknas. Installera med: python3 -m pip install pyyaml")
    if not path.exists():
        raise SystemExit(f"Saknar metadatafil: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate_metadata(meta: dict) -> None:
    required = ["title", "author", "language", "identifier", "date", "version", "chapters"]
    missing = [key for key in required if not meta.get(key)]
    if missing:
        raise SystemExit("Metadata saknar obligatoriska fält: " + ", ".join(missing))
    if meta["language"] not in {"sv", "en"}:
        raise SystemExit("language måste vara 'sv' eller 'en'.")
    chapters = meta.get("chapters") or []
    if not chapters or chapters[0] != "chapters/00-inledning.md":
        raise SystemExit("Första kapitel måste vara chapters/00-inledning.md.")


def count_table_cells(line: str) -> int:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return -1
    return len([c for c in stripped.strip("|").split("|")])


def validate_markdown(path: Path, text: str) -> list[str]:
    warnings: list[str] = []
    if re.search(r"^#{4,}\s", text, re.MULTILINE):
        warnings.append(f"{path}: innehåller H4 eller djupare rubriker.")
    if text.count("```") % 2:
        warnings.append(f"{path}: ojämnt antal kodblockmarkörer.")
    lines = text.splitlines()
    table_rows_covered: set[int] = set()
    separator_re = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
    for i, line in enumerate(lines):
        if i in table_rows_covered:
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            if i + 1 < len(lines) and separator_re.match(lines[i + 1]):
                expected = count_table_cells(line)
                table_rows_covered.add(i)
                table_rows_covered.add(i + 1)
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|") and lines[j].strip().endswith("|"):
                    table_rows_covered.add(j)
                    if count_table_cells(lines[j]) != expected:
                        warnings.append(f"{path}: tabellrad {j+1} har fel antal celler.")
                    j += 1
            elif i == 0 or not separator_re.match(lines[i]):
                warnings.append(f"{path}: möjlig tabell utan separatorrad nära rad {i+1}.")
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
        img = match.group(1)
        if not img.startswith(("http://", "https://")):
            img_path = (path.parent / img).resolve()
            if not img_path.exists():
                warnings.append(f"{path}: bildreferens saknar fil: {img}")
    return warnings


def build_combined_markdown(meta: dict) -> Path:
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    out = build / "book.md"
    parts = []
    all_warnings = []
    for rel in meta["chapters"]:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"Saknar kapitel: {rel}")
        text = path.read_text(encoding="utf-8")
        all_warnings.extend(validate_markdown(path, text))
        parts.append(text.strip() + "\n")
    if all_warnings:
        raise SystemExit("Markdownvalidering stoppade exporten:\n" + "\n".join(all_warnings))
    out.write_text("\n\n".join(parts), encoding="utf-8")
    return out


def run_pandoc(meta: dict, source: Path, formats: list[str]) -> None:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise SystemExit("Pandoc saknas. Installera Pandoc och kör sedan scriptet igen.")
    exports = ROOT / "exports"
    exports.mkdir(exist_ok=True)
    lang = "sv-SE" if meta["language"] == "sv" else "en-US"
    base = meta.get("project_slug") or "book"

    if "epub" in formats:
        cmd = [
            pandoc, str(source), "--from=gfm", "--to=epub3",
            "--metadata", f"title={meta['title']}",
            "--metadata", f"author={meta['author']}",
            "--metadata", f"lang={lang}",
            "--css=styles/epub.css",
            "--epub-cover-image=assets/cover/cover.png" if (ROOT / "assets" / "cover" / "cover.png").exists() else "",
            "--output", str(exports / f"{base}.epub"),
        ]
        cmd = [part for part in cmd if part]
        subprocess.run(cmd, cwd=ROOT, check=True)

    if "pdf" in formats:
        cmd = [
            pandoc, str(source), "--from=gfm",
            "--pdf-engine=xelatex",
            "--toc", "--toc-depth=3",
            "--metadata", f"title={meta['title']}",
            "--metadata", f"author={meta['author']}",
            "--metadata", f"lang={lang}",
            "--output", str(exports / f"{base}.pdf"),
        ]
        try:
            subprocess.run(cmd, cwd=ROOT, check=True)
        except FileNotFoundError:
            raise SystemExit("xelatex saknas. Installera MacTeX/TinyTeX eller ange annan Pandoc-kompatibel PDF-engine.")
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"PDF-export misslyckades. Kontrollera att xelatex finns installerat. Felkod: {exc.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exportera bokprojekt till EPUB/PDF lokalt.")
    parser.add_argument("--format", choices=["epub", "pdf", "all"], default="all")
    args = parser.parse_args()

    meta_path = ROOT / "docs" / "export-metadata.yaml"
    meta = read_yaml(meta_path)
    validate_metadata(meta)
    combined = build_combined_markdown(meta)

    formats = ["epub", "pdf"] if args.format == "all" else [args.format]
    run_pandoc(meta, combined, formats)
    print("Export klar. Se exports/.")


if __name__ == "__main__":
    main()
