# Sås från grunden

Detta är projektmappen för boken **Sås från grunden** av Erland Lindmark.

## Syfte

Boken lär nybörjare att förstå, laga och utveckla såser för modern hemmamat. Den kombinerar praktiska steg, tydliga smakförklaringar och klassiska tekniker i en progression från grundläggande begrepp till egna såser.

## Projektstruktur

- `chapters/` innehåller manus.
- `docs/` innehåller bokspecifikation, kapitelplan, status och metadata.
- `assets/cover/` är platsen för omslagsbild.
- `assets/image-prompts/` innehåller prompt för omslaget.
- `styles/` innehåller CSS för EPUB/PDF.
- `scripts/` innehåller lokal exportpipeline.
- `exports/` är målplats för genererade filer.

## Export

Kör lokalt:

```bash
bash scripts/export-book.sh
```

Scriptet validerar metadata och markdown innan EPUB/PDF skapas.
