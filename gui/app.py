"""
PBR Maps Converter — Modern GUI (customtkinter)
Highly polished Dark Theme with blue/mint accents, rounded panels.
Fully reactive layout matching reference design.
Native Windows file drag-and-drop via tkinterdnd2.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    TkinterDnD.DnDWrapper()
    HAS_DND = True
except Exception:
    HAS_DND = False

# Resolve imports when running from PyInstaller bundle
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from converters import spec_gloss_to_metal_rough, metal_rough_to_spec_gloss

# ── Color Palette & Styling ──────────────────────────────────────────
BG_OUTER      = "#0a0d14"   # Ultra dark charcoal background
BG_PANEL      = "#121620"   # Sleek dark slate card background
BG_SLOT       = "#1a1f2c"   # Individual map slots background
BG_SLOT_HOVER = "#242b3d"   # Slot hover background
BORDER_CLR    = "#272f3d"   # Sleek border outline
ACCENT_BLUE   = "#0ea5e9"   # Premium Sky Blue
ACCENT_MINT   = "#10b981"   # Emerald Green success
FG_TITLE      = "#f9fafb"   # High contrast off-white text
FG_TEXT       = "#e5e7eb"   # Main readable text
FG_DIM        = "#9ca3af"   # Muted hints/labels
ERROR_CLR     = "#ef4444"   # Vibrant red for errors

FONT_FAMILY   = "Segoe UI"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".tga", ".exr"}
DIFF_SUFFIXES = ("_diff", "_diffuse", "_color", "_colour", "_col", "_albedo", "_bc")
SPEC_SUFFIXES = ("_spec", "_specular", "_metal", "_metallic", "_m")
GLOSS_SUFFIXES = ("_gloss", "_glossiness", "_rough", "_roughness", "_r")


# ── Helper functions ────────────────────────────────────────────────
def _parse_drop_paths(data: str):
    """Parse tkinterdnd2 drop data into a list of file paths."""
    paths = []
    current = []
    in_braces = False
    for ch in data:
        if ch == '{':
            in_braces = True
            continue
        if ch == '}':
            in_braces = False
            paths.append("".join(current))
            current = []
            continue
        if ch == ' ' and not in_braces:
            if current:
                paths.append("".join(current))
                current = []
            continue
        current.append(ch)
    if current:
        paths.append("".join(current))
    return [os.path.normpath(p) for p in paths if p.strip()]


def _strip_role_suffix(path: str, workflow: str):
    stem = os.path.splitext(os.path.basename(path))[0]
    lower_stem = stem.lower()
    
    # Workflow-specific suffixes mapping
    if workflow == "SG":
        suffixes_map = {
            "diff": ("_diff", "_diffuse", "_color", "_colour", "_col"),
            "spec": ("_spec", "_specular"),
            "gloss": ("_gloss", "_glossiness"),
        }
    else: # MR
        suffixes_map = {
            "diff": ("_albedo", "_bc", "_color", "_colour", "_col"),
            "spec": ("_metal", "_metallic", "_m"),
            "gloss": ("_rough", "_roughness", "_r"),
        }
        
    for role, suffixes in suffixes_map.items():
        for suffix in suffixes:
            if lower_stem.endswith(suffix):
                return stem[: -len(suffix)], role
    return stem, None


def _is_image_file(path: str):
    return os.path.isfile(path) and os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def apply_dark_title_bar(window):
    """Force Windows Immersive Dark Mode on the given window's title bar."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            if hwnd == 0:
                hwnd = window.winfo_id()
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attr,
                    ctypes.byref(ctypes.c_int(1)),
                    ctypes.sizeof(ctypes.c_int(1))
                )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
class ImagePopup(ctk.CTkToplevel):
    """A premium modal pop-up window showing full-res image details."""

    def __init__(self, parent, image_path: str, label_text: str):
        super().__init__(parent)
        self.title(f"Image Preview - {os.path.basename(image_path)}")
        self.geometry("540x620")
        self.resizable(False, False)
        self.configure(fg_color=BG_OUTER)

        # Set child window icon and force dark title bar with safety delays
        def _set_icon_and_theme():
            if hasattr(parent, "icon_path") and os.path.exists(parent.icon_path):
                try:
                    self.iconbitmap(parent.icon_path)
                except Exception:
                    pass
            apply_dark_title_bar(self)

        self.after(10, lambda: apply_dark_title_bar(self))
        self.after(100, lambda: apply_dark_title_bar(self))
        self.after(200, _set_icon_and_theme)

        # Force window on top and grab focus (modal behavior)
        self.transient(parent)
        self.grab_set()

        # Center relative to parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 540) // 2
        y = parent_y + (parent_h - 620) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        # Title / Type
        title_lbl = ctk.CTkLabel(
            self,
            text=f"{label_text.upper()} MAP DETAILS",
            font=(FONT_FAMILY, 14, "bold"),
            text_color=ACCENT_BLUE
        )
        title_lbl.pack(pady=(16, 6))

        # Photo Container (Rounded border)
        img_frame = ctk.CTkFrame(
            self,
            width=460,
            height=460,
            fg_color=BG_PANEL,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=12
        )
        img_frame.pack(pady=10)
        img_frame.pack_propagate(False)

        img_label = ctk.CTkLabel(img_frame, text="Loading image...")
        img_label.pack(fill="both", expand=True)

        # Detail text
        self.detail_lbl = ctk.CTkLabel(
            self,
            text="Gathering metadata...",
            font=(FONT_FAMILY, 10),
            text_color=FG_DIM,
            justify="center"
        )
        self.detail_lbl.pack(pady=(4, 12))

        # Close button
        close_btn = ctk.CTkButton(
            self,
            text="Close Preview",
            font=(FONT_FAMILY, 12, "bold"),
            fg_color=BORDER_CLR,
            hover_color=BG_SLOT_HOVER,
            text_color=FG_TITLE,
            corner_radius=8,
            command=self.destroy
        )
        close_btn.pack(pady=(0, 16))

        # Bind escape key to close
        self.bind("<Escape>", lambda e: self.destroy())

        # Load image asynchronously to prevent UI freezing
        threading.Thread(target=self._load_image, args=(image_path, img_label), daemon=True).start()

    def _load_image(self, path, label_widget):
        try:
            with Image.open(path) as img:
                w, h = img.size
                mode = img.mode
                size_bytes = os.path.getsize(path)
                size_mb = size_bytes / (1024 * 1024)

                # Resize to fit 440x440
                preview_img = img.copy()
                preview_img.thumbnail((440, 440), Image.Resampling.BILINEAR)

                # Handle transparency checkerboard
                if preview_img.mode in ("RGBA", "LA") or (preview_img.mode == "P" and "transparency" in preview_img.info):
                    bg = Image.new("RGBA", preview_img.size, (28, 33, 44, 255))
                    preview_img = Image.alpha_composite(bg, preview_img.convert("RGBA")).convert("RGB")
                else:
                    preview_img = preview_img.convert("RGB")

                # Setup CTkImage
                self.ctk_img = ctk.CTkImage(
                    light_image=preview_img,
                    dark_image=preview_img,
                    size=preview_img.size
                )

                details = f"File: {os.path.basename(path)}\nDimensions: {w} × {h} pixels   |   Format: {mode}   |   Size: {size_mb:.2f} MB"

                def _update_ui():
                    label_widget.configure(image=self.ctk_img, text="")
                    self.detail_lbl.configure(text=details)

                self.after(0, _update_ui)
        except Exception as e:
            def _error_ui():
                label_widget.configure(text=f"Failed to load image.\n{e}", text_color=ERROR_CLR)
                self.detail_lbl.configure(text="Error loading image details.")
            self.after(0, _error_ui)


