# -*- mode: python ; coding: utf-8 -*-

# 这是一个经过简化的spec文件，以提高可维护性。

# Analysis负责收集所有的Python脚本和模块。
analysis = Analysis(
    ['src/app.py'],
    # 如果项目需要，可以在这里添加需要打包的数据文件。
    # 示例: datas=[('path/to/your/model', 'models')]
    datas=[],
    # 如果PyInstaller未能自动发现某些库，可以在这里添加。
    hiddenimports=[],
)

# PYZ负责从纯Python模块创建一个Python库归档文件。
pyz = PYZ(analysis.pure)

# EXE负责创建主可执行文件。
# 在单目录模式下，此参数是必需的，以防止路径冲突。
# 在macOS上，console=False会创建一个窗口化应用（无终端窗口）。
exe = EXE(
    pyz,
    analysis.scripts,
    exclude_binaries=True,
    name='OCR-Reader',
    # console=True 和 debug=True 用于调试，发布时应设为 False。
    console=True, # 发布时: False
    debug=True,   # 发布时: False
    strip=False,
    upx=True,
)

# COLLECT负责将所有文件（可执行文件、库、数据）收集到一个目录中。
# 这将创建一个单目录（one-dir）的应用包。
collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name='OCR-Reader',
)
