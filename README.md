# PBR Texture Converter

A lightweight utility for converting texture maps between physically-based rendering (PBR) workflows:

**Specular/Glossiness ↔ Metallic/Roughness**

Designed for artists and technical artists working with assets from different engines, marketplaces, and rendering pipelines.

---

## Features

### Bidirectional Conversion

- Specular/Glossiness → Metallic/Roughness  
- Metallic/Roughness → Specular/Glossiness  

Supports standard PBR conversion workflows using physically-based formulas.

---

### Batch Conversion

- Automatically groups texture sets by material name
- Supports converting entire folders at once
- Ignores incompatible texture types automatically

---

### MRA Packing

Optional channel packing:
- Metallic → Red
- Roughness → Green
- AO → Blue

---

### Preview System

Built-in previews for input and converted textures.

---

### Drag & Drop Support

Quickly import texture maps using drag-and-drop.

---

## Getting Started

### Prerequisites

Ensure you have Python 3.10+ installed. Install the necessary libraries using `pip`:

```bash
pip install customtkinter Pillow tkinterdnd2
```

### Running from Source

Simply run the `main.py` script:

```bash
python main.py
```

### Compiling to a Standalone Executable (.exe)

You can build a single, self-contained Windows executable by using `pyinstaller` with the pre-configured `.spec` file:

```bash
pip install pyinstaller
pyinstaller --clean PBR_Maps_Converter.spec
```

The compiled standalone executable will be generated at `dist/PBR_Maps_Converter.exe`.

---

## Acknowledgments & Credits

Developed with ♥ by **Vladislav Sh.**

Mathematical algorithms and workflow calculations are based on standard PBR translation principles and adapted from:
- **F1shez/converter-material-pbr** (MIT) — Spec/Gloss to Metal/Rough algorithms.
- **prov3ntus/Lambda** (GPL-3.0) — Metal/Rough to Spec/Gloss algorithms.

---

## License

This project is licensed under the **GNU General Public License, Version 3 (GPL-3.0)**. See the `LICENSE` file for details.
