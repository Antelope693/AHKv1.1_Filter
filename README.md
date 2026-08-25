# AHK_Filter

Desktop manager for **AutoHotkey v1.1** scripts in a working folder.

Scan local `.ahk` files, assign a unique hotkey to each script, tick which ones should run, and toggle everything with one global start/stop hotkey — without repeatedly dismissing UAC prompts.

## Features

- **Visual manager** (CustomTkinter): checkbox list that grows with the number of scripts
- **Per-script hotkey**: click to record a combo; conflict detection included
- **Global start / stop hotkey**: enable or suspend all selected scripts at once
- **Refresh scan**: re-read the folder (only while globally stopped; processes are torn down and rebuilt safely)
- **Admin once**: the manager elevates on launch; script processes inherit elevation and stay resident. Start/stop only changes *effectiveness* via `Suspend`, not repeated elevation
- **In-place script wrapping**: each `.ahk` receives a small managed block so the UI can enable/disable it over a window message

## Requirements

- Windows 10/11
- Python 3.10+
- [AutoHotkey v1.1](https://www.autohotkey.com/) installed (AutoHotkeyU64.exe / AutoHotkey.exe on `PATH` or in the usual install directories)

## Install

```bat
pip install -r requirements.txt
```

## Run

```bat
run.bat
```

or:

```bat
python run.py
```

Optional: pass a folder to scan (defaults to the project directory):

```bat
python run.py "D:\scripts"
```

The first launch asks for administrator approval once. After that, start/stop/refresh operate without additional UAC dialogs under normal use.

## Usage

1. Place `.ahk` scripts in the working directory (example scripts: `Pure_RightFireK.ahk`, `Pure_WheelDouble.ahk`).
2. Open AHK_Filter; scripts are detected and wrapped automatically.
3. Tick the scripts you want active, record hotkeys as needed.
4. **Global start** — selected scripts become effective; others stay suspended.
5. Use a script’s hotkey to pause/resume that script while the session is running.
6. **Global stop** — all scripts suspend (processes remain elevated).
7. **Refresh** — only after global stop; rescans the folder and reinjects managed blocks.

Default hotkeys (editable in the UI):

| Action        | Default            |
|---------------|--------------------|
| Global toggle | `Ctrl+Shift+F8`    |
| Refresh       | `Ctrl+Shift+F5`    |

Settings are stored in `ahk_filter_config.json` (local, not committed).

## Example scripts

| File                   | Behavior                                      |
|------------------------|-----------------------------------------------|
| `Pure_RightFireK.ahk`  | Hold right mouse button to repeatedly send K  |
| `Pure_WheelDouble.ahk` | Double wheel-up burst-sends `2`               |

These two files split formerly combined “Pure” behaviors so each can be toggled and tested on its own.

## Project layout

```
ahk_filter/          Python package (UI, runtime, injector)
tests/               Unit tests for core helpers
Pure_*.ahk           Tracked example scripts
run.py / run.bat     Entry points
requirements.txt
```

Personal `.ahk` files beside the examples are ignored by git (`*.ahk` with `!Pure_*.ahk`).

## Tests

```bat
python -m unittest discover -s tests -v
```

## Notes

- Scripts must be AHK **v1.1** syntax.
- Closing the manager terminates managed AutoHotkey processes.
- Do not hand-edit the `AHK_Filter MANAGED BLOCK` region; it is regenerated on scan/refresh.

## License

MIT
