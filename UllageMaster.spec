# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\ULLAGEMASTER\\src\\main.py'],
    pathex=['D:\\ULLAGEMASTER\\src'],
    binaries=[],
    datas=[('D:\\ULLAGEMASTER\\src\\i18n\\en.json', 'src/i18n'), ('D:\\ULLAGEMASTER\\src\\i18n\\tr.json', 'src/i18n'), ('D:\\ULLAGEMASTER\\data\\config\\company_logo', 'data/config/company_logo'), ('D:\\ULLAGEMASTER\\template\\TEMPLATE - Copy.xlsm', 'template'), ('D:\\ULLAGEMASTER\\template\\TEMPLATE.xlsm', 'template'), ('D:\\ULLAGEMASTER\\template\\TEMPLATE1.xlsm', 'template')],
    hiddenimports=['PyQt6', 'openpyxl', 'reportlab', 'ui', 'ui.main_window', 'ui.styles', 'ui.splash_screen', 'ui.widgets', 'models', 'core', 'export', 'reporting', 'utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='UllageMaster',
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
)
