block_cipher = None

analysis = Analysis(
    ["PSEPSX.py"],
    pathex = ["."],
    binaries = [],
    datas = [
        ("Patches/*.*", "Patches"),
        ("Resources/*.*", "Resources"),
    ],
    hiddenimports = [],
    hookspath = [],
    hooksconfig = {},
    runtime_hooks = [],
    excludes = [],
    win_no_prefer_redirects = False,
    win_private_assemblies = False,
    cipher = block_cipher,
    noarchive = False
)

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
