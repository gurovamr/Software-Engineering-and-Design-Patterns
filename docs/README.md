# Documentation

This folder keeps documentation sources and generated inspection files separate.

## Source files

- `class_overview.md` - editable source for the class overview.
- `uml_description.puml` - editable PlantUML source for all UML diagrams.
- `render_docs.ps1` - regenerates every file in `generated/`.

## Generated files

Generated files live in `generated/` and are committed for easy review on GitHub:

- `class_overview.html`
- `uml_description_view.html`
- `uml_*.png`

Run this command from the repository root after changing the source files:

```powershell
powershell -ExecutionPolicy Bypass -File docs\render_docs.ps1
```
