# PBR Texture Converter

An elegant, bidirectional, and high-performance utility designed to seamlessly translate texture maps between physically-based rendering (PBR) workflows: **Specular/Glossiness** ↔ **Metallic/Roughness**. 

Built with a highly polished, modern dark theme interface, the tool features real-time visual previews, thread-safe asynchronous processing, robust batch conversions, and full Windows Immersive Dark Mode integration.

---

## Key Features

*   **Bidirectional Conversion Pipelines**:
    *   **Specular/Glossiness ➔ Metallic/Roughness** (Diffuse, Specular, Glossiness ➔ Base Color, Metallic, Roughness)
    *   **Metallic/Roughness ➔ Specular/Glossiness** (Base Color, Metallic, Roughness ➔ Diffuse, Specular, Glossiness)
*   **Highly Responsive UI & Aesthetics**: Modern glassmorphism card panels with vibrant blue and emerald mint accents, featuring responsive hover transitions and locked window scales.
*   **Immersive Title Bar Integration**: Perfect Windows dark title bar integration instantly on startup across both the main window and all popup dialogs.
*   **Live High-Fidelity Previews**: Built-in thumbnail preview visualizers for both input slots and generated output slots that render instantly during drag-and-drop or conversions.
*   **Click-to-Expand Premium Modals**: Clicking any thumbnail opens a premium modal window showing a high-resolution preview along with detailed image metadata (dimensions, format, file size).
*   **Robust Batch Conversion Mode**: 
    *   Detects and groups material texture sets dynamically by name and role using active-workflow suffix filtering (e.g. `_diffuse`, `_roughness`).
    *   Ignores incompatible map types automatically to prevent invalid workflows.
    *   Supports batch converting dozens of materials simultaneously with optional **MRA packing** (Metallic in Red, Roughness in Green, AO in Blue).
*   **Non-Blocking Multithreaded Engine**: All file reading, image resizing, and conversions run in background threads to guarantee zero application freezes.
*   **Fast Directory Navigation**: One-click "Open Output Folder" action to launch Windows Explorer directly in your conversion folder.
*   **Drag-and-Drop Support**: Native drag-and-drop interface via `tkinterdnd2` for swift map importing.

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