# ══════════════════════════════════════════════════════════════════════
class HelpPopup(ctk.CTkToplevel):
    """An elegant modal popup describing the application details and author."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("About PBR Texture Converter")
        self.geometry("450x440")
        self.resizable(False, False)
        self.configure(fg_color=BG_OUTER)

        # Set child window icon and force dark title bar with safety delays
        def _set_icon_and_theme():
            if hasattr(parent, "icon_path") and os.path.exists(parent.icon_path):
                try:
                    self.iconbitmap(parent.icon_path)
                except Exception:
                    pass
            apply_dark_title_bar(self)

        self.after(10, lambda: apply_dark_title_bar(self))
        self.after(100, lambda: apply_dark_title_bar(self))
        self.after(200, _set_icon_and_theme)

        self.transient(parent)
        self.grab_set()

        # Center relative to parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 450) // 2
        y = parent_y + (parent_h - 440) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        # Logo Image
        logo_lbl = None
        if hasattr(parent, "icon_path") and os.path.exists(parent.icon_path):
            try:
                with Image.open(parent.icon_path) as img:
                    # Open frame and resize safely
                    logo_img = img.convert("RGBA").resize((60, 60), Image.Resampling.BILINEAR)
                    self.logo_ctk_img = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(60, 60))
                    logo_lbl = ctk.CTkLabel(self, image=self.logo_ctk_img, text="")
                    logo_lbl.pack(pady=(20, 0))
            except Exception:
                pass

        # Logo / Header
        header = ctk.CTkLabel(
            self,
            text="PBR Texture Converter",
            font=(FONT_FAMILY, 18, "bold"),
            text_color=ACCENT_BLUE
        )
        header.pack(pady=(10 if logo_lbl else 24, 4))

        version = ctk.CTkLabel(
            self,
            text="v2.0 (Public Release)",
            font=(FONT_FAMILY, 10, "italic"),
            text_color=FG_DIM
        )
        version.pack(pady=(0, 16))

        # Main Info Panel
        info_panel = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=10
        )
        info_panel.pack(padx=20, fill="both", expand=True)

        desc = (
            "PBR Texture Converter is an elegant, bi-directional utility designed "
            "to translate texture maps seamlessly between physically-based rendering workflows "
            "(Specular/Glossiness ↔ Metallic/Roughness).\n\n"
            "It utilizes standard, mathematically documented equations to provide a robust "
            "starting point. However, minor manual artistic fine-tuning may still be helpful "
            "to achieve perfect visual parity under specific light environments."
        )

        desc_lbl = ctk.CTkLabel(
            info_panel,
            text=desc,
            font=(FONT_FAMILY, 11),
            text_color=FG_TEXT,
            wraplength=370,
            justify="left"
        )
        desc_lbl.pack(padx=16, pady=16)

        # Developer Info
        dev_lbl = ctk.CTkLabel(
            self,
            text="Developed with \u2665 by Vladislav Sh.",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=ACCENT_MINT
        )
        dev_lbl.pack(pady=(12, 12))

        # Close
        close_btn = ctk.CTkButton(
            self,
            text="Dismiss",
            font=(FONT_FAMILY, 12, "bold"),
            fg_color=BORDER_CLR,
            hover_color=BG_SLOT_HOVER,
            text_color=FG_TITLE,
            corner_radius=8,
            command=self.destroy
        )
        close_btn.pack(pady=(0, 20))

        self.bind("<Escape>", lambda e: self.destroy())


# ══════════════════════════════════════════════════════════════════════
class ClickablePreview(ctk.CTkFrame):
    """A beautiful square preview thumbnail that triggers full preview modal on click."""

    def __init__(self, parent, label_text: str, click_callback, size=90):
        super().__init__(parent, fg_color="transparent")
        self.label_text = label_text
        self.click_callback = click_callback
        self.size = size
        self.image_path = None
        self.pil_img = None
        self.ctk_img = None

        # Image Slot
        self.img_frame = ctk.CTkFrame(
            self,
            width=size,
            height=size,
            fg_color=BG_SLOT,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=10
        )
        self.img_frame.pack(pady=(0, 4))
        self.img_frame.pack_propagate(False)

        self.img_label = None
        self._recreate_img_label(text="Empty", image=None)

        # Bottom label
        self.text_label = ctk.CTkLabel(
            self,
            text=label_text,
            font=(FONT_FAMILY, 10),
            text_color=FG_DIM
        )
        self.text_label.pack()

        # Bind hover and click actions
        self.img_frame.bind("<Button-1>", self._on_click)
        self.img_frame.bind("<Enter>", self._on_enter)
        self.img_frame.bind("<Leave>", self._on_leave)

    def _recreate_img_label(self, text="", image=None):
        if hasattr(self, "img_label") and self.img_label:
            try:
                self.img_label.destroy()
            except Exception:
                pass

        self.img_label = ctk.CTkLabel(
            self.img_frame,
            text=text,
            image=image,
            font=(FONT_FAMILY, 9),
            text_color=FG_DIM
        )
        self.img_label.pack(fill="both", expand=True)

        # Bind hover and click actions to the newly created label
        self.img_label.bind("<Button-1>", self._on_click)
        self.img_label.bind("<Enter>", self._on_enter)
        self.img_label.bind("<Leave>", self._on_leave)

    def _on_click(self, event):
        if self.image_path:
            self.click_callback(self.image_path, self.label_text)

    def _on_enter(self, event):
        if self.image_path:
            self.img_frame.configure(border_color=ACCENT_BLUE)

    def _on_leave(self, event):
        if self.image_path:
            self.img_frame.configure(border_color=BORDER_CLR)

    def update_image(self, path: str | None):
        """Update the preview image. Fully safe for repeated calls in any state."""
        # Hold old references alive until widget is reconfigured
        _old_ctk = self.ctk_img
        _old_pil = self.pil_img

        self.image_path = path

        if not path:
            self.ctk_img = None
            self.pil_img = None
            try:
                self._recreate_img_label(text="Empty", image=None)
            except Exception:
                pass
            return

        try:
            with Image.open(path) as img:
                preview_img = img.copy()
                preview_img.thumbnail((self.size, self.size), Image.Resampling.BILINEAR)

                if preview_img.mode in ("RGBA", "LA") or (preview_img.mode == "P" and "transparency" in preview_img.info):
                    bg = Image.new("RGBA", preview_img.size, (36, 42, 55, 255))
                    preview_img = Image.alpha_composite(bg, preview_img.convert("RGBA")).convert("RGB")
                else:
                    preview_img = preview_img.convert("RGB")

                self.pil_img = preview_img.copy()

            self.ctk_img = ctk.CTkImage(
                light_image=self.pil_img,
                dark_image=self.pil_img,
                size=(self.size, self.size)
            )
            try:
                self._recreate_img_label(text="", image=self.ctk_img)
            except Exception:
                pass
        except Exception:
            self.ctk_img = None
            self.pil_img = None
            try:
                self._recreate_img_label(text="Err", image=None)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════
class DropZone(ctk.CTkFrame):
    """An elegant drag-and-drop file receiver that supports thumbnails."""

    def __init__(self, parent, label_text: str, channel_char: str = "D", file_changed_callback=None, **kw):
        super().__init__(
            parent,
            fg_color=BG_SLOT,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=12,
            width=104, # Fixed width to prevent squishing!
            height=114, # Fixed height to prevent squishing!
            **kw
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.file_path: str | None = None
        self._label_text = label_text
        self.channel_char = channel_char
        self.file_changed_callback = file_changed_callback
        self.slot_ctk_img = None

        # Internal container
        self.container = ctk.CTkFrame(self, fg_color="transparent", width=96, height=102)
        self.container.pack(fill="both", expand=True, padx=4, pady=6)
        self.container.pack_propagate(False)
        self.container.grid_propagate(False)

        # Icon Label / Slot Character
        self.icon_label = None
        self._recreate_icon_label(text=channel_char, image=None)

        # Title
        self.title_label = ctk.CTkLabel(
            self.container,
            text=label_text,
            font=(FONT_FAMILY, 11, "bold"),
            text_color=FG_TITLE
        )
        self.title_label.pack(pady=(0, 1))

        # Hint
        self.hint_label = ctk.CTkLabel(
            self.container,
            text="Drop / click",
            font=(FONT_FAMILY, 8),
            text_color=FG_DIM,
            wraplength=88
        )
        self.hint_label.pack(pady=(0, 2))

        # Bind events for interaction
        for widget in (self, self.container, self.title_label, self.hint_label):
            widget.bind("<Button-1>", self._browse)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.dnd_bind("<<DragLeave>>", self._on_drag_leave)

    def _recreate_icon_label(self, text="", image=None):
        if hasattr(self, "title_label"):
            self.title_label.pack_forget()
        if hasattr(self, "hint_label"):
            self.hint_label.pack_forget()

        if hasattr(self, "icon_label") and self.icon_label:
            try:
                self.icon_label.destroy()
            except Exception:
                pass

        self.icon_label = ctk.CTkLabel(
            self.container,
            text=text,
            image=image,
            font=(FONT_FAMILY, 18, "bold"),
            text_color=FG_DIM,
            fg_color=BG_OUTER,
            width=36,
            height=36,
            corner_radius=6
        )
        self.icon_label.pack(pady=(4, 2))

        if hasattr(self, "title_label"):
            self.title_label.pack(pady=(0, 1))
        if hasattr(self, "hint_label"):
            self.hint_label.pack(pady=(0, 2))

        # Bind events to the newly created icon label
        self.icon_label.bind("<Button-1>", self._browse)
        self.icon_label.bind("<Enter>", self._on_enter)
        self.icon_label.bind("<Leave>", self._on_leave)

    def _on_enter(self, _e=None):
        self.configure(fg_color=BG_SLOT_HOVER, border_color=ACCENT_BLUE)

    def _on_leave(self, _e=None):
        if self.file_path:
            self.configure(fg_color=BG_SLOT, border_color=ACCENT_MINT)
        else:
            self.configure(fg_color=BG_SLOT, border_color=BORDER_CLR)

    def _on_drag_enter(self, _e=None):
        self.configure(fg_color=BG_SLOT_HOVER, border_color=ACCENT_BLUE)

    def _on_drag_leave(self, _e=None):
        self._on_leave()

    def _browse(self, _event=None):
        path = filedialog.askopenfilename(
            title=f"Select {self._label_text}",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.tga *.exr"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.set_path(path)

    def _on_drop(self, event):
        paths = _parse_drop_paths(event.data)
        if paths:
            self.set_path(paths[0])

    def set_path(self, path: str):
        """Load a file into this slot. Fully safe for repeated calls."""
        # Hold old image reference alive until widget is reconfigured
        _old_img = self.slot_ctk_img

        self.file_path = os.path.normpath(path)
        name = os.path.basename(self.file_path)

        # Update visuals
        self.hint_label.configure(text=name, text_color=ACCENT_MINT)
        self.configure(border_color=ACCENT_MINT)

        # Load very fast miniature icon
        try:
            with Image.open(self.file_path) as img:
                min_img = img.copy()
                min_img.thumbnail((32, 32), Image.Resampling.BILINEAR)
                min_img = min_img.convert("RGB")
                self.slot_ctk_img = ctk.CTkImage(light_image=min_img, dark_image=min_img, size=(32, 32))
                self._recreate_icon_label(text="", image=self.slot_ctk_img)
        except Exception:
            self.slot_ctk_img = None
            self._recreate_icon_label(text=self.channel_char, image=None)

        if self.file_changed_callback:
            self.file_changed_callback(self.file_path)

    def set_label_text(self, label_text: str):
        self._label_text = label_text
        self.title_label.configure(text=label_text)

    def reset(self):
        """Fully reset this slot to empty state. Always idempotent."""
        # Hold old image reference alive until widget is reconfigured
        _old_img = self.slot_ctk_img

        was_loaded = self.file_path is not None
        self.file_path = None
        self.slot_ctk_img = None

        try:
            self._recreate_icon_label(text=self.channel_char, image=None)
        except Exception:
            pass
        self.hint_label.configure(text="Drop / click", text_color=FG_DIM)
        self.configure(border_color=BORDER_CLR)

        # Only fire callback if we actually had content to clear
        if was_loaded and self.file_changed_callback:
            self.file_changed_callback(None)


# ══════════════════════════════════════════════════════════════════════
class PBRConverterApp:
    """Main Application GUI."""

    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize TkinterDnD window
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = ctk.CTk()

        self.root.title("PBR Texture Converter")
        self.root.geometry("840x660")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_OUTER)

        # Enable immersive dark mode title bar on Windows immediately and with safety delays
        if sys.platform.startswith("win"):
            # Apply immediately
            apply_dark_title_bar(self.root)
            # Apply again after mapping triggers to prevent Windows from reverting to light theme
            self.root.after(10, lambda: apply_dark_title_bar(self.root))
            self.root.after(100, lambda: apply_dark_title_bar(self.root))
            self.root.after(300, lambda: apply_dark_title_bar(self.root))

        # Set custom window icon
        self.icon_path = os.path.normpath(os.path.join(_base, "icon.ico"))
        self.root.icon_path = self.icon_path
        if os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception:
                pass

        self.batch_groups = {}
        self.batch_mode_var = tk.BooleanVar(value=False)
        self.save_mra_var = tk.BooleanVar(value=False)
        self.output_directory = None

        self._build_ui()

    def _build_ui(self):
        # ── Header ───────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(16, 0))

        title = ctk.CTkLabel(
            header_frame,
            text="PBR Texture Converter",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=FG_TITLE
        )
        title.pack(side="left")

        # Help Button [?]
        help_btn = ctk.CTkButton(
            header_frame,
            text="?",
            font=(FONT_FAMILY, 12, "bold"),
            width=28,
            height=28,
            fg_color=BG_PANEL,
            hover_color=BG_SLOT_HOVER,
            text_color=FG_TEXT,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=14,
            command=self._show_help
        )
        help_btn.pack(side="right")

        # Subtitle
        sub_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        sub_frame.pack(fill="x", padx=24, pady=(2, 6))

        subtitle = ctk.CTkLabel(
            sub_frame,
            text="Convert PBR texture maps between workflows",
            font=(FONT_FAMILY, 10),
            text_color=FG_DIM
        )
        subtitle.pack(side="left")

        # Batch Mode Switch
        batch_switch = ctk.CTkSwitch(
            sub_frame,
            text="Batch Convertation Mode",
            font=(FONT_FAMILY, 10, "bold"),
            variable=self.batch_mode_var,
            text_color=FG_TEXT,
            fg_color=BORDER_CLR,
            progress_color=ACCENT_BLUE,
            command=self._toggle_batch_mode
        )
        batch_switch.pack(side="right")

        # ── Main Content Container ────────────────────────────────────
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=8)

        # 1. Single Mode View Frame
        self.single_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._build_single_mode_view()

        # 2. Batch Mode View Frame
        self.batch_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._build_batch_mode_view()

        # ── Bottom Action Area (Status & Action buttons) ──────────────
        action_panel = ctk.CTkFrame(
            self.root,
            fg_color=BG_PANEL,
            height=54,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=0
        )
        action_panel.pack(fill="x", side="bottom")
        action_panel.pack_propagate(False)

        self.status_lbl = ctk.CTkLabel(
            action_panel,
            text="READY",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=FG_DIM
        )
        self.status_lbl.pack(side="left", padx=24, fill="y")

        # Output Folder open button
        self.open_output_btn = ctk.CTkButton(
            action_panel,
            text="📁 Open Output Folder",
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=BG_SLOT,
            hover_color=BG_SLOT_HOVER,
            text_color=FG_TEXT,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=8,
            state="disabled",
            command=self._open_output_folder
        )
        self.open_output_btn.pack(side="right", padx=24, pady=12)

        # Default mode activation
        self._toggle_batch_mode()

    # ── Single Conversion View Layout ─────────────────────────────────
    def _build_single_mode_view(self):
        # A grid layout for side-by-side structures
        self.single_view.columnconfigure(0, weight=4) # Input Pipeline
        self.single_view.columnconfigure(1, weight=1) # Middlelane Convert
        self.single_view.columnconfigure(2, weight=4) # Output Pipeline

        # ── Left Column: Input Pipeline Panel ─────────────────────────
        in_panel = ctk.CTkFrame(
            self.single_view,
            fg_color=BG_PANEL,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=16
        )
        in_panel.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        in_lbl = ctk.CTkLabel(
            in_panel,
            text="INPUT PIPELINE",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=FG_DIM
        )
        in_lbl.pack(pady=(12, 4))

        self.input_combo = ctk.CTkComboBox(
            in_panel,
            values=["SPECULAR / GLOSSINESS", "METALLIC / ROUGHNESS"],
            font=(FONT_FAMILY, 12, "bold"),
            dropdown_font=(FONT_FAMILY, 11),
            fg_color=BG_SLOT,
            border_color=BORDER_CLR,
            button_color=BORDER_CLR,
            button_hover_color=BG_SLOT_HOVER,
            width=240,
            command=self._on_input_combo_changed
        )
        self.input_combo.pack(pady=(0, 14))

        # Input Slots Area (Horizontal Layout)
        in_slots_frame = ctk.CTkFrame(in_panel, fg_color="transparent")
        in_slots_frame.pack(fill="x", padx=16, pady=(0, 16))
        in_slots_frame.columnconfigure((0, 1, 2), weight=1)

        self.in_slot1 = DropZone(in_slots_frame, "Diffuse", "D", lambda p: self.in_prev1.update_image(p))
        self.in_slot1.grid(row=0, column=0, padx=6, sticky="ew")

        self.in_slot2 = DropZone(in_slots_frame, "Specular", "S", lambda p: self.in_prev2.update_image(p))
        self.in_slot2.grid(row=0, column=1, padx=6, sticky="ew")

        self.in_slot3 = DropZone(in_slots_frame, "Glossiness", "G", lambda p: self.in_prev3.update_image(p))
        self.in_slot3.grid(row=0, column=2, padx=6, sticky="ew")

        # ── Middle Column: Convert & Indicators ──────────────────────
        mid_panel = ctk.CTkFrame(self.single_view, fg_color="transparent")
        mid_panel.grid(row=0, column=1, padx=4, pady=8, sticky="ns")

        # Dynamic arrow
        self.arrow_lbl = ctk.CTkLabel(
            mid_panel,
            text="⇄",
            font=(FONT_FAMILY, 34, "bold"),
            text_color=ACCENT_BLUE,
            cursor="hand2"
        )
        self.arrow_lbl.pack(expand=True, pady=(24, 8))
        self.arrow_lbl.bind("<Button-1>", lambda e: self._swap_pipelines())
        self.arrow_lbl.bind("<Enter>", lambda e: self.arrow_lbl.configure(text_color=ACCENT_MINT))
        self.arrow_lbl.bind("<Leave>", lambda e: self.arrow_lbl.configure(text_color=ACCENT_BLUE))

        # Convert Button
        self.convert_btn = ctk.CTkButton(
            mid_panel,
            text="CONVERT",
            font=(FONT_FAMILY, 12, "bold"),
            width=100,
            height=38,
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            text_color="#ffffff",
            corner_radius=10,
            command=self._run_single_conversion
        )
        self.convert_btn.pack(expand=True, pady=(8, 24))

        # ── Right Column: Output Pipeline Panel ────────────────────────
        out_panel = ctk.CTkFrame(
            self.single_view,
            fg_color=BG_PANEL,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=16
        )
        out_panel.grid(row=0, column=2, padx=8, pady=8, sticky="nsew")

        out_lbl = ctk.CTkLabel(
            out_panel,
            text="OUTPUT PIPELINE",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=FG_DIM
        )
        out_lbl.pack(pady=(12, 4))

        self.output_combo = ctk.CTkComboBox(
            out_panel,
            values=["METALLIC / ROUGHNESS", "SPECULAR / GLOSSINESS"],
            font=(FONT_FAMILY, 12, "bold"),
            dropdown_font=(FONT_FAMILY, 11),
            fg_color=BG_SLOT,
            border_color=BORDER_CLR,
            button_color=BORDER_CLR,
            button_hover_color=BG_SLOT_HOVER,
            width=240,
            command=self._on_output_combo_changed
        )
        self.output_combo.pack(pady=(0, 14))

        # Output Slots Area (Horizontal Layout)
        out_slots_frame = ctk.CTkFrame(out_panel, fg_color="transparent")
        out_slots_frame.pack(fill="x", padx=16, pady=(0, 16))
        out_slots_frame.columnconfigure((0, 1, 2), weight=1)

        # Output zones do not receive drop files, but they act as visual shells and display output thumbnails!
        self.out_slot1 = DropZone(out_slots_frame, "Base Color", "BC", lambda p: self.out_prev1.update_image(p))
        self.out_slot1.grid(row=0, column=0, padx=6, sticky="ew")

        self.out_slot2 = DropZone(out_slots_frame, "Metallic", "M", lambda p: self.out_prev2.update_image(p))
        self.out_slot2.grid(row=0, column=1, padx=6, sticky="ew")

        self.out_slot3 = DropZone(out_slots_frame, "Roughness", "R", lambda p: self.out_prev3.update_image(p))
        self.out_slot3.grid(row=0, column=2, padx=6, sticky="ew")

        # ── Bottom Row: Dedicated Previews Area ───────────────────────
        self.previews_frame = ctk.CTkFrame(
            self.single_view,
            fg_color=BG_PANEL,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=16
        )
        self.previews_frame.grid(row=1, column=0, columnspan=3, padx=8, pady=(12, 4), sticky="ew")

        prev_header = ctk.CTkLabel(
            self.previews_frame,
            text="LIVE HIGH-FIDELITY PREVIEWS (CLICK TO VIEW FULL-RESOLUTION POP-UP)",
            font=(FONT_FAMILY, 9, "bold"),
            text_color=FG_DIM
        )
        prev_header.pack(pady=(10, 8))

        prev_flex = ctk.CTkFrame(self.previews_frame, fg_color="transparent")
        prev_flex.pack(fill="x", padx=24, pady=(0, 14))

        # Left Previews Container
        left_box = ctk.CTkFrame(prev_flex, fg_color="transparent")
        left_box.pack(side="left", expand=True)

        self.in_prev1 = ClickablePreview(left_box, "Diffuse", self._open_image_viewer)
        self.in_prev1.pack(side="left", padx=10)

        self.in_prev2 = ClickablePreview(left_box, "Specular", self._open_image_viewer)
        self.in_prev2.pack(side="left", padx=10)

        self.in_prev3 = ClickablePreview(left_box, "Glossiness", self._open_image_viewer)
        self.in_prev3.pack(side="left", padx=10)

        # Flex middlelane indicator
        mid_arrow = ctk.CTkLabel(
            prev_flex,
            text="⇄",
            font=(FONT_FAMILY, 24, "bold"),
            text_color=ACCENT_BLUE
        )
        mid_arrow.pack(side="left", padx=20)

        # Right Previews Container
        right_box = ctk.CTkFrame(prev_flex, fg_color="transparent")
        right_box.pack(side="left", expand=True)

        self.out_prev1 = ClickablePreview(right_box, "Base Color", self._open_image_viewer)
        self.out_prev1.pack(side="left", padx=10)

        self.out_prev2 = ClickablePreview(right_box, "Metallic", self._open_image_viewer)
        self.out_prev2.pack(side="left", padx=10)

        self.out_prev3 = ClickablePreview(right_box, "Roughness", self._open_image_viewer)
        self.out_prev3.pack(side="left", padx=10)

    # ── Batch Conversion View Layout ──────────────────────────────────
    def _build_batch_mode_view(self):
        self.batch_view.columnconfigure(0, weight=1)

        # Main Centered Panel
        center_panel = ctk.CTkFrame(
            self.batch_view,
            fg_color=BG_PANEL,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=16
        )
        center_panel.grid(row=0, column=0, padx=120, pady=8, sticky="nsew")
        self.batch_view.rowconfigure(0, weight=1)

        header_lbl = ctk.CTkLabel(
            center_panel,
            text="BATCH WORKFLOW IMPORT & CONVERSION",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=FG_DIM
        )
        header_lbl.pack(pady=(16, 8))

        # Workflow Combobox for batch direction
        combo_frame = ctk.CTkFrame(center_panel, fg_color="transparent")
        combo_frame.pack(fill="x", padx=24, pady=(0, 10))

        combo_lbl = ctk.CTkLabel(
            combo_frame,
            text="Conversion Flow:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=FG_TEXT
        )
        combo_lbl.pack(side="left", padx=(0, 10))

        self.batch_flow_combo = ctk.CTkComboBox(
            combo_frame,
            values=["Spec / Gloss  →  Metal / Rough", "Metal / Rough  →  Spec / Gloss"],
            font=(FONT_FAMILY, 11, "bold"),
            dropdown_font=(FONT_FAMILY, 10),
            fg_color=BG_SLOT,
            border_color=BORDER_CLR,
            button_color=BORDER_CLR,
            button_hover_color=BG_SLOT_HOVER,
            width=260,
            command=self._on_batch_flow_combo_changed
        )
        self.batch_flow_combo.pack(side="left")

        # Wide Drop Box
        self.batch_drop_lbl = ctk.CTkLabel(
            center_panel,
            text="Drop multiple texture files here\nor click to browse",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=FG_TEXT,
            fg_color=BG_SLOT,
            height=64,
            corner_radius=12
        )
        self.batch_drop_lbl.pack(fill="x", padx=24, pady=6)
        self.batch_drop_lbl.bind("<Button-1>", lambda e: self._browse_batch_files())

        if HAS_DND:
            self.batch_drop_lbl.drop_target_register(DND_FILES)
            self.batch_drop_lbl.dnd_bind("<<Drop>>", self._on_batch_drop)
            self.batch_drop_lbl.dnd_bind("<<DragEnter>>", lambda e: self.batch_drop_lbl.configure(fg_color=BG_SLOT_HOVER))
            self.batch_drop_lbl.dnd_bind("<<DragLeave>>", lambda e: self.batch_drop_lbl.configure(fg_color=BG_SLOT))

        # Materials Scroll List
        self.batch_table = ctk.CTkScrollableFrame(
            center_panel,
            fg_color=BG_OUTER,
            border_color=BORDER_CLR,
            border_width=1,
            corner_radius=10,
            height=200
        )
        self.batch_table.pack(fill="both", expand=True, padx=24, pady=8)

        # Batch Options Frame
        opts_frame = ctk.CTkFrame(center_panel, fg_color="transparent")
        opts_frame.pack(fill="x", padx=24, pady=(6, 12))

        # Save MRA checkbox (Metal / Roughness / AO packing)
        self.mra_checkbox = ctk.CTkCheckBox(
            opts_frame,
            text="Save Packed MRA Map (Red: Metallic, Green: Roughness, Blue: AO)",
            variable=self.save_mra_var,
            font=(FONT_FAMILY, 10),
            text_color=FG_TEXT,
            fg_color=BG_SLOT,
            border_color=BORDER_CLR,
            hover_color=BG_SLOT_HOVER,
            checkmark_color=ACCENT_BLUE
        )
        self.mra_checkbox.pack(side="left")

        # Convert All Button
        self.batch_convert_btn = ctk.CTkButton(
            center_panel,
            text="⚡  CONVERT ALL MATERIALS",
            font=(FONT_FAMILY, 12, "bold"),
            width=220,
            height=40,
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            text_color="#ffffff",
            corner_radius=10,
            command=self._run_batch_conversion
        )
        self.batch_convert_btn.pack(pady=(0, 16))

        self._render_batch_table()

    # ── Single Mode Combo Triggers ────────────────────────────────────
    def _on_input_combo_changed(self, value):
        if value == "SPECULAR / GLOSSINESS":
            self.output_combo.set("METALLIC / ROUGHNESS")
        else:
            self.output_combo.set("SPECULAR / GLOSSINESS")
        self._update_single_labels(value)

    def _on_output_combo_changed(self, value):
        if value == "METALLIC / ROUGHNESS":
            self.input_combo.set("SPECULAR / GLOSSINESS")
            self._update_single_labels("SPECULAR / GLOSSINESS")
        else:
            self.input_combo.set("METALLIC / ROUGHNESS")
            self._update_single_labels("METALLIC / ROUGHNESS")

    def _update_single_labels(self, in_mode=None):
        if in_mode is None:
            in_mode = self.input_combo.get()

        # Step 1: Set channel_chars and label texts FIRST (before any reset)
        if in_mode == "SPECULAR / GLOSSINESS":
            self.in_slot1.channel_char = "D"
            self.in_slot1.set_label_text("Diffuse")
            self.in_slot2.channel_char = "S"
            self.in_slot2.set_label_text("Specular")
            self.in_slot3.channel_char = "G"
            self.in_slot3.set_label_text("Glossiness")

            self.out_slot1.channel_char = "BC"
            self.out_slot1.set_label_text("Base Color")
            self.out_slot2.channel_char = "M"
            self.out_slot2.set_label_text("Metallic")
            self.out_slot3.channel_char = "R"
            self.out_slot3.set_label_text("Roughness")

            self.in_prev1.text_label.configure(text="Diffuse")
            self.in_prev2.text_label.configure(text="Specular")
            self.in_prev3.text_label.configure(text="Glossiness")
            self.out_prev1.text_label.configure(text="Base Color")
            self.out_prev2.text_label.configure(text="Metallic")
            self.out_prev3.text_label.configure(text="Roughness")
        else:
            self.in_slot1.channel_char = "BC"
            self.in_slot1.set_label_text("Base Color")
            self.in_slot2.channel_char = "M"
            self.in_slot2.set_label_text("Metallic")
            self.in_slot3.channel_char = "R"
            self.in_slot3.set_label_text("Roughness")

            self.out_slot1.channel_char = "D"
            self.out_slot1.set_label_text("Diffuse")
            self.out_slot2.channel_char = "S"
            self.out_slot2.set_label_text("Specular")
            self.out_slot3.channel_char = "G"
            self.out_slot3.set_label_text("Glossiness")

            self.in_prev1.text_label.configure(text="Base Color")
            self.in_prev2.text_label.configure(text="Metallic")
            self.in_prev3.text_label.configure(text="Roughness")
            self.out_prev1.text_label.configure(text="Diffuse")
            self.out_prev2.text_label.configure(text="Specular")
            self.out_prev3.text_label.configure(text="Glossiness")

        # Step 2: Now reset all slots ONCE (channel_chars are already correct)
        self._reset_single_slots()

    def _reset_single_slots(self):
        """Reset all 6 slots. Each reset uses the already-configured channel_char."""
        self.in_slot1.reset()
        self.in_slot2.reset()
        self.in_slot3.reset()
        self.out_slot1.reset()
        self.out_slot2.reset()
        self.out_slot3.reset()

    # ── Batch Combo Triggers ─────────────────────────────────────────
    def _on_batch_flow_combo_changed(self, value):
        self.batch_groups.clear()
        self._render_batch_table()

    # ── Mode Switch Trigger ───────────────────────────────────────────
    def _toggle_batch_mode(self):
        is_batch = self.batch_mode_var.get()
        if is_batch:
            self.single_view.pack_forget()
            self.batch_view.pack(fill="both", expand=True)
            self._on_batch_flow_combo_changed(self.batch_flow_combo.get())
        else:
            self.batch_view.pack_forget()
            self.single_view.pack(fill="both", expand=True)
            self._update_single_labels()

        self.status_lbl.configure(text="READY", text_color=FG_DIM)

    # ── Help Popup Launcher ──────────────────────────────────────────
    def _show_help(self):
        HelpPopup(self.root)

    # ── Clickable Preview Window Launcher ────────────────────────────
    def _open_image_viewer(self, path: str, label_text: str):
        ImagePopup(self.root, path, label_text)

    # ── Batch Drag and Drop ──────────────────────────────────────────
    def _on_batch_drop(self, event):
        self._add_batch_files(_parse_drop_paths(event.data))

    def _browse_batch_files(self):
        paths = filedialog.askopenfilenames(
            title="Select PBR maps for batch import",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.tga *.exr"),
                ("All files", "*.*"),
            ]
        )
        if paths:
            self._add_batch_files(paths)

    def _add_batch_files(self, paths):
        added = 0
        flow = self.batch_flow_combo.get()
        workflow = "SG" if flow.startswith("Spec") else "MR"

        for p in paths:
            norm = os.path.normpath(p)
            if not _is_image_file(norm):
                continue
            mat_name, role = _strip_role_suffix(norm, workflow)
            if not role:
                continue

            key = mat_name.lower()
            group = self.batch_groups.setdefault(
                key,
                {"display": mat_name, "diff": None, "spec": None, "gloss": None}
            )
            group[role] = norm
            added += 1

        self._render_batch_table()
        if added:
            self._set_status(f"Imported {added} batch texture maps successfully.", ACCENT_MINT)

    def _is_batch_group_complete(self, group):
        return bool(group.get("diff") and group.get("spec") and group.get("gloss"))

    def _render_batch_table(self):
        if not hasattr(self, "batch_table"):
            return

        for child in self.batch_table.winfo_children():
            child.destroy()

        flow = self.batch_flow_combo.get()
        if flow.startswith("Spec"):
            col_headers = [("Material", "name"), ("Diffuse", "diff"), ("Specular", "spec"), ("Glossiness", "gloss"), ("", "remove")]
        else:
            col_headers = [("Material", "name"), ("Base Color", "diff"), ("Metallic", "spec"), ("Roughness", "gloss"), ("", "remove")]

        # Draw Table Headers
        for col_idx, (title, _) in enumerate(col_headers):
            lbl = ctk.CTkLabel(
                self.batch_table,
                text=title,
                font=(FONT_FAMILY, 9, "bold"),
                text_color=FG_DIM,
                anchor="w"
            )
            lbl.grid(row=0, column=col_idx, padx=8, pady=(4, 8), sticky="ew")
            self.batch_table.columnconfigure(col_idx, weight=1 if title else 0)

        # Empty State
        if not self.batch_groups:
            empty = ctk.CTkLabel(
                self.batch_table,
                text="No compatible textures loaded. Drag them above to auto-detect PBR workflows.",
                font=(FONT_FAMILY, 10, "italic"),
                text_color=FG_DIM
            )
            empty.grid(row=1, column=0, columnspan=len(col_headers), pady=36)
            return

        # Populating Rows
        sorted_keys = sorted(self.batch_groups.keys())
        for row_idx, key in enumerate(sorted_keys, start=1):
            group = self.batch_groups[key]
            complete = self._is_batch_group_complete(group)
            row_bg = "#1e293b" if complete else "#3b1e22" # Soft red tint if incomplete

            for col_idx, (_, role) in enumerate(col_headers):
                if role == "remove":
                    btn = ctk.CTkButton(
                        self.batch_table,
                        text="✕",
                        font=(FONT_FAMILY, 10, "bold"),
                        width=24,
                        height=24,
                        fg_color="#3b4455",
                        hover_color=ERROR_CLR,
                        text_color=FG_TITLE,
                        corner_radius=4,
                        command=lambda k=key: self._remove_batch_group(k)
                    )
                    btn.grid(row=row_idx, column=col_idx, padx=6, pady=3)
                    continue

                if role == "name":
                    text_val = group.get("display", key)
                else:
                    path_val = group.get(role)
                    text_val = os.path.basename(path_val) if path_val else "Missing Map"

                fg = FG_TITLE if (role == "name" or group.get(role)) else ERROR_CLR
                lbl = ctk.CTkLabel(
                    self.batch_table,
                    text=text_val,
                    font=(FONT_FAMILY, 9, "bold" if role=="name" else "normal"),
                    text_color=fg,
                    fg_color=row_bg,
                    corner_radius=6,
                    anchor="w",
                    height=28,
                    padx=8
                )
                lbl.grid(row=row_idx, column=col_idx, padx=4, pady=2, sticky="ew")

                # Double click to browse single missing cell
                if role != "name":
                    lbl.bind("<Double-Button-1>", lambda e, k=key, r=role: self._browse_single_cell(k, r))

    def _remove_batch_group(self, key):
        self.batch_groups.pop(key, None)
        self._render_batch_table()

    def _browse_single_cell(self, key, role):
        path = filedialog.askopenfilename(
            title=f"Assign map for {role}",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.tga *.exr"),
                ("All files", "*.*"),
            ]
        )
        if path:
            if key in self.batch_groups:
                self.batch_groups[key][role] = os.path.normpath(path)
                self._render_batch_table()

    def _swap_pipelines(self):
        current = self.input_combo.get()
        if current == "SPECULAR / GLOSSINESS":
            self.input_combo.set("METALLIC / ROUGHNESS")
            self._on_input_combo_changed("METALLIC / ROUGHNESS")
        else:
            self.input_combo.set("SPECULAR / GLOSSINESS")
            self._on_input_combo_changed("SPECULAR / GLOSSINESS")

    # ── Single Conversion Action ─────────────────────────────────────
    def _run_single_conversion(self):
        in_mode = self.input_combo.get()

        # Gather inputs
        paths = {
            "slot1": self.in_slot1.file_path,
            "slot2": self.in_slot2.file_path,
            "slot3": self.in_slot3.file_path
        }

        missing = []
        if not paths["slot1"]: missing.append(self.in_slot1._label_text)
        if not paths["slot2"]: missing.append(self.in_slot2._label_text)
        if not paths["slot3"]: missing.append(self.in_slot3._label_text)

        if missing:
            messagebox.showwarning("Missing Textures", f"Please provide: {', '.join(missing)}")
            return

        self._set_status("⏳  CONVERTING TEXTURE PIPELINES ...", ACCENT_BLUE)
        self.convert_btn.configure(state="disabled")

        def _worker():
            try:
                if in_mode == "SPECULAR / GLOSSINESS":
                    albedo, metallic, roughness = spec_gloss_to_metal_rough.convert(
                        paths["slot1"], paths["slot2"], paths["slot3"]
                    )
                    out_dir = self._output_dir(paths["slot1"])
                    base = self._base_from_diffuse_path(paths["slot1"])

                    # Save Outputs
                    out1_path = os.path.join(out_dir, f"{base}_BC.png")
                    albedo.save(out1_path)

                    if self.save_mra_var.get():
                        out2_path = os.path.join(out_dir, f"{base}_MRA.png")
                        self._save_mra(out2_path, metallic, roughness)
                        out3_path = None
                    else:
                        out2_path = os.path.join(out_dir, f"{base}_metallic.png")
                        out3_path = os.path.join(out_dir, f"{base}_roughness.png")
                        metallic.save(out2_path)
                        roughness.save(out3_path)
                else:
                    diffuse, specular, glossiness = metal_rough_to_spec_gloss.convert(
                        paths["slot1"], paths["slot2"], paths["slot3"]
                    )
                    out_dir = self._output_dir(paths["slot1"])
                    base = self._base_from_diffuse_path(paths["slot1"])

                    out1_path = os.path.join(out_dir, f"{base}_diffuse.png")
                    out2_path = os.path.join(out_dir, f"{base}_specular.png")
                    out3_path = os.path.join(out_dir, f"{base}_glossiness.png")

                    diffuse.save(out1_path)
                    specular.save(out2_path)
                    glossiness.save(out3_path)

                # Set globally for navigation
                self.output_directory = out_dir

                def _success():
                    self._set_status(f"✅ CONVERSION DONE! Saved in: {os.path.basename(out_dir)}", ACCENT_MINT)
                    self.convert_btn.configure(state="normal")
                    self.open_output_btn.configure(state="normal")

                    # Update output slot displays and preview panels (automatically updates previews via callback!)
                    self.out_slot1.set_path(out1_path)

                    if out2_path:
                        self.out_slot2.set_path(out2_path)
                    else:
                        self.out_slot2.reset()

                    if out3_path:
                        self.out_slot3.set_path(out3_path)
                    else:
                        # If MRA was packed, Slot 3 is merged into Slot 2
                        self.out_slot3.reset()
                        self.out_slot3.hint_label.configure(text="Packed in MRA", text_color=ACCENT_MINT)

                self.root.after(0, _success)

            except Exception as e:
                def _error():
                    self._set_status(f"❌ ERROR: {e}", ERROR_CLR)
                    self.convert_btn.configure(state="normal")
                    messagebox.showerror("Conversion Failed", str(e))
                self.root.after(0, _error)

        threading.Thread(target=_worker, daemon=True).start()

    # ── Batch Conversion Action ──────────────────────────────────────
    def _run_batch_conversion(self):
        if not self.batch_groups:
            messagebox.showwarning("Empty Materials", "Please import textures to convert first.")
            return

        incomplete = [self.batch_groups[k]["display"] for k in self.batch_groups if not self._is_batch_group_complete(self.batch_groups[k])]
        if incomplete:
            messagebox.showwarning(
                "Missing Channels",
                f"Please load all missing maps for the following materials first:\n• " + "\n• ".join(incomplete)
            )
            return

        flow = self.batch_flow_combo.get()
        self._set_status("⏳  PROCESSING BATCH CONVERSIONS ...", ACCENT_BLUE)
        self.batch_convert_btn.configure(state="disabled")

        jobs = [(k, dict(self.batch_groups[k])) for k in self.batch_groups]

        def _worker():
            converted_cnt = 0
            out_dirs = set()
            try:
                for _, group in jobs:
                    if flow.startswith("Spec"):
                        albedo, metallic, roughness = spec_gloss_to_metal_rough.convert(
                            group["diff"], group["spec"], group["gloss"]
                        )
                        out_dir = self._output_dir(group["diff"])
                        base = self._base_from_diffuse_path(group["diff"])

                        albedo.save(os.path.join(out_dir, f"{base}_BC.png"))
                        if self.save_mra_var.get():
                            self._save_mra(os.path.join(out_dir, f"{base}_MRA.png"), metallic, roughness)
                        else:
                            metallic.save(os.path.join(out_dir, f"{base}_metallic.png"))
                            roughness.save(os.path.join(out_dir, f"{base}_roughness.png"))
                    else:
                        diffuse, specular, glossiness = metal_rough_to_spec_gloss.convert(
                            group["diff"], group["spec"], group["gloss"]
                        )
                        out_dir = self._output_dir(group["diff"])
                        base = self._base_from_diffuse_path(group["diff"])

                        diffuse.save(os.path.join(out_dir, f"{base}_diffuse.png"))
                        specular.save(os.path.join(out_dir, f"{base}_specular.png"))
                        glossiness.save(os.path.join(out_dir, f"{base}_glossiness.png"))

                    out_dirs.add(out_dir)
                    converted_cnt += 1

                # Set globally for navigation (select first one)
                if out_dirs:
                    self.output_directory = list(out_dirs)[0]

                def _success():
                    text = f"✅ BATCH SUCCESS! Converted {converted_cnt} materials."
                    self._set_status(text, ACCENT_MINT)
                    self.batch_convert_btn.configure(state="normal")
                    self.open_output_btn.configure(state="normal")
                    messagebox.showinfo("Batch Complete", f"Successfully converted {converted_cnt} material sets.")

                self.root.after(0, _success)

            except Exception as e:
                def _error():
                    self._set_status(f"❌ BATCH ERROR: {e}", ERROR_CLR)
                    self.batch_convert_btn.configure(state="normal")
                    messagebox.showerror("Batch Conversion Failed", str(e))
                self.root.after(0, _error)

        threading.Thread(target=_worker, daemon=True).start()

    # ── Output Directories & MRA Packing ──────────────────────────────
    def _output_dir(self, reference_path: str) -> str:
        parent = os.path.dirname(reference_path)
        out = os.path.join(parent, "Converted")
        os.makedirs(out, exist_ok=True)
        return out

    def _base_from_diffuse_path(self, path: str) -> str:
        base = os.path.splitext(os.path.basename(path))[0]
        lower_base = base.lower()
        for sfx in DIFF_SUFFIXES:
            if lower_base.endswith(sfx):
                return base[: -len(sfx)]
        return base

    def _save_mra(self, path: str, metallic, roughness):
        metallic_l = metallic.convert("L")
        roughness_l = roughness.convert("L")
        ao_l = Image.new("L", metallic_l.size, 255)
        Image.merge("RGB", (metallic_l, roughness_l, ao_l)).save(path)

    def _open_output_folder(self):
        if self.output_directory and os.path.exists(self.output_directory):
            try:
                os.startfile(self.output_directory)
            except Exception as e:
                messagebox.showerror("Cannot Open Folder", f"Failed to launch directory: {e}")

    def _set_status(self, text: str, color=FG_DIM):
        self.status_lbl.configure(text=text, text_color=color)

    def run(self):
        self.root.mainloop()
