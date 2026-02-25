param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$OutputDir = ".\dist"
)

& $Python -m nuitka `
    --standalone `
    --onefile `
    --windows-disable-console `
    --enable-plugin=pyside6 `
    --include-package=tldextract `
    --include-package=websockets `
    --include-package=websockets.asyncio `
    --include-data-dir=timetracker\assets=timetracker\assets `
    --include-data-dir=timetracker\browser_extension=timetracker\browser_extension `
    --windows-icon-from-ico=timetracker\assets\Health_Monitor_Icon.ico `
    --output-dir=$OutputDir `
    timetracker\main.py
