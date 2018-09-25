# ScreenRecorder_ChinaMobile

## Build

1. Install pyinstaller and pywin32
using pip:

```bash
pip install pyinstaller
pip install pywin32
```

2. Compile source into binary
run
```bash
pyinstaller -F ScreenRecorder.spec
pyinstaller -F HTTPFileServer.spec
```

3. Run
Install windows service, run cmd.exe as Admin:
```bash
HTTPFileServer.exe install
sc start HTTPFileServer
```