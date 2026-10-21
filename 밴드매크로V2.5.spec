# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# customtkinter 테마/아이콘, gologin 리소스를 exe에 포함
ctk_datas, ctk_bins, ctk_hidden = collect_all('customtkinter')
gl_datas, gl_bins, gl_hidden = collect_all('gologin')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ctk_bins + gl_bins,
    datas=ctk_datas + gl_datas,
    hiddenimports=[
        'customtkinter',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.edge',
        'selenium.webdriver.edge.webdriver',
        'selenium.webdriver.edge.options',
        'selenium.webdriver.edge.service',
        'selenium.webdriver.common',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.keys',
        'selenium.webdriver.common.action_chains',
        'selenium.webdriver.support',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'selenium.webdriver.remote',
        'selenium.webdriver.remote.webdriver',
        'selenium.common.exceptions',
        'gologin',
        'requests',
    ] + ctk_hidden + gl_hidden,
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
    name='밴드매크로V2.5',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 압축은 백신 오진을 늘리므로 사용 안 함
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
