# ────────────────────────────────────────────────────────────────────────────────
# jarvis.spec – complete, drop-in replacement
# ────────────────────────────────────────────────────────────────────────────────
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import pvporcupine                              # locate package at build time

block_cipher = None

# ------------------------------------------------------------------------------
# 1.  Hidden imports PyInstaller cannot detect automatically
# ------------------------------------------------------------------------------
hiddenimports = (
    collect_submodules("qtawesome")
    + collect_submodules("PyQt6")
    + collect_submodules("psycopg2")
    + collect_submodules("jarvis_gmail_ext")
)

# ------------------------------------------------------------------------------
# 2.  Common paths
# ------------------------------------------------------------------------------
BASE     = Path(".").resolve()
PVP_PATH = Path(pvporcupine.__file__).parent     # …/Lib/site-packages/pvporcupine

# ------------------------------------------------------------------------------
# 3.  Analysis
# ------------------------------------------------------------------------------
a = Analysis(
    ["app.py"],               # <─- your main script
    pathex=[str(BASE)],
    #
    # ---- native libraries -----------------------------------------------------
    binaries=[
        # all Tesseract DLLs
        ("Tesseract-OCR\\*.dll", "Tesseract-OCR"),
        # Porcupine wake-word engine (64-bit Windows build)
        (
            str(PVP_PATH / "lib" / "windows" / "amd64" / "libpv_porcupine.dll"),
            "pvporcupine/lib/windows/amd64",
        ),
    ],
    #
    # ---- data files -----------------------------------------------------------
    datas=[
        # audio / images
        ("alarm.mp3", "."),
        ("form.png", "."),
        ("highlighted.png", "."),
        ("input_boxes_detected.png", "."),
        ("input_boxes_highlighted.png", "."),
        ("visual_input_boxes.png", "."),
        #
        # json configuration & lookup tables
         ("jarvis-ocr.json", "."),          # <- root next to exe
    ("credentials.json", "."),         # <- root next to exe
        ("forms_config.json", "."),
        ("known_forms.json", "."),
        ("known_forms_js.json", "."),
        ("suggested_files.json", "."),
        # Porcupine keyword & model resources (whole folder)
        (str(PVP_PATH / "resources"), "pvporcupine/resources"),
        #
        # Gmail helper (unzipped folder)
        ("jarvis-gmail-ext\\*", "jarvis-gmail-ext"),
    ],
    #
    hiddenimports=hiddenimports,
    cipher=block_cipher,
    noarchive=False,
)

# ------------------------------------------------------------------------------
# 4.  Build
# ------------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JARVIS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,     # True => console window; False => pure GUI
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="JARVIS",
)
