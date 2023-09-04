# GUI Utilities

## Mr. SKFONT
![skfont_editor_preview](https://github.com/TheOpponent/st3-translation-notes/assets/8432212/0611332e-6340-4dfd-8758-ab1ccd528d9c)

This is a tile editor written in wxPython created solely to edit [SKFONT.CG](https://github.com/TheOpponent/st3-translation-notes/wiki/SKFONT.CG), which contains the font sheet. It is identical across all discs.

### Instructions

Mr. SKFONT requires Pillow and wxPython as dependencies.

```python3 skfont_editor.cg```

- Use the settings in the property grid, the mouse wheel, or the scroll bar to navigate the font tiles. Double click on a tile to set it as the tile offset.
- Click on the **Replace Tiles...** button to open a PNG file and overwrite the tiles starting at the currently selected tile. The PNG file must be an RGB image with 8 bits per channel and no transparency. The red channel of this image will be used to generate the font tiles. You will be asked to confirm the replacement of the tiles.
- Click on the **Export Tile...** button to export the currently selected tile to a PNG file. This currently supports exporting only one tile at a time.
- Click on the **Save SKFONT.CG** button to save your changes.

### Notes
The secondary font sheets SKFONT2.CG, SKFONT3.CG, and SKFONT4.CG are also supported, but they currently do not show the correct RAM locations.
