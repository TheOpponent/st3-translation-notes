import os
import struct

import wx
import wx.grid
import wx.propgrid as wxpg
import wx.lib.agw.hyperlink as hl
from PIL import Image, ImageDraw, ImageOps

class MainFrame(wx.Frame):

    TILE_MAX: int
    "Total number of tiles in SKFONT.CG."

    tile_size: int
    "Length of each side of the FontTile image in pixels."

    tile_data_length: int
    "Length of FontTile data in bytes."

    tile_rows: int
    "Number of rows visible in the tile grid viewer."

    tile_cols: int
    "Number of columns visible in the tile grid viewer."

    tile_scale: int
    "Scaling factor for the tile grid viewer, starting at 1."

    tile_offset: int
    "Starting tile number in the tile grid viewer."

    selected_tile: int
    "Selected tile in the tile grid viewer."

    tile_grid: wx.Bitmap
    "The tile grid is the bitmap image formed from assembled FontTile images."

    tile_cursor: tuple[int,int]
    "Position of the cursor in the tile grid viewer."

    def __init__(self, parent, title):
        super().__init__(parent=None, title=title, size=(800, 600))

        self.VERSION = "1.1.0"
        self.TILE_MAX = 3488

        main_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.file_data = b''
        self.tiles = []
        self.tile_rows = 10
        self.tile_cols = 10
        self.tile_scale = 1
        self.tile_offset = 0
        self.invert_image = False
        self.selected_tile = 0
        self.tile_grid = wx.Bitmap()
        self.tile_cursor = (0,0)

        self.modified = False

        self.filename = wx.FileSelector("Open SKFONT.CG",default_filename="SKFONT.CG",flags=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if self.filename != "":
            if os.stat(self.filename).st_size == 1178944:
                self.tile_size = 26
            elif os.stat(self.filename).st_size == 1004544:
                self.tile_size = 24
            elif os.stat(self.filename).st_size == 844096:
                self.tile_size = 22
            else:
                wx.MessageBox("Invalid SKFONT.CG file.","Error",style=wx.OK | wx.ICON_ERROR)
                exit()

            self.tiles = []
            self.tile_data_length = (self.tile_size ** 2) // 2

            with open(self.filename,"rb") as skfont:
                self.file_data = skfont.read()
            for i in range(0,self.TILE_MAX):
                tile = FontTile(self.file_data[i * self.tile_data_length:i * self.tile_data_length + self.tile_data_length],self.tile_size)
                self.tiles.append(tile)
        else:
            exit()

        # Create property grid panel.
        self.pg_panel = wx.Panel(self)
        self.pg_source = ""
        self.pg = wxpg.PropertyGrid(self.pg_panel, style=wxpg.PG_SPLITTER_AUTO_CENTER)
        self.pg.SetMinSize((230,0))
        self.pg.SetColumnProportion(0,4)
        self.pg.SetColumnProportion(1,2)

        self.pg.Append(wxpg.PropertyCategory("Tile Grid View"))
        self.pg.Append(wxpg.IntProperty("Tile Offset","TileOffset",value=self.tile_offset))
        self.pg.SetPropertyEditor("TileOffset", "SpinCtrl")
        self.pg.SetPropertyAttribute("TileOffset", "Min",0)
        self.pg.SetPropertyAttribute("TileOffset", "Max",self.TILE_MAX - (self.tile_rows * self.tile_cols))

        self.pg.Append(wxpg.IntProperty("Rows","TileRows",value=self.tile_rows))
        self.pg.SetPropertyEditor("TileRows", "SpinCtrl")
        self.pg.SetPropertyAttribute("TileRows", "Min",0)

        self.pg.Append(wxpg.IntProperty("Columns","TileCols",value=self.tile_cols))
        self.pg.SetPropertyEditor("TileCols", "SpinCtrl")
        self.pg.SetPropertyAttribute("TileCols", "Min",0)

        self.pg.Append(wxpg.IntProperty("Scale","TileScale",value=self.tile_scale))
        self.pg.SetPropertyEditor("TileScale", "SpinCtrl")
        self.pg.SetPropertyAttribute("TileScale", "Min",1)

        self.pg.Append(wxpg.BoolProperty("Invert (Preview Only)","Invert",value=self.invert_image))
        self.pg.SetPropertyAttribute("Invert",wxpg.PG_BOOL_USE_CHECKBOX,True)

        self.pg.Append(wxpg.PropertyCategory("Selected Tile Properties"))
        self.pg.Append(wxpg.IntProperty("Selected Tile","SelectedTile",value=self.selected_tile))
        self.pg.SetPropertyEditor("SelectedTile", "SpinCtrl")
        self.pg.SetPropertyAttribute("SelectedTile", "Min",0)
        self.pg.SetPropertyAttribute("SelectedTile", "Max",self.TILE_MAX)

        self.pg.Append(wxpg.StringProperty("Selected Tile Location","SelectedTileLocation",value=str(hex(self.selected_tile))))
        self.pg.Append(wxpg.StringProperty("RAM Location","RAMLocation",value=str(hex(self.selected_tile + 0x8ccd7ec0))[2:]))

        self.pg.Bind(wx.EVT_TEXT, self.on_text_entry)
        self.pg.Bind(wx.EVT_SPINCTRL, self.on_spinctrl)
        self.pg.Bind(wxpg.EVT_PG_CHANGED, self.on_property_change)

        # Add buttons.
        self.open_png_button = wx.Button(self.pg_panel,label="Replace Tiles...")
        self.open_png_button.Bind(wx.EVT_BUTTON,self.on_replace_tiles)
        self.save_png_button = wx.Button(self.pg_panel,label="Export Tile...")
        self.save_png_button.Bind(wx.EVT_BUTTON,self.on_export_tile)
        self.save_button = wx.Button(self.pg_panel,label="Save SKFONT.CG")
        self.save_button.Bind(wx.EVT_BUTTON,self.on_save_skfont)
        self.about_button = wx.Button(self.pg_panel,label="About...")
        self.about_button.Bind(wx.EVT_BUTTON,self.on_about)

        pg_sizer = wx.BoxSizer(wx.VERTICAL)
        pg_sizer.Add(self.pg, 2,flag=wx.EXPAND)
        pg_sizer.Add(self.open_png_button, flag=wx.EXPAND)
        pg_sizer.Add(self.save_png_button, flag=wx.EXPAND)
        pg_sizer.Add(self.save_button, flag=wx.EXPAND)
        pg_sizer.Add(wx.StaticLine(self.pg_panel), flag=wx.ALL, border=5)
        pg_sizer.Add(self.about_button, flag=wx.EXPAND)
        self.pg_panel.SetSizer(pg_sizer)

        # Create tile editor panel.
        self.tile_grid = self.create_tile_bitmap(self.tiles,self.tile_offset,self.TILE_MAX,self.tile_rows,self.tile_cols,self.tile_size,self.tile_scale)
        self.tilegrid_panel = GridBitmap(self,self.tile_grid,self.tile_rows,self.tile_cols)
        tilegrid_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.scrollbar = wx.ScrollBar(self.tilegrid_panel,style=wx.SB_VERTICAL)
        self.scrollbar.SetScrollbar(0,self.tile_rows,self.TILE_MAX // self.tile_cols,self.tile_rows)
        self.scrollbar.Bind(wx.EVT_KEY_DOWN,self.on_scroll_key)
        self.scrollbar.Bind(wx.EVT_SCROLL,self.on_scroll)

        tilegrid_sizer.AddStretchSpacer()
        tilegrid_sizer.Add(self.scrollbar,0,wx.EXPAND)
        self.tilegrid_panel.SetSizer(tilegrid_sizer)

        self.tilegrid_panel.Bind(wx.EVT_LEFT_DOWN,self.on_tile_click)
        self.tilegrid_panel.Bind(wx.EVT_LEFT_DCLICK,self.on_tile_doubleclick)
        self.tilegrid_panel.Bind(wx.EVT_MOUSEWHEEL,self.on_mousewheel)
        self.tilegrid_panel.Bind(wx.EVT_CHAR_HOOK,self.on_tilegrid_panel_key)

        # Populate main sizer.
        main_sizer.Add(self.pg_panel, 0, wx.EXPAND)
        main_sizer.Add(self.tilegrid_panel, 1, wx.EXPAND)

        self.SetSizer(main_sizer)
        self.Bind(wx.EVT_CLOSE,self.on_close)

    def create_tile_bitmap(self,tile_source: list,tile_range_start: int,tile_range_max: int,rows: int,cols: int,size: int,scale: int,add_gridlines=False):
        """Regenerate the bitmap for the tile grid from tile_source, a list of FontTile objects,
        starting from tile_range_start and not exceeding tile_range_max. Returns a wx.Bitmap.
        Call the Refresh() method on the window containing it afterward."""

        # Rows and columns are transposed for x and y dimensions.
        tile_grid = Image.new("RGB",(cols * size,rows * size))
        if add_gridlines:
            tile_grid_draw = ImageDraw.Draw(tile_grid)

        current_tile = 0
        for y in range(0,rows):
            for x in range(0,cols):
                if tile_range_start + current_tile < tile_range_max:
                    tile_image = tile_source[tile_range_start + current_tile].image
                else:
                    # If the tile range exceeds the file size, fill in with blank images.
                    tile_image = Image.new("RGB",(size,size))

                tile_grid.paste(tile_image,(x * size,y * size))
                if add_gridlines and current_tile > 0:
                    tile_grid_draw.line([(x * size,0),(x * size,size)],fill=(128,128,128))

                current_tile += 1

        if scale > 1:
            tile_grid = tile_grid.resize((cols * size * scale, rows * size * scale),resample=Image.Resampling.NEAREST)

        if self.invert_image:
            tile_grid = ImageOps.invert(tile_grid)

        tile_grid_output = wx.Image(tile_grid.size,tile_grid.tobytes())

        return wx.Bitmap(tile_grid_output)

    def save_skfont(self):
        output_data = b''
        for tile in self.tiles:
            output_data += tile.data

        try:
            with open(self.filename,"wb") as file:
                file.write(output_data)
            wx.MessageBox(f"{self.filename} saved successfully.","Save Complete",wx.OK)
            self.modified = False
        except Exception as e:
            wx.MessageBox(str(e),"Error",wx.OK | wx.ICON_ERROR)

    def on_replace_tiles(self,event):
        """Open a PNG image and convert it into FontTile objects. The FontTile(s) will
        overwrite the selected tile."""

        image_tiles = []
        new_tiles = []
        image_filename = wx.FileSelector("Open Image",wildcard="*.png",flags=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if image_filename != "":

            with Image.open(image_filename) as image:
                if image.height != self.tile_size:
                    wx.MessageDialog(f"Image must have a height of {self.tile_size} pixels.","Invalid Image",wx.OK | wx.ICON_ERROR)
                    return
                if image.width % self.tile_size != 0:
                    wx.MessageDialog(f"Image must have a width divisible by {self.tile_size} pixels.","Invalid Image",wx.OK | wx.ICON_ERROR)
                    return
                if image.mode != "RGB":
                    wx.MessageDialog(f"Image must be RGB with 8 bits per channel and no transparency.","Invalid Image",wx.OK | wx.ICON_ERROR)

                # Divide input image into square tiles.
                for x in range(0,image.width // self.tile_size):
                    image_tiles.append(image.crop((x * self.tile_size,0,(x + 1) * self.tile_size,self.tile_size)))

                # Convert tiles into FontTiles.
                for tile in image_tiles:
                    converted_tile = tile.getdata(0)
                    array = b''
                    for y in range(0,self.tile_size,2):
                        # Read each byte of converted_tile and convert into two pixels at a time vertically. Each byte is two 4-bit values, with the right nybble on top and the left nybble on the bottom.
                        for x in range(0,self.tile_size):
                            hi_pixel = converted_tile[x + y * self.tile_size] >> 4
                            lo_pixel = converted_tile[x + ((y + 1) * self.tile_size)] & 0xf0
                            array += struct.pack("=B",lo_pixel | hi_pixel)
                    new_tiles.append(FontTile(array,self.tile_size))

            new_tiles_bitmap = self.create_tile_bitmap(new_tiles,0,len(new_tiles),1,len(new_tiles),self.tile_size,1,True)
            with self.ReplaceTilesDialog(self,len(new_tiles),self.selected_tile,new_tiles_bitmap) as dialog:
                if dialog.ShowModal() == wx.OK:
                    for i in range(0,len(new_tiles)):
                        self.tiles[self.selected_tile + i] = new_tiles[i]
                    self.modified = True

            # Update view.
            self.tile_grid = self.create_tile_bitmap(self.tiles,self.tile_offset,self.TILE_MAX,self.tile_rows,self.tile_cols,self.tile_size,self.tile_scale)
            self.tilegrid_panel.bitmap = self.tile_grid
            self.tilegrid_panel.Refresh()

    def on_export_tile(self,event):
        """Save the selected tiles as a PNG image."""

        with self.ExportTilesDialog(self,self.selected_tile) as dialog:
            if dialog.ShowModal() == wx.OK:
                tile_count = dialog.tile_count
                output_image = Image.new("RGB",(self.tile_size * tile_count,self.tile_size))
                for i in range(0,tile_count):
                    output_image.paste(self.tiles[self.selected_tile + i].image,(self.tile_size * i,0))
                save_filename = wx.FileSelector("Save PNG Image",wildcard="*.png",flags=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
                if save_filename != "":
                    try:
                        output_image.save(save_filename,"PNG")
                    except Exception as e:
                        wx.MessageBox(str(e),"Error",wx.OK | wx.ICON_ERROR)

    def on_save_skfont(self,event):
        self.save_skfont()
        event.Skip()

    def on_about(self,event):
        with self.AboutDialog(self,self.VERSION) as dialog:
            dialog.ShowModal()
        event.Skip()

    def on_text_entry(self,event):
        self.pg_source = 'text'
        event.Skip()

    def on_spinctrl(self,event):
        self.pg_source = 'spinctrl'
        event.Skip()

    def on_property_change(self,event):
        prop = event.GetProperty()
        tile_limit = self.tile_rows * self.tile_cols

        if prop:
            name = prop.GetName()
            value = prop.GetValue()

            if name == "TileOffset":
                self.selected_tile += value - self.tile_offset
                self.tile_offset = value
            elif name == "TileRows":
                self.tile_rows = value
            elif name == "TileCols":
                self.tile_cols = value
            elif name == "TileScale":
                self.tile_scale = value
            elif name == "Invert":
                self.invert_image = value

            # Update highlighted tile.
            elif name == "SelectedTile":
                if self.pg_source != "mousewheel":
                    self.selected_tile = value
                    self.tile_cursor = divmod(self.selected_tile - self.tile_offset,self.tile_cols)[::-1]

            # Update the tile_offset maximum based on the current visible number of tiles.
            self.pg.SetPropertyAttribute("TileOffset", "Max",self.TILE_MAX - tile_limit)

            if self.selected_tile < self.tile_offset:
                if self.pg_source != 'keyboard':
                    self.tile_offset = self.selected_tile
                    self.tile_cursor = (0,0)
                else:
                    self.tile_offset -= self.tile_cols
                    self.tile_cursor = (self.selected_tile - self.tile_offset,0)
                self.pg.SetPropertyValue("TileOffset",self.tile_offset)

            elif self.selected_tile >= self.tile_offset + tile_limit:
                if self.pg_source in ['keyboard','mousewheel']:
                    self.tile_offset += self.tile_cols
                else:
                    self.tile_offset = self.selected_tile - tile_limit + 1
                    self.tile_cursor = (self.tile_cols,self.tile_rows)

                self.pg.SetPropertyValue("TileOffset",self.tile_offset)

            # Add 1 to the range to allow the last row to be incomplete.
            self.scrollbar.SetScrollbar(self.tile_offset // self.tile_cols,self.tile_rows,self.TILE_MAX // self.tile_cols + 1,self.tile_rows)

            self.pg.SetPropertyValue("SelectedTile",self.selected_tile)

            # Update RAM address values.
            self.pg.SetPropertyValueString("SelectedTileLocation",str(hex(self.selected_tile * self.tile_data_length)))
            self.pg.SetPropertyValueString("RAMLocation",str(hex(self.selected_tile * self.tile_data_length + 0x8ccd7ec0))[2:])

            # Update view.
            self.tile_grid = self.create_tile_bitmap(self.tiles,self.tile_offset,self.TILE_MAX,self.tile_rows,self.tile_cols,self.tile_size,self.tile_scale)
            self.tilegrid_panel.bitmap = self.tile_grid
            self.tilegrid_panel.rows = self.tile_rows
            self.tilegrid_panel.cols = self.tile_cols
            self.tilegrid_panel.select_tile(self.tile_cursor)
            self.tilegrid_panel.Refresh()

    def on_tile_click(self,event):
        """Update self.selected_tile when the tile grid is clicked on."""

        x = event.GetX()
        y = event.GetY()
        width,height = self.tile_grid.GetSize()
        self.tilegrid_panel.SetFocus()
        if x < width and y < height:
            self.tile_cursor = (x // self.tilegrid_panel.cell_height,y // self.tilegrid_panel.cell_width)
            self.selected_tile = self.tile_offset + self.tile_cursor[0] + self.tile_cursor[1] * self.tile_cols
            self.tilegrid_panel.select_tile(self.tile_cursor)
            self.pg.ChangePropertyValue("SelectedTile",self.selected_tile)

    def on_tile_doubleclick(self,event):
        """Change tile offset to tile that was double clicked."""

        x = event.GetX()
        y = event.GetY()
        width,height = self.tile_grid.GetSize()
        self.tilegrid_panel.SetFocus()
        if x < width and y < height:
            self.tile_offset = self.selected_tile
            self.tile_cursor = (0,0)
            self.tilegrid_panel.select_tile((0,0))
            self.pg.ChangePropertyValue("TileOffset",self.tile_offset)

    def on_tilegrid_panel_key(self,event):
        """Move the cursor in response to the arrow keys and Page Up and Page Down."""

        key = event.GetKeyCode()
        tile_limit = self.tile_rows * self.tile_cols

        if key == wx.WXK_DOWN:
            self.selected_tile += self.tile_cols
            self.pg_source = 'keyboard'
        elif key == wx.WXK_UP:
            self.selected_tile -= self.tile_cols
            self.pg_source = 'keyboard'
        elif key == wx.WXK_LEFT:
            self.selected_tile -= 1
            self.pg_source = 'keyboard'
        elif key == wx.WXK_RIGHT:
            self.selected_tile += 1
            self.pg_source = 'keyboard'
        elif key == wx.WXK_PAGEDOWN:
            self.tile_offset += tile_limit
            self.selected_tile += tile_limit
            self.pg_source = 'keyboard'
        elif key == wx.WXK_PAGEUP:
            self.tile_offset -= tile_limit
            self.selected_tile -= tile_limit
            self.pg_source = 'keyboard'
        elif key == wx.WXK_HOME:
            self.tile_offset = 0
            self.selected_tile = 0
            self.pg_source = 'keyboard'
        elif key == wx.WXK_END:
            self.tile_offset = self.TILE_MAX - tile_limit + 1
            self.selected_tile = self.TILE_MAX
            self.pg_source = 'keyboard'

        self.tile_offset = max(0,min(self.tile_offset,self.TILE_MAX - tile_limit + 1))
        self.selected_tile = max(0,min(self.selected_tile,self.TILE_MAX))
        self.pg.SetPropertyValue("TileOffset",self.tile_offset)
        self.pg.ChangePropertyValue("SelectedTile",self.selected_tile)

    def on_mousewheel(self,event):
        """Scroll one tile row on mouse wheel input."""

        tile_limit = self.tile_rows * self.tile_cols
        self.pg_source = 'mousewheel'
        rotation = event.GetWheelRotation()

        if rotation > 0:
            if self.tile_offset > 0:
                self.selected_tile -= self.tile_cols
            self.tile_offset -= self.tile_cols
        else:
            if self.tile_offset + tile_limit + self.tile_cols < self.TILE_MAX:
                self.tile_offset += self.tile_cols
                self.selected_tile += self.tile_cols

        self.tile_offset = max(0,min(self.tile_offset,self.TILE_MAX - tile_limit))
        self.selected_tile = max(0,min(self.selected_tile,self.TILE_MAX - tile_limit))
        self.pg.SetPropertyValue("TileOffset",self.tile_offset)
        self.pg.ChangePropertyValue("SelectedTile",self.selected_tile)
        event.Skip()

    def on_scroll_key(self,event):
        """The scrollbar should not respond to Left or Right arrow keys,
        so consume those inputs here."""

        key = event.GetKeyCode()

        if key in [wx.WXK_LEFT,wx.WXK_RIGHT,wx.WXK_UP,wx.WXK_DOWN]:
            return

        event.Skip()

    def on_scroll(self,event):
        """Scroll at least one tile row on scrollbar input."""

        value = self.scrollbar.GetThumbPosition()

        # Store old tile values based on cursor position, then replace with calculated values from scrollbar position.
        old_tile_offset = self.tile_offset % self.tile_cols
        old_selected_tile = self.selected_tile - self.tile_offset
        self.tile_offset = value * self.tile_cols + old_tile_offset
        self.selected_tile = self.tile_offset + old_selected_tile

        # Bounds checking for tile values.
        self.tile_offset = max(0,min(self.tile_offset,self.TILE_MAX))
        self.selected_tile = max(0,min(self.selected_tile,self.TILE_MAX))

        self.pg.SetPropertyValue("TileOffset",self.tile_offset)
        self.pg.ChangePropertyValue("SelectedTile",self.selected_tile)
        event.Skip()

    def on_close(self,event):
        if event.CanVeto() and self.modified:
            confirm = wx.MessageBox("Save changes to SKFONT.CG before closing?","Confirm Exit",style=wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
            if confirm == wx.CANCEL:
                event.Veto()
                return
            elif confirm == wx.YES:
                self.save_skfont()

        event.Skip()


    class ReplaceTilesDialog(wx.Dialog):
        """Dialog that shows the input image with grid lines drawn over it
        before they are committed to the main tile grid."""

        def __init__(self,parent,tile_count: int,selected_tile: int,tile_grid_bitmap: wx.Bitmap,title="Replacing Tiles"):
            super().__init__(parent,wx.ID_ANY,title=title)

            dialog_sizer = wx.BoxSizer(wx.VERTICAL)

            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_panel = wx.Panel(self)
            label = wx.StaticText(main_panel,label=f"Replacing {tile_count} tile(s) at tile number {selected_tile}.")
            tilepanel_grid = wx.StaticBitmap(main_panel,bitmap=tile_grid_bitmap)
            main_sizer.Add(label,0,wx.ALL | wx.CENTER,10)
            main_sizer.Add(tilepanel_grid,0,wx.ALL | wx.CENTER,10)

            ok_sizer = wx.StdDialogButtonSizer()
            ok_button = wx.Button(main_panel,wx.ID_OK)
            ok_button.Bind(wx.EVT_BUTTON,self.on_ok)
            ok_sizer.AddButton(ok_button)
            cancel_button = wx.Button(main_panel,wx.ID_CANCEL)
            cancel_button.Bind(wx.EVT_BUTTON,self.on_cancel)
            ok_sizer.AddButton(cancel_button)
            ok_sizer.Realize()
            main_sizer.Add(ok_sizer,0,wx.ALL | wx.CENTER,5)

            main_panel.SetSizer(main_sizer)

            dialog_sizer.Add(main_panel,0,wx.CENTER)

            self.SetSizer(dialog_sizer)
            self.Fit()

        def on_ok(self,event):
            self.EndModal(wx.OK)

        def on_cancel(self,event):
            self.EndModal(wx.CANCEL)


    class ExportTilesDialog(wx.Dialog):
        """Prompt the user to select a number of tiles to export."""
        # TODO: Show a live preview of the tiles to be exported.

        def __init__(self,parent,selected_tile: int,title="Export Tiles"):
            super().__init__(parent,wx.ID_ANY,title=title)

            self.selected_tile = selected_tile
            self.parent = parent
            self.tile_count = 1
            dialog_sizer = wx.GridBagSizer()

            main_panel = wx.Panel(self)

            label1 = wx.StaticText(main_panel,label=f"Exporting tiles starting from tile number {selected_tile}.")
            label2 = wx.StaticText(main_panel,label=f"Select the number of tiles to export:")
            self.spinctrl = wx.SpinCtrl(main_panel,wx.ID_ANY,min=1,max=parent.TILE_MAX,initial=1)
            self.spinctrl.Bind(wx.EVT_SPINCTRL,self.on_spinctrl)

            ok_sizer = wx.StdDialogButtonSizer()
            ok_button = wx.Button(main_panel,wx.ID_OK)
            ok_button.Bind(wx.EVT_BUTTON,self.on_ok)
            ok_sizer.AddButton(ok_button)
            cancel_button = wx.Button(main_panel,wx.ID_CANCEL)
            cancel_button.Bind(wx.EVT_BUTTON,self.on_cancel)
            ok_sizer.AddButton(cancel_button)
            ok_sizer.Realize()

            dialog_sizer.Add(label1,wx.GBPosition(0,0),wx.GBSpan(1,2),flag=wx.ALIGN_LEFT | wx.ALL,border=5)
            dialog_sizer.Add(label2,wx.GBPosition(1,0),wx.GBSpan(1,1),flag=wx.ALIGN_LEFT | wx.ALL,border=5)
            dialog_sizer.Add(self.spinctrl,wx.GBPosition(1,1),wx.GBSpan(1,1),flag=wx.ALL,border=5)
            dialog_sizer.Add(ok_sizer,wx.GBPosition(2,0),wx.GBSpan(1,2),flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL,border=5)

            main_panel.SetSizer(dialog_sizer)
            main_panel.Fit()
            self.Fit()

        def on_spinctrl(self,event):
            self.tile_count = self.spinctrl.GetValue()
            event.Skip()

        def on_yes(self,event):
            self.EndModal(wx.YES)

        def on_no(self,event):
            self.EndModal(wx.NO)


    class AboutDialog(wx.Dialog):
        def __init__(self,parent,version):
            super().__init__(parent,wx.ID_ANY,title="About Mr. SKFONT")

            sizer = wx.GridBagSizer()
            panel = wx.Panel(self)

            text = wx.StaticText(panel,label=f"Mr. SKFONT version {version} by The Opponent\nPart of the Sakura Taisen 3 translation notes repository.\n\nThis program is in the public domain (Unlicense).",style=wx.LEFT)
            link = hl.HyperLinkCtrl(panel,-1,"https://github.com/TheOpponent/st3-translation-notes",URL="https://github.com/TheOpponent/st3-translation-notes",style=wx.TE_LEFT)
            button = wx.Button(panel,label="OK")
            button.Bind(wx.EVT_BUTTON,self.on_button)
            spacer_top = wx.StaticText(panel,label="")
            spacer_top.SetMinSize((0,10))
            spacer_left = wx.StaticText(panel,label="")
            spacer_left.SetMinSize((20,0))
            spacer_right = wx.StaticText(panel,label="")
            spacer_right.SetMinSize((20,0))

            # TODO: Is there a better way to add padding on one side?
            sizer.Add(spacer_top,wx.GBPosition(0,0),flag=wx.EXPAND)
            sizer.Add(spacer_left,wx.GBPosition(1,0),flag=wx.EXPAND)
            sizer.Add(spacer_right,wx.GBPosition(1,2),flag=wx.EXPAND)
            sizer.Add(text,wx.GBPosition(2,1),flag=wx.ALIGN_LEFT | wx.ALL,border=5)
            sizer.Add(link,wx.GBPosition(3,1),flag=wx.ALIGN_LEFT | wx.ALL,border=5)
            sizer.Add(button,wx.GBPosition(4,1),flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL,border=5)

            panel.SetSizer(sizer)
            panel.Fit()
            self.Fit()

        def on_button(self,event):
            self.EndModal(wx.OK)


class GridBitmap(wx.Panel):
    def __init__(self, parent, bitmap: wx.Bitmap, rows: int, cols: int):
        super().__init__(parent,wx.ID_ANY)
        self.bitmap = bitmap
        self.bitmap_width, self.bitmap_height = self.bitmap.GetSize()
        self.rows = rows
        self.cols = cols
        self.selected_tile = (0,0)
        self.highlight_pen = wx.Pen(wx.RED,2)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.Clear()
        dc.DrawBitmap(self.bitmap, 0, 0, True)
        self.bitmap_width, self.bitmap_height = self.bitmap.GetSize()
        self.cell_width = self.bitmap_width // self.cols
        self.cell_height = self.bitmap_height // self.rows

        dc.SetPen(wx.GREY_PEN)
        for i in range(self.rows):
            y = i * self.cell_height
            dc.DrawLine(0, y, self.bitmap_width, y)
        for i in range(self.cols):
            x = i * self.cell_width
            dc.DrawLine(x, 0, x, self.bitmap_height)

        # Bounds checking for changed row and column values in parent Frame.
        if self.selected_tile[0] > self.cols - 1:
            self.selected_tile = (self.cols - 1,self.selected_tile[1])
        if self.selected_tile[1] > self.rows - 1:
            self.selected_tile = (self.selected_tile[0],self.rows - 1)

        # Draw cursor on selected tile.
        dc.SetPen(self.highlight_pen)
        dc.DrawLine(self.selected_tile[0] * self.cell_width - 1,self.selected_tile[1] * self.cell_height,(self.selected_tile[0] + 1) * self.cell_width + 1,self.selected_tile[1] * self.cell_height)
        dc.DrawLine(self.selected_tile[0] * self.cell_width,self.selected_tile[1] * self.cell_height - 1,self.selected_tile[0] * self.cell_width,(self.selected_tile[1] + 1) * self.cell_height + 1)
        dc.DrawLine(self.selected_tile[0] * self.cell_width,(self.selected_tile[1] + 1) * self.cell_height + 1,(self.selected_tile[0] + 1) * self.cell_width + 1,(self.selected_tile[1] + 1) * self.cell_height + 1)
        dc.DrawLine((self.selected_tile[0] + 1) * self.cell_width + 1,self.selected_tile[1] * self.cell_height,(self.selected_tile[0] + 1) * self.cell_width + 1,(self.selected_tile[1] + 1) * self.cell_height)

    def select_tile(self,tile_num: tuple):
        """Update the highlighted tile in the tile grid. tile_num is a tuple representing grid coordinates."""

        self.selected_tile = tile_num


class FontTile():
    """Contains the binary data for an SKFONT.CG tile and a PIL Image derived from that data."""

    data: bytes
    "Bytes representing a font tile."

    size: int
    "Length of this tile image in pixels."

    def __init__(self,data,size):
        self.data = data
        self.size = size
        array = [[0]*self.size for _ in range(0,self.size)]

        for y in range(0,self.size // 2):
            # Read two pixels at a time vertically. Each byte is two 4-bit values, with the right nybble on top and the left nybble on the bottom.
            lo_pixels = []
            hi_pixels = []
            for x in range(0,self.size):
                byte = data[x + (y * self.size)]
                lo_pixels.append((byte >> 4) * 16)
                hi_pixels.append((byte & 0xf) * 16)
            array[y*2] = hi_pixels
            array[(y*2)+1] = lo_pixels

        # Flatten list of lists.
        flat_array = []
        for i in array:
            flat_array += i

        # Convert monochrome pixel data to RGB, as conversion to mode L causes loss of precision.
        pixel_data = b''
        for i in flat_array:
            pixel_data += bytes((i,i,i))

        self.image = Image.frombytes("RGB",(self.size,self.size),pixel_data)


if __name__ == '__main__':
    app = wx.App()
    frame = MainFrame(None, title="Mr. SKFONT")
    frame.Show()
    app.MainLoop()
