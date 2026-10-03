# -*- mode: python ; coding: utf-8 -*-
"""
Spec do PyInstaller para o Sistema de Gestão de Gado
Sítio Santo Antonio — Família: Geane, Deyvid, Nilson
"""

import os

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),   # HTML templates
        ('config.py',   '.'),
        ('db.py',       '.'),
        ('calculos.py', '.'),
        ('exportar.py', '.'),
        ('registros.py','.'),
        ('relatorios.py','.'),
        ('ui_helper.py','.'),
        ('main.py',     '.'),
    ],
    hiddenimports=[
        'openpyxl',
        'openpyxl.cell._writer',
        'openpyxl.styles',
        'openpyxl.utils',
        'pandas',
        'flask',
        'werkzeug',
        'jinja2',
        'click',
        'bs4',
        'requests',
        'matplotlib',
        'matplotlib.backends.backend_agg',
        'saude',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'wx'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GadoSitioSantoAntonio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # Sem janela de terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GadoSitioSantoAntonio',
)
