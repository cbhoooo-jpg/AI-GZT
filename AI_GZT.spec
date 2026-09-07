# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('chat_float.html', '.'), ('chat_ui.html', '.'), ('file_editor.html', '.'), ('sample.html', '.'), ('web_backup.html', '.'), ('web_file_repo.html', '.'), ('web_log.html', '.'), ('web_plugin_market.html', '.'), ('web_scheduler.html', '.'), ('web_settings.html', '.'), ('web_workspace.html', '.'), ('web_about.html', '.'), ('config.json', '.'), ('memory_config.json', '.'), ('prompt_templates.json', '.'), ('requirements.txt', '.'), ('logo.png', '.'), ('app_icon.ico', '.'), ('editor_empty_bg.png', '.'), ('AI_GZT_User_Guide.md', '.'), ('THIRD_PARTY_LICENSES.md', '.'), ('static', 'static'), ('plugins', 'plugins'), ('plugin_templates', 'plugin_templates'), ('tools', 'tools'), ('gte-small-zh', 'gte-small-zh')],
    hiddenimports=['memory_cache', 'rag_manager', 'api_server', 'llm_client', 'tool_template_manager', 'auto_sync_monitor', 'ai_browser', 'screenshot_tool', 'project_manual_manager', 'scheduler_manager', 'http', 'http.cookies', 'http.client', 'http.server', 'email', 'email.mime', 'email.mime.multipart', 'email.mime.text', 'mimetypes', 'html', 'html.parser', 'urllib', 'urllib.parse', 'urllib.request', 'colorsys', 'logging.config', 'pypinyin'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['unittest', 'doctest', 'pdb', 'profile', 'pstats', 'uvicorn', 'uvicorn.logging', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'fastapi', 'fastapi.middleware', 'fastapi.middleware.cors', 'fastapi.staticfiles', 'fastapi.responses', 'sse_starlette', 'sse_starlette.sse', 'pydantic', 'pydantic_core', 'pydantic._internal', 'pydantic.deprecated', 'pydantic.networks', 'pydantic.types', 'pydantic.fields', 'multipart', 'multipart.multipart', 'torch', 'torchvision', 'torchaudio', 'tensorboard', 'torch.distributed', 'sentence_transformers', 'transformers', 'tensorflow', 'keras', 'scipy', 'sklearn', 'scikit-learn', 'sentencepiece', 'safetensors', 'faiss', 'faiss._swigfaiss', 'tokenizers', 'huggingface_hub', 'nltk', 'datasets'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI_GZT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI_GZT',
)
