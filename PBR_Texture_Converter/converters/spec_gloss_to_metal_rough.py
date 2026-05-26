# Spec/Gloss → Metal/Rough conversion
# Ported from F1shez/converter-material-pbr (MIT License)
# Original: WebGL shaders → Python/NumPy
#
# Algorithm:
#   1. Compute perceived brightness of diffuse and specular
#   2. Solve for metallic via quadratic formula (dielectric F0 = 0.04)
#   3. Derive base color by lerping between diffuse-based and specular-based estimates
#   4. Roughness = 1 - glossiness

import numpy as np
from PIL import Image
import os


DIELECTRIC_F0 = 0.04
EPSILON = 1e-6


def _brightness(r: np.ndarray, g: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Perceived brightness (same formula as the original shader)."""
    return np.sqrt(r * r * 0.299 + g * g * 0.587 + b * b * 0.114)


def _solve_metallic(
    diff_brightness: np.ndarray,
    spec_brightness: np.ndarray,
    one_minus_spec_strength: np.ndarray,
) -> np.ndarray:
    """Quadratic solve for metallic value (port of GLSL solveMetallic)."""
    metallic = np.zeros_like(diff_brightness)

    mask = spec_brightness >= DIELECTRIC_F0

    a = DIELECTRIC_F0
    b = (
        diff_brightness[mask] * one_minus_spec_strength[mask] / (1.0 - DIELECTRIC_F0)
        + spec_brightness[mask]
        - 2.0 * DIELECTRIC_F0
    )
    c = DIELECTRIC_F0 - spec_brightness[mask]
    D = np.maximum(b * b - 4.0 * a * c, 0.0)
    metallic[mask] = np.clip((-b + np.sqrt(D)) / (2.0 * a), 0.0, 1.0)

    return metallic


def convert(
    diffuse_path: str,
    specular_path: str,
    glossiness_path: str,
):
    """
    Convert Specular/Glossiness workflow textures to Metallic/Roughness.

    Returns:
        (albedo_image, metallic_image, roughness_image) — PIL Images
    """
    # Load images
    diffuse_img = Image.open(diffuse_path).convert("RGB")
    specular_img = Image.open(specular_path).convert("RGB")
    glossiness_img = Image.open(glossiness_path).convert("L")

    # Resize specular & gloss to match diffuse if needed
    w, h = diffuse_img.size
    if specular_img.size != (w, h):
        specular_img = specular_img.resize((w, h), Image.LANCZOS)
    if glossiness_img.size != (w, h):
        glossiness_img = glossiness_img.resize((w, h), Image.LANCZOS)

    # Normalise to 0‑1 float
    diff = np.asarray(diffuse_img, dtype=np.float64) / 255.0
    spec = np.asarray(specular_img, dtype=np.float64) / 255.0
    gloss = np.asarray(glossiness_img, dtype=np.float64) / 255.0

    diff_r, diff_g, diff_b = diff[..., 0], diff[..., 1], diff[..., 2]
    spec_r, spec_g, spec_b = spec[..., 0], spec[..., 1], spec[..., 2]

    # ── Step 1: Metallic ─────────────────────────────────────────────
    one_minus_spec_strength = 1.0 - np.maximum(spec_r, np.maximum(spec_g, spec_b))
    diff_bright = _brightness(diff_r, diff_g, diff_b)
    spec_bright = _brightness(spec_r, spec_g, spec_b)

    metallic = _solve_metallic(diff_bright, spec_bright, one_minus_spec_strength)

    # ── Step 2: Base Color (Albedo) ──────────────────────────────────
    # From diffuse
    denom_diff = np.maximum(1.0 - metallic, EPSILON)
    base_from_diff = diff * (one_minus_spec_strength[..., np.newaxis]
                             / (1.0 - DIELECTRIC_F0)
                             / denom_diff[..., np.newaxis])

    # From specular
    denom_spec = np.maximum(metallic, EPSILON)
    base_from_spec = spec - (DIELECTRIC_F0 * (1.0 / denom_spec[..., np.newaxis])
                             * (1.0 - metallic[..., np.newaxis]))
    base_from_spec = np.clip(base_from_spec, 0.0, 1.0)

    # Lerp
    met3 = metallic[..., np.newaxis]
    albedo = base_from_diff + met3 * (base_from_spec - base_from_diff)
    albedo = np.clip(albedo, 0.0, 1.0)

    # ── Step 3: Roughness ────────────────────────────────────────────
    roughness = 1.0 - gloss

    # ── Convert back to PIL Images ───────────────────────────────────
    albedo_out = Image.fromarray((albedo * 255).astype(np.uint8), "RGB")
    metallic_out = Image.fromarray((metallic * 255).astype(np.uint8), "L")
    roughness_out = Image.fromarray((roughness * 255).astype(np.uint8), "L")

    return albedo_out, metallic_out, roughness_out
