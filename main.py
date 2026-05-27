"""
PBR Maps Converter
==================
Unified tool for converting PBR texture maps between workflows:
  • Specular/Glossiness  →  Metallic/Roughness
  • Metallic/Roughness   →  Specular/Glossiness

Based on:
  - F1shez/converter-material-pbr (MIT)  — Spec/Gloss → Metal/Rough algorithm
  - prov3ntus/Lambda (GPL-3.0)           — Metal/Rough → Spec/Gloss algorithm
"""

import sys
import os

# Ensure the project root is importable when running from source or frozen exe
if getattr(sys, "frozen", False):
    _root = sys._MEIPASS
else:
    _root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from gui.app import PBRConverterApp


def main():
    app = PBRConverterApp()
    app.run()


if __name__ == "__main__":
    main()
