# PyInstaller spec для сборки автономного .exe/бинарника тренажёра.
#
# Сборка (из корня проекта, с активным venv, где стоит pygame и pyinstaller):
#   pyinstaller kiberstrategi.spec
#
# Результат: dist/КиберстратегиБитваЗаДанные(.exe на Windows).
# Путь для сохранения прогресса (savegame.json) — рядом с этим файлом.
import glob
import os
import sys

block_cipher = None

root = os.path.abspath(SPECPATH)

# Сюжетные и заставочные картинки лежат прямо в корне проекта (1.jpg..16.jpg,
# main.jpg, main_image.jpg) — их пути в коде строятся относительно __file__
# внутри game/, поэтому в бандле они должны остаться в корне.
story_images = [(p, '.') for p in glob.glob(os.path.join(root, '*.jpg'))]

datas = story_images + [
    (os.path.join(root, 'assets'), 'assets'),
]

a = Analysis(
    ['main.py'],
    pathex=[root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='КиберстратегиБитваЗаДанные',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root, 'icon.ico') if os.path.exists(os.path.join(root, 'icon.ico')) else None,
)

# На macOS оборачиваем в .app, чтобы запускалось двойным кликом без терминала
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='КиберстратегиБитваЗаДанные.app',
        icon=None,
        bundle_identifier='by.kiberstrategi.trainer',
        info_plist={'NSHighResolutionCapable': True},
    )
