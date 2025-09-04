# Save As Dialog Fix - Terminal Limitation

## Problem
Many terminals cannot distinguish between `Ctrl+S` and `Ctrl+Shift+S` because they send the same control code (ASCII 19). This is a fundamental terminal limitation, not a bug in the code.

## Solution
Changed the Save As keybinding from `Ctrl+Shift+S` to `F12` to work around this terminal limitation.

## New Key Bindings
- **Ctrl+S** - Save file
- **F12** - Save As (opens dialog with filename input and directory browser)
- **Ctrl+O** - Open file dialog

## Alternative Solutions If F12 Doesn't Work

If F12 doesn't work in your terminal, you can try these alternatives by editing `src/tino/ui/preview_app.py` line 271:

1. **Alt+S**: `Binding("alt+s", "save_file_as", "Save As")`
2. **Ctrl+A then S**: Create a two-key sequence
3. **Ctrl+D**: `Binding("ctrl+d", "save_file_as", "Save As")` 
4. **Escape then S**: `Binding("escape,s", "save_file_as", "Save As")`

## Testing
1. Run: `python -m tino`
2. Open or create a file
3. Press F12 to open the Save As dialog
4. Enter a filename and select a directory
5. Click Save

## Why This Happens
- Terminals were designed in the 1970s-80s with limited control codes
- Shift modifier often doesn't create distinct codes with Ctrl
- Modern terminal emulators maintain backward compatibility
- Function keys (F1-F12) have dedicated escape sequences

This is why many terminal apps use:
- Function keys for special operations
- Alt key combinations  
- Two-key sequences (like vim's `:w` for save)