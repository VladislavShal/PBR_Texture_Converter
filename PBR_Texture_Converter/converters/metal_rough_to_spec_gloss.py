# Metal/Rough → Spec/Gloss conversion
# Ported from prov3ntus/Lambda (GPL-3.0 License)
# Original: PIL compositing → Python/NumPy
#
# Algorithm:
#   1. Diffuse  = composite(black, albedo, metallic_mask)
#      → where metallic is high, diffuse goes to black (metals have no diffuse)
#   2. Specular = composite(F0(56,56,56), albedo, inverted_metallic_mask)
#      → metals reflect their albedo; dielectrics reflect F0 ≈ (56,56,56)
#   3. Glossiness = 1 - roughness  (new feature, not in original Lambda)

import numpy as np
from PIL import Image
import os


DIELECTRIC_F0 = 56  # ≈ 0.04 * 255 ≈ 10, but Lambda uses 56 (≈ 0.22) — kept for compatibility


def convert(albedo_path: str, metallic_path: str, roughness_path: str):
    """
    Convert Metallic/Roughness workflow textures to Specular/Glossiness.

    Returns:
        (diffuse_image, specular_image, glossiness_image) — PIL Images
    """
    # Load images
    albedo_img = Image.open(albedo_path).convert("RGB")
    metallic_img = Image.open(metallic_path).convert("L")
    roughness_img = Image.open(roughness_path).convert("L")

    w, h = albedo_img.size
    if metallic_img.size != (w, h):
        metallic_img = metallic_img.resize((w, h), Image.LANCZOS)
    if roughness_img.size != (w, h):
        roughness_img = roughness_img.resize((w, h), Image.LANCZOS)

    # Normalise to 0‑1 float
    albedo = np.asarray(albedo_img, dtype=np.float64) / 255.0
    metallic = np.asarray(metallic_img, dtype=np.float64) / 255.0
    roughness = np.asarray(roughness_img, dtype=np.float64) / 255.0

    met3 = metallic[..., np.newaxis]  # broadcast to 3 channels

    # ── Step 1: Diffuse ──────────────────────────────────────────────
    # composite(black, albedo, mask=metallic)
    # Where metallic=1 → black, where metallic=0 → albedo
    diffuse = albedo * (1.0 - met3)

    # ── Step 2: Specular ─────────────────────────────────────────────
    # composite(F0, albedo, mask=inverted_metallic)
    # Where metallic=1 → albedo (metal reflects its own color)
    # Where metallic=0 → F0 dielectric reflectance
    f0_normalized = DIELECTRIC_F0 / 255.0
    specular = f0_normalized * (1.0 - met3) + albedo * met3

    # ── Step 3: Glossiness ───────────────────────────────────────────
    glossiness = 1.0 - roughness

    # ── Clamp & convert back to PIL Images ───────────────────────────
    diffuse = np.clip(diffuse, 0.0, 1.0)
    specular = np.clip(specular, 0.0, 1.0)
    glossiness = np.clip(glossiness, 0.0, 1.0)

    diffuse_out = Image.fromarray((diffuse * 255).astype(np.uint8), "RGB")
    specular_out = Image.fromarray((specular * 255).astype(np.uint8), "RGB")
    glossiness_out = Image.fromarray((glossiness * 255).astype(np.uint8), "L")

    return diffuse_out, specular_out, glossiness_out
