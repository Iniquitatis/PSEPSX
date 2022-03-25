import os

library_blacklist = [
    "Qt6OpenGL.dll",
    "Qt6QmlModels.dll",
    "Qt6Quick.dll",
    "Qt6Svg.dll",
    "Qt6VirtualKeyboard.dll",
    "opengl32sw.dll",
    "PySide6/plugins/imageformats/qgif.dll",
    "PySide6/plugins/imageformats/qicns.dll",
    "PySide6/plugins/imageformats/qjpeg.dll",
    "PySide6/plugins/imageformats/qtga.dll",
    "PySide6/plugins/imageformats/qtiff.dll",
    "PySide6/plugins/imageformats/qwbmp.dll",
    "PySide6/plugins/imageformats/qwebp.dll",
    "PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll",
]

block_cipher = None

analysis = Analysis(
    ["PSEPSX.py"],
    pathex = ["."],
    binaries = [],
    datas = [
        ("Data", "Data"),
        ("Patches", "Patches"),
        ("Resources", "Resources"),
        ("Scripts", "Scripts"),
    ],
    hiddenimports = [f"Scripts.{os.path.splitext(x)[0]}" for x in os.listdir("Scripts")],
    hookspath = [],
    hooksconfig = {},
    runtime_hooks = [],
    excludes = [
        "_asyncio",
        "_bz2",
        "_ctypes",
        "_hashlib",
        "_lzma",
        "_multiprocessing",
        "_overlapped",
        "_queue",
        "_ssl",
        "PIL._imagingtk",
        "PIL._webp",
        "PySide6.QtNetwork",
    ],
    win_no_prefer_redirects = False,
    win_private_assemblies = False,
    cipher = block_cipher,
    noarchive = False
)
analysis.binaries -= TOC([(os.path.normcase(x), None, None) for x in library_blacklist])

pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher = block_cipher
)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name = "PSEPSX",
    debug = False,
    bootloader_ignore_signals = False,
    strip = False,
    upx = False,
    upx_exclude = [],
    runtime_tmpdir = None,
    console = False,
    disable_windowed_traceback = False,
    target_arch = None,
    codesign_identity = None,
    entitlements_file = None,
    icon = "Resources/Icon.ico"
)
