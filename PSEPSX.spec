import os

library_blacklist = [
    "Qt6OpenGL.dll",
    "Qt6QmlModels.dll",
    "Qt6Quick.dll",
    "Qt6Svg.dll",
    "Qt6VirtualKeyboard.dll",
    "opengl32sw.dll",
]

block_cipher = None

analysis = Analysis(
    ["PSEPSX.py"],
    pathex = ["."],
    binaries = [],
    datas = [
        ("Modules/*.*", "Modules"),
        ("Patches/*.*", "Patches"),
        ("Resources/*.*", "Resources"),
    ],
    hiddenimports = [f"Modules.{os.path.splitext(x)[0]}" for x in os.listdir("Modules")],
    hookspath = [],
    hooksconfig = {},
    runtime_hooks = [],
    excludes = [],
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
