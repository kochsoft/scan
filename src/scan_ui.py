#!/usr/bin/python
"""
This is a tkinter user interface for the command line tool scan.py.

Markus-Hermann Koch, https://github.com/kochsoft, 13th April 2025.
"""

import os
import sys
import logging
import tkinter as tk
import tkinter.filedialog
from pathlib import Path
from tkinter import ttk
from tkinter.filedialog import asksaveasfilename
from idlelib.tooltip import Hovertip

from scan import *


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()


pfname_script = Path(__file__)

pfname_png_logo = Path(pfname_script.parent, 'icons/logo.png')
pfname_png_single = Path(pfname_script.parent, 'icons/single_scan.png')
pfname_png_multi = Path(pfname_script.parent, 'icons/multi_scan.png')
pfname_png_disk = Path(pfname_script.parent, 'icons/disk.png')


class TextWindow:
    """A glorified text box."""
    def __init__(self, parent: tk.Tk, msg: str, img: Optional[tk.PhotoImage] = None, dim=(80,40)):
        self.root = tk.Toplevel(parent)
        self.root.wm_transient(parent)

        if img:
            panel = tk.Label(self.root, image=img)
            panel.grid(row=0, column=0)

        self.ta_content = tk.Text(self.root, width=dim[0], height=dim[1], state='normal', wrap=tk.WORD, font='Arial')
        self.ta_content.grid(row=0, column=1, sticky='ewns')
        self.ta_content.insert(0.0, msg)
        self.ta_content.config(state='disabled')

        self.button_ok = tk.Button(self.root, text='Close', command=self.close, bg='#009999')
        self.button_ok.grid(row=1, column=1, sticky='ew')

    def close(self):
        self.root.destroy()
        self.root.update()


