# GUI Utilities

## Mr. SKFONT
![skfont_editor_preview](https://github.com/TheOpponent/st3-translation-notes/assets/8432212/98631d09-21c2-4b78-9e60-5f99de0b9908)

This is a tile editor written in wxPython created solely to edit [SKFONT.CG](https://github.com/TheOpponent/st3-translation-notes/wiki/SKFONT.CG), which contains the font sheet. It is identical across all discs.

### Instructions

Mr. SKFONT requires Pillow and wxPython as dependencies.

```python3 skfont_editor.py```

- Use the settings in the property grid, the mouse wheel, the scroll bar, or the keyboard to navigate the font tiles. Double click on a tile to set it as the tile offset.
- Click on the **Replace Tiles...** button to open a PNG file and overwrite the tiles starting at the currently selected tile. The PNG file must be an RGB image with 8 bits per channel and no transparency. The image must have a height of 26 and a width of a multiple of 26. The red channel of this image will be used to generate the font tiles. You will be asked to confirm the replacement of the tiles.
- Click on the **Export Tile...** button to export the currently selected tile or range of tiles to a PNG file. The exported image will contain the range of tiles in a single row.
- Click on the **Show Hex Data...** button to view the currently selected tile or range of tiles as hexadecimal data. This can be used to paste edited tile data into a hex editor or debugger while an emulator is running to show changes immediately.
- Click on the **Save SKFONT.CG** button to save your changes.

### Notes
The location of SKFONT.CG can be provided as a command line argument.

The secondary font sheets SKFONT2.CG, SKFONT3.CG, and SKFONT4.CG are also supported, but they currently do not show the correct RAM locations.
