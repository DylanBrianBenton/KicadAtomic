import wx
import os
import kiutils.symbol
import copy
import pandas as pd
import sys
import json
import kiutils.items.common

device_library_path = r"BaseSymbols.kicad_sym"
config_file = "AtomicPaths.txt"  # File to save the directory path

def load_saved_directory():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return f.read().strip()
    return ""

def save_directory(path):
    with open(config_file, 'w') as f:
        f.write(path)

class SymbolUpdaterApp(wx.Frame):
    def __init__(self, parent, title):
        super(SymbolUpdaterApp, self).__init__(parent, title=title, size=(400, 450))

        panel = wx.Panel(self)

        # CSV File Selection Button
        self.csv_file_label = wx.StaticText(panel, label="No file selected", pos=(20, 20))
        self.csv_button = wx.Button(panel, label="Choose CSV", pos=(20, 50))
        self.csv_button.Bind(wx.EVT_BUTTON, self.on_select_file)

        # Save Directory Button
        self.dir_label = wx.StaticText(panel, label="No directory selected", pos=(20, 100))
        self.dir_button = wx.Button(panel, label="Choose Save Directory", pos=(20, 130))
        self.dir_button.Bind(wx.EVT_BUTTON, self.on_select_directory)

        self.combo_label = wx.StaticText(panel, label="Select option:", pos=(20, 180))
        self.combo = wx.ComboBox(panel, choices=["Option 1", "Option 2", "Option 3"], pos=(20, 210))

        # Execute button
        self.run_button = wx.Button(panel, label="Run Script", pos=(20, 250))
        self.run_button.Bind(wx.EVT_BUTTON, self.on_run_script)

        self.file_path = None
        self.save_directory = load_saved_directory()
        if self.save_directory:
            self.dir_label.SetLabel(f"Save directory: {self.save_directory}")

    def on_select_file(self, event):
        file_dialog = wx.FileDialog(self, "Open CSV file", wildcard="CSV files (*.csv)|*.csv", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if file_dialog.ShowModal() == wx.ID_OK:
            self.file_path = file_dialog.GetPath()
            file_name = os.path.basename(self.file_path)
            self.csv_file_label.SetLabel(f"Selected file: {file_name}")
        else:
            self.file_path = None
            self.csv_file_label.SetLabel("No file selected")

    def on_select_directory(self, event):
        dir_dialog = wx.DirDialog(self, "Select Save Directory", style=wx.DD_DEFAULT_STYLE)
        if dir_dialog.ShowModal() == wx.ID_OK:
            self.save_directory = dir_dialog.GetPath()
            self.dir_label.SetLabel(f"Save directory: {self.save_directory}")
            save_directory(self.save_directory)  # Save the directory path

    def on_run_script(self, event):
        if not self.file_path:
            wx.MessageBox("Please select a CSV file first.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if not self.save_directory:
            wx.MessageBox("Please select a directory to save the output.", "Error", wx.OK | wx.ICON_ERROR)
            return

        file_name = os.path.basename(self.file_path)
        file = os.path.splitext(file_name)

        df = pd.read_csv(self.file_path)
        symbols_data = df.to_dict(orient='records')

        library = kiutils.symbol.SymbolLib.from_file(device_library_path)

        NewParts = []
        for symbol_row in symbols_data:
            symbol_name = symbol_row.get("Symbol")
            NewPart_name = symbol_row.get("Part")

            if not symbol_name or not NewPart_name:
                print(f"Skipping row due to missing 'Symbol' or 'Part' value: {symbol_row}")
                continue

            symbol_found = None
            for symbol in library.symbols:
                if symbol.entryName == symbol_name:
                    symbol_found = symbol
                    break

            if symbol_found:
                NewPart = copy.deepcopy(symbol_found)
                NewPart.entryName = NewPart_name
                NewPart.libId = NewPart.libId.replace(symbol_name, NewPart_name)

                existing_properties = {prop.key: prop for prop in NewPart.properties}

                properties_to_update = ["Value", "Description", "Footprint", "Datasheet", "Package", "Type", "Series", "Brand"]
                properties_to_hide = ["Description", "Footprint", "Datasheet", "Package", "Type", "Series", "Brand"]

                for field in properties_to_update:
                    if field in symbol_row:
                        if field in existing_properties:
                            prop = existing_properties[field]
                            prop.value = symbol_row[field]
                            if field in properties_to_hide:
                                prop.effects = kiutils.items.common.Effects(hide=True)
                        else:
                            new_property = kiutils.symbol.Property(field, symbol_row[field])
                            NewPart.properties.append(new_property)

                            if field in properties_to_hide:
                                new_property.effects = kiutils.items.common.Effects(hide=True)

                NewParts.append(NewPart)
            else:
                print(f"Symbol '{symbol_name}' not found in the library.")

        if NewParts:
            new_library = kiutils.symbol.SymbolLib()
            new_library.symbols.extend(NewParts)
            output_path = os.path.join(self.save_directory, file[0] + '.kicad_sym')
            new_library.to_file(output_path)
            wx.MessageBox("New symbol library created with {len(NewParts)} symbols at {output_path}.", "Done", wx.OK)
        else:
            wx.MessageBox("No symbols were copied or created.", "Done", wx.OK)


if __name__ == "__main__":
    app = wx.App(False)
    frame = SymbolUpdaterApp(None, "Symbol Updater")
    frame.Show()
    app.MainLoop()