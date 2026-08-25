# AHK_Filter

Desktop manager for **AutoHotkey v1.1** scripts under a `scripts/` folder.

Scan scripts, organize them into collapsible configuration groups, assign per-script hotkeys, and toggle everything with one customizable global start/stop hotkey — without repeatedly dismissing UAC prompts.

## Features

- **Visual manager** (CustomTkinter): groups + loose scripts, adaptive layout
- **Configuration groups**: each subfolder under `scripts/` is a group (collapsible, default collapsed, one-click select all)
- **Loose scripts**: `.ahk` files placed directly in `scripts/` appear below all groups
- **Per-script hotkey**: click to record; conflict detection included
- **Custom global start/stop hotkey** (default `Ctrl+Shift+F8`)
- **Refresh scan** button (only while globally stopped; safely tears down and rescans)
- **Admin once**: manager elevates on launch; script processes stay resident — start/stop only changes effectiveness via `Suspend`
- **In-place script wrapping**: each `.ahk` receives a managed block for remote enable/disable

## Requirements

- Windows 10/11
- Python 3.10+
- [AutoHotkey v1.1](https://www.autohotkey.com/) installed

## Install

```bat
pip install -r requirements.txt
```

## Run

```bat
run.bat
```

Optional working directory (defaults to project root):

```bat
python run.py "D:\my-setup"
```

## Script layout

```
scripts/
  Pure/                    # example configuration group
    Pure_RightFireK.ahk
    Pure_WheelDouble.ahk
  my-group/                # your own group (any folder name)
    feature.ahk
  standalone.ahk           # loose script (shown below groups)
```

On first open, **no scripts are checked** — tick the ones you want, then press **全局启动**.

## Usage

1. Put `.ahk` files in `scripts/` or a subfolder.
2. Launch AHK_Filter; scripts are detected and wrapped automatically.
3. Expand a group if needed, tick scripts (or use **全选** on a group).
4. **全局启动** — selected scripts become effective; others stay suspended.
5. Use a script hotkey to pause/resume it while running.
6. **全局终止** — suspend all (processes remain elevated).
7. **刷新扫描** — only after global stop; rescans `scripts/` and reinjects managed blocks.

Click **启停热键** in the toolbar to record a new global toggle combo.

Settings live in `ahk_filter_config.json` (local, not committed).

## Example scripts

| File | Behavior |
|------|----------|
| `scripts/Pure/Pure_RightFireK.ahk` | Hold right mouse button to repeatedly send K |
| `scripts/Pure/Pure_WheelDouble.ahk` | Double wheel-up burst-sends `2` |

## Tests

```bat
python -m unittest discover -s tests -v
```

## Notes

- Scripts must use AHK **v1.1** syntax.
- Avoid binding the same physical key in multiple active scripts.
- Do not hand-edit the `AHK_Filter MANAGED BLOCK` region.

## License

MIT
