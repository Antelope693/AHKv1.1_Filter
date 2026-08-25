# AHK_Filter

Desktop manager for **AutoHotkey v1.1** scripts under a `scripts/` folder.

## Features

- Startup **environment check** (Python packages / AutoHotkey) with guided install; silent when OK
- **Single start/stop button** — red = stopped, blue = running; global hotkey sits to its right
- **TEST** expands an in-window input bar (no extra window) for verifying script behavior
- **Handbook** (book icon) loads `docs/HANDBOOK.md` from GitHub; checks Releases for **hot updates** that preserve `scripts/` and config
- Collapsible configuration groups + loose scripts
- Per-script hotkeys; admin once, Suspend-based effectiveness

## Requirements

- Windows 10/11
- Python 3.10+
- AutoHotkey v1.1

## Install / Run

```bat
run.bat
```

`run.bat` installs missing pip packages automatically. Missing AutoHotkey is handled by the app on launch.

## Script layout

```
scripts/
  Pure/                 # configuration group
    Pure_RightFireK.ahk
    Pure_WheelDouble.ahk
  my-group/
    feature.ahk
  standalone.ahk        # loose (below groups)
```

## Maintaining the handbook

Edit and push [`docs/HANDBOOK.md`](docs/HANDBOOK.md). The in-app handbook prefers the GitHub raw file.

## Hot update

Publish a GitHub Release (tag like `v1.1.0`). Users clicking **检查更新** can apply a hot update that overlays code while keeping:

- `scripts/`
- `ahk_filter_config.json` (checkboxes, hotkeys, group collapse state)

## Tests

```bat
python -m unittest discover -s tests -v
```

## License

MIT