class ScanGui:
    def __init__(self):

        self.width_column = 40
        self.padding_columns = 10

        self.root = None  # type: Optional[tk.Tk]
        self.frame = None  # type: Optional[tk.Frame]

        self.icon_logo = None  # type: Optional[tk.PhotoImage]
        self.icon_single = None  # type: Optional[tk.PhotoImage]
        self.icon_multi = None  # type: Optional[tk.PhotoImage]
        self.icon_disk = None  # type: Optional[tk.PhotoImage]

        self.var_combo_device = None  # type: Optional[tk.StringVar]
        self.combo_device = None  # type: Optional[ttk.Combobox]
        self.check_png = None  # type: Optional[tk.Checkbutton]
        self.check_A4 = None  # type: Optional[tk.Checkbutton]

        self.ta_log = None  # type: Optional[tk.Text]

        self.button_scan_adf = None  # type: Optional[tk.Button]
        self.button_scan_fb = None  # type: Optional[tk.Button]

        self.label_pages = None  # type: Optional[tk.Label]

        self.button_save = None  # type: Optional[tk.Button]

        self.menu = None  # type: Optional[tk.Menu]

        self.build_gui()

        if self.root:
            self.root.mainloop()
            #self.scan = Scan(self.print)
        else:
            _log.warning("No GUI available. Consider using the command line script, 'scan.py', directly.")
            sys.exit(1)

    def print(self, msg: str):
        print(msg)  # Todo: Move this into the target text area.

    def mb_about(self):
        msg = """This tkinter GUI is intended to provide a simple frontend to the otherwise useful
Sane scanner software. Focussing on the bare-bone most essential function:
Scanning!

Functionality encompasses
+ Scan of single pages into png or pdf.
+ Scan of multiple pages into pdf.

This may be done both from flatbed and, if available in the driver,
automatic document feeder (ADF).

April 2025, Markus-H. Koch ( https://github.com/kochsoft/scan )
"""
        TextWindow(self.root, msg, self.icon_single, (70,14))

    def set_png(self, val: bool):
        pass

    def set_force_A4(self, val: bool):
        pass

    def scan_single(self):
        pass

    def scan_multi(self):
        pass

    def save(self):
        pass

    def build_gui(self):
        # > Main Window. ---------------------------------------------
        self.root = tk.Tk()
        self.root.title("Scan")
        self.root.geometry('640x480')
        self.icon_logo = tk.PhotoImage(file=str(pfname_png_single))
        self.icon_single = tk.PhotoImage(file=str(pfname_png_single))
        self.icon_multi = tk.PhotoImage(file=str(pfname_png_multi))
        self.icon_disk = tk.PhotoImage(file=str(pfname_png_disk))
        self.root.iconphoto(True, self.icon_single)

        self.frame = tk.Frame(self.root)  #, bg='orange')
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=1)
        self.frame.pack(fill=tk.BOTH, expand=True)
        # < ----------------------------------------------------------
        # > Menu. ----------------------------------------------------
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)

        menu_files = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='File', menu=menu_files)
        menu_files.add_command(label='Exit', command=self.root.quit)

        menu_help = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Help', menu=menu_help)
        menu_help.add_command(label='About ...', command=self.mb_about)
        # < ----------------------------------------------------------
        # > Control elements. ----------------------------------------
        # https://www.pythontutorial.net/tkinter/tkinter-combobox/
        # [Note: The var for the combobox needs to be a persistent variable.]
        self.var_combo_device = tk.StringVar()
        self.combo_device = ttk.Combobox(self.frame, textvariable=self.var_combo_device, width=self.width_column)
        self.combo_device.grid(row=0,column=0, columnspan=2, sticky='ew')
        self.combo_device['values'] = '<empty>',
        self.combo_device['state'] = 'readonly'
        self.combo_device.current(0)
        Hovertip(self.combo_device, 'Once initialized, select the scanning device intended for usage.')

        var_png = tk.IntVar()
        self.check_png = tk.Checkbutton(self.frame, anchor=tk.W, text='as png', variable=var_png, command=lambda: self.set_png(bool(var_png.get())))
        self.check_png.grid(row=1, column=0, sticky='ew')
        Hovertip(self.check_png, 'Normally a PDF will be saved. Unless this is checked for PNG output.')

        var_A4 = tk.IntVar()
        self.check_A4 = tk.Checkbutton(self.frame, anchor=tk.W, text='force A4', variable=var_A4, command=lambda: self.set_force_A4(bool(var_A4.get())))
        self.check_A4.grid(row=1, column=1, sticky='ew')
        Hovertip(self.check_A4, 'If checked A4 image size will be enforced. This usually is unnecessary.')

        self.ta_log = tk.Text(self.frame, height=10, width=self.width_column, state='normal', wrap=tk.WORD)
        self.ta_log.grid(row=2, column=0, columnspan=2, sticky='ewns')
        self.ta_log.insert('1.0', 'Initializing. Please wait.')

        self.button_scan_fb = tk.Button(self.frame, image=self.icon_single, command=self.scan_single)
        self.button_scan_fb.grid(row=3, column=0, sticky='ew')
        Hovertip(self.button_scan_fb, 'Initialize a single flatbed scan.')

        self.button_scan_adf = tk.Button(self.frame, image=self.icon_multi, command=self.scan_multi)
        self.button_scan_adf.grid(row=3, column=1, sticky='ew')
        Hovertip(self.button_scan_adf, 'Initialize a potential multi-scan from the automatic document feed.')

        self.button_save = tk.Button(self.frame, image=self.icon_disk, command=self.save)
        self.button_save.grid(row=4, column=0, columnspan=2, sticky='ew')
        Hovertip(self.button_save, 'Save the current images list to disk.')

        self.label_pages = tk.Label(self.frame, text='Current number of pages: 0', relief=tk.RIDGE, anchor=tk.W)
        self.label_pages.grid(row=5, column=0, columnspan=2, sticky='ew')
        Hovertip(self.label_pages, 'If a document were to be saved now it should receive this many pages.')
        # < ----------------------------------------------------------

if __name__ == '__main__':
    ScanGui()
    print("Done.")
