#!/usr/bin/python
"""
This is a tkinter user interface for the command line tool scan.py.

Markus-Hermann Koch, https://github.com/kochsoft, 13th April 2025.

Literature:
===========
* Background threads talking to tkinter thread via events.
    https://stackoverflow.com/questions/64287940/update-tkinter-gui-from-a-separate-thread-running-a-command
* About threads and passing arguments.
    https://nitratine.net/blog/post/python-threading-basics/
"""

import os
import sys
import time
import logging
from threading import Thread
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
pfname_png_stop = Path(pfname_script.parent, 'icons/stop.png')

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
        self.icon_stop = None  # type: Optional[tk.PhotoImage]

        self.var_combo_device = None  # type: Optional[tk.StringVar]
        self.combo_device = None  # type: Optional[ttk.Combobox]
        self.var_check_seascape = None  # type: Optional[tk.IntVar]
        self.var_check_A4 = None  # type: Optional[tk.IntVar]
        self.check_seascape = None  # type: Optional[tk.Checkbutton]
        self.check_A4 = None  # type: Optional[tk.Checkbutton]

        self.ta_log = None  # type: Optional[tk.Text]

        self.button_scan_adf = None  # type: Optional[tk.Button]
        self.button_scan_fb = None  # type: Optional[tk.Button]

        self.label_pages = None  # type: Optional[tk.Label]

        self.button_save = None  # type: Optional[tk.Button]

        self.menu = None  # type: Optional[tk.Menu]

        self.build_gui()
        self.thread_init = None  # type: Optional[Thread]
        self.thread_scan = None  # type: Optional[Thread]

        if self.root:
            self.scan = None  # type: Optional[Scan]
            self.threaded_initialize_Scan_object()
            self.call_threaded(ScanGui.t_wait_and_bind_events, (self,))
            self.root.mainloop()
        else:
            _log.warning("No GUI available. Consider using the command line script, 'scan.py', directly.")
            sys.exit(1)

    @staticmethod
    def t_wait_and_bind_events(ui):
        """Threaded function that will sleep 0.5 seconds (until all GUI objects are defined), and then add
        all local event bindings for later self.root.event_generate('..', when='tail', [state=]) commands
        that in turn will trigger the event handlers registered below in self.build_GUI."""
        time.sleep(0.5)
        # _log.info("Initializing root bind.")
        ui.root.bind_all('<<init_complete>>', ui.handler_init)
        ui.root.bind_all('<<scan_complete>>', ui.handler_scan)

    @staticmethod
    def call_threaded(fct_thd, args4thd: Optional[tuple]=None) -> Thread:
        if args4thd:
            t = Thread(target=fct_thd, args=args4thd)
        else:
            t = Thread(target=fct_thd)
        t.daemon = True
        t.start()
        return t

    def get_combo_index_by_value(self, val: Optional[str] = None) -> Optional[int]:
        """Get the index of the combo_device combobox for the given string value. Or None if not found."""
        codes = Scan.get_available_codes()
        if val is None:
            val = self.var_combo_device.get()
        try:
            return codes.index(val)
        except ValueError:
            return None

    def handler_init(self, event: tk.Event):
        """Initialization handler."""
        self.print(f"Initialization complete. {len(Scan.data_devices_info)} devices have been identified.\n{self.scan}")
        self.enable_gui(True)
        code = self.scan.code
        index = 0
        codes = self.scan.get_available_codes()
        for elt in codes:
            if elt == code:
                break
            index = index + 1
        self.combo_device['values'] = tuple(codes)
        if index < len(codes):
            self.combo_device.current(index)
        elif len(codes):
            self.combo_device.current(0)

    def handler_scan(self, event: tk.Event):
        self.enable_gui(True)
        self.enable_stop(to_stop=False, enable=True, single_scan=True)
        self.enable_stop(to_stop=False, enable=True, single_scan=False)

    def cb_init(self):
        self.root.event_generate("<<init_complete>>", when='tail') #, state=123)

    def cb_scan(self):
        self.root.event_generate("<<scan_complete>>", when='tail')  # , state=123)

    @staticmethod
    def get_time(frmt: str = "%y%m%d_%H%M%S", unix_time_s: Optional[int] = None) -> str:
        """:return Time string for introduction into file names."""
        unix_time_s = int(time.time()) if unix_time_s is None else int(unix_time_s)
        return time.strftime(frmt, time.localtime(unix_time_s))

    def print(self, msg: str):
        if self.ta_log:
            self.ta_log.insert(1.0, f"{self.get_time('%H:%M:%S')}: {msg}\n")
        else:
            print(msg)

    def threaded_initialize_Scan_object(self):
        """Start a new thread for filling self.scan."""
        def t_init_scan_object(ui):
            ui.scan = Scan(cb_print=self.print, cb_init=ui.cb_init)
        self.call_threaded(t_init_scan_object, (self,))
        self.enable_gui(False)

    def threaded_initialize_scan_action(self, tp_: E_ScanType) -> Thread:
        def t_init_scan_action(ui, tp: E_ScanType):
            code = ui.var_combo_device.get()
            if code not in Scan.data_devices:
                Scan.init_device(code)
            if tp == E_ScanType.ST_MULTI_ADF:
                ui.scan.scan_adf(code=code, cb_done=ui.cb_scan)
            else:
                ui.scan.scan_flatbed(code=code, cb_done=ui.cb_scan)
        self.enable_gui(False)
        self.enable_stop(to_stop=True, enable=True, single_scan=(tp_ != E_ScanType.ST_MULTI_ADF))
        return self.call_threaded(t_init_scan_action, (self, tp_))

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

    def verify_scan_object(self) -> int:
        """Verifies if a scan object is available.
        :returns 0 if and only if a scan object is available."""
        if self.thread_init and self.thread_init.is_alive():
            self.print("Scanner initialization still running. Please wait.")
            return 1
        elif not self.scan:
            self.print("Scan object not available. Attempting to rebuild. Please wait.")
            self.threaded_initialize_Scan_object()
            return 2
        return 0

    def set_png(self, val: bool):
        pass

    def set_force_A4(self, val: bool):
        pass

    def scan_single(self):
        """Initialize flatbed-Scan, or cancel it, if such a thread is already running."""
        if self.thread_scan and self.thread_scan.is_alive():
            self.scan.scan_stop(self.var_combo_device.get())
        else:
            self.thread_scan = self.threaded_initialize_scan_action(E_ScanType.ST_SINGLE_FLATBED)

    def scan_multi(self):
        """Initialize ADF (Automatic Document Feeder) scan, or cancel it, if such a thread is already running."""
        if self.thread_scan and self.thread_scan.is_alive():
            self.scan.scan_stop(self.var_combo_device.get())
        else:
            self.thread_scan = self.threaded_initialize_scan_action(E_ScanType.ST_MULTI_ADF)

    def save(self):
        if self.verify_scan_object():
            return
        if not self.scan.images:
            self.print("No scanned images available for saving.")
            return
        force_A4 = bool(self.var_check_A4.get())
        seascape = bool(self.var_check_seascape.get())
        files = [('PDF', '*.pdf'), ('png', '*.png')]
        pfname_out = tk.filedialog.asksaveasfilename(filetypes=files, title=f'Save {len(self.scan.images)} images as document(s)', defaultextension='.pdf')
        tp = E_OutputType.OT_PNG if pfname_out.lower().endswith('png') else E_OutputType.OT_PDF
        success = 'Failure to save' if self.scan.save_images(pfname_out, self.scan.images, tp=tp, enforce_A4=force_A4, seascape=seascape) else 'Successfully saved '
        self.print(f"{success} {len(self.scan.images)} images, using base pfname '{pfname_out}'.")
        self.scan.images.clear()

    def enable_stop(self, *, to_stop: bool, enable: bool, single_scan: bool):
        target = self.button_scan_fb if single_scan else self.button_scan_adf  # type: tk.Button
        icon_base = self.icon_single if single_scan else self.icon_multi  # type: tk.PhotoImage
        icon = self.icon_stop if to_stop else icon_base
        target.config(state='normal')
        target.configure(image=icon)
        target.photo = icon
        if enable:
            target.config(state='normal')
        else:
            target.config(state='disabled')

    def enable_gui(self, enable: bool):
        elts = [self.check_seascape, self.check_A4, self.button_scan_fb, self.button_scan_adf, self.button_save]
        for widget in elts:
            if enable:
                widget.config(state='normal')
            else:
                widget.config(state='disabled')

    def build_gui(self):
        # > Main Window. ---------------------------------------------
        self.root = tk.Tk()
        self.root.title("Scan")
        self.root.geometry('640x480')
        self.icon_logo = tk.PhotoImage(file=str(pfname_png_single))
        self.icon_single = tk.PhotoImage(file=str(pfname_png_single))
        self.icon_multi = tk.PhotoImage(file=str(pfname_png_multi))
        self.icon_disk = tk.PhotoImage(file=str(pfname_png_disk))
        self.icon_stop = tk.PhotoImage(file=str(pfname_png_stop))
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

        self.var_check_seascape = tk.IntVar()
        self.check_seascape = tk.Checkbutton(self.frame, anchor=tk.W, text='Seascape', variable=self.var_check_seascape, command=lambda: self.set_png(bool(self.var_check_seascape.get())))
        self.check_seascape.grid(row=1, column=0, sticky='ew')
        Hovertip(self.check_seascape, 'Normally files will be saved landscape (long edge is vertical). Check this to get seascape.')

        self.var_check_A4 = tk.IntVar()
        self.check_A4 = tk.Checkbutton(self.frame, anchor=tk.W, text='Force A4', variable=self.var_check_A4, command=lambda: self.set_force_A4(bool(self.var_check_A4.get())))
        self.check_A4.grid(row=1, column=1, sticky='ew')
        Hovertip(self.check_A4, 'If checked A4 image size will be enforced. This usually is unnecessary.')

        self.ta_log = tk.Text(self.frame, height=10, width=self.width_column, state='normal', wrap=tk.WORD)
        self.ta_log.grid(row=2, column=0, columnspan=2, sticky='ewns')
        #self.ta_log.insert('1.0', 'Initializing. Please wait.')
        self.print('Initializing. Please wait.')

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
    if print(tk.Tcl().eval('puts $tcl_platform(threaded)')) == '0':
        _log.warning("Local TCL installation (a dependency of tkinter, the GUI package) is non-threaded. However, "+
                     "'threaded' is needed for this UI. The command line tool 'scan.py' should still work though.")
    else:
        ScanGui()
    print("Done.")
