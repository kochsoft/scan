#!/usr/bin/python
"""
This is a tkinter user interface for the command line tool scan.py.

Markus-Hermann Koch, https://github.com/kochsoft, 13th April 2025.

Literature:
===========
[1] Background threads talking to tkinter thread via events.
    https://stackoverflow.com/questions/64287940/update-tkinter-gui-from-a-separate-thread-running-a-command
[2] About threads and passing arguments.
    https://nitratine.net/blog/post/python-threading-basics/
[3] Displaying a PIL image in a label.
    https://python-forum.io/thread-38512.html
    https://www.activestate.com/resources/quick-reads/how-to-add-images-in-tkinter/
"""

import time
import tkinter as tk
import tkinter.filedialog
from tkinter import ttk
from threading import Thread
from idlelib.tooltip import Hovertip

import PIL.Image
from PIL import Image, ImageTk

from scan import *


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()


pfname_script = Path(__file__)

pfname_png_logo = Path(pfname_script.parent, 'icons/logo.png')
pfname_png_single = Path(pfname_script.parent, 'icons/single_scan.png')
pfname_png_multi = Path(pfname_script.parent, 'icons/multi_scan.png')
pfname_png_disk = Path(pfname_script.parent, 'icons/disk.png')
pfname_png_stop = Path(pfname_script.parent, 'icons/stop.png')
pfname_png_empty = Path(pfname_script.parent, 'icons/empty.png')
pfname_png_up_image = Path(pfname_script.parent, 'icons/up_image.png')
pfname_png_dn_image = Path(pfname_script.parent, 'icons/dn_image.png')
pfname_png_delete = Path(pfname_script.parent, 'icons/delete.png')

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
        self.tabControl =  None  # type: Optional[ttk.Notebook]
        self.tab1 = None  # type: Optional[tk.Frame]
        self.tab2 = None  # type: Optional[tk.Frame]

        self.icon_logo = None  # type: Optional[tk.PhotoImage]
        self.icon_single = None  # type: Optional[tk.PhotoImage]
        self.icon_multi = None  # type: Optional[tk.PhotoImage]
        self.icon_disk = None  # type: Optional[tk.PhotoImage]
        self.icon_stop = None  # type: Optional[tk.PhotoImage]
        self.icon_empty = None  # type: Optional[ImageTk.PhotoImage]
        self.icon_up_image = None  # type: Optional[tk.PhotoImage]
        self.icon_dn_image = None  # type: Optional[tk.PhotoImage]
        self.icon_delete = None  # type: Optional[tk.PhotoImage]

        self.var_combo_device = None  # type: Optional[tk.StringVar]
        self.combo_device = None  # type: Optional[ttk.Combobox]
        self.var_check_landscape = None  # type: Optional[tk.IntVar]
        self.check_landscape = None  # type: Optional[tk.Checkbutton]
        self.var_combo_A4 = None  # type: Optional[tk.StringVar]
        self.combo_A4 = None  # type: Optional[ttk.Combobox]

        self.ta_log = None  # type: Optional[tk.Text]

        self.button_scan_adf = None  # type: Optional[tk.Button]
        self.button_scan_fb = None  # type: Optional[tk.Button]
        self.button_save = None  # type: Optional[tk.Button]
        self.label_pages = None  # type: Optional[tk.Label]
        self.label_pages2 = None  # type: Optional[tk.Label]

        self.image_empty = None  # type: Optional[Image]
        self.image_preview = None  # type: Optional[Image]
        self.photo_preview = None  # type: Optional[ImageTk.PhotoImage]
        self.label_preview = None  # type: Optional[tk.Label]
        self.var_combo_index_preview = None  # type: Optional[tk.StringVar]
        self.combo_index_preview = None  # type: Optional[ttk.Combobox]
        self.button_up_image = None  # type: Optional[tk.Button]
        self.button_dn_image = None  # type: Optional[tk.Button]
        self.button_delete_image = None  # type: Optional[tk.Button]

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

    def ask_ok(self, msg, title: str = 'Acceptable?', icon: str=tkinter.messagebox.WARNING) -> bool:
        """Open a dialog asking for ok or cancel.
        :returns True if and only if Ok was selected. False else."""
        decision = tkinter.messagebox.Message(self.root, message=msg, title=title, icon=icon, type=tkinter.messagebox.OKCANCEL).show()
        return decision == tkinter.messagebox.OK

    @property
    def label_pages_number(self) -> int:
        """Getter for the number that is displayed in self.label_pages_number."""
        if not self.label_pages:
            return 0
        text = self.label_pages.cget('text')
        numbers = re.findall('([0-9]+)', text)
        return int(numbers[-1]) if numbers else 0

    @label_pages_number.setter
    def label_pages_number(self, val: int):
        """Setter for the number that is displayed in self.label_pages_number."""
        if val < 0:
            val = 0
        if self.label_pages:
            text = re.sub('[0-9]+', str(val), str(self.label_pages.cget('text')))
            self.label_pages.config(text=text)
        if self.label_pages2:
            text = re.sub('[0-9]+', str(val), str(self.label_pages2.cget('text')))
            self.label_pages2.config(text=text)

    @property
    def status_A4(self) -> E_Status_A4:
        val = self.combo_A4.current()
        try:
            return E_Status_A4(val)
        except ValueError:
            return E_Status_A4.SA_NONE

    def update_preview_image(self, image: Optional[Image] = None):
        is_empty = False
        if image is None:
            try:
                val = int(self.var_combo_index_preview.get())
                image = self.scan.images[val].copy()
            except (AttributeError, IndexError, ValueError):
                image = self.image_empty.copy()
                is_empty = True
        if not is_empty:
            need_A4 = self.status_A4
            if need_A4 != E_Status_A4.SA_NONE:
                image = Scan.convert_to_A4(image, stretch_content=(need_A4==E_Status_A4.SA_STRETCH))
            if bool(self.var_check_landscape.get()):
                image = image.rotate(90, expand=True)
        sz_widget = self.label_preview.winfo_width(), self.label_preview.winfo_height()
        sz_image = image.size
        if sz_widget[1] > 1 and sz_image[1] > 1:
            if is_empty:
                sz_image_new = sz_widget
            else:
                factor = 1.
                aspect_widget = sz_widget[0] / sz_widget[1]
                aspect_image = sz_image[0]  /  sz_image[1]
                if aspect_widget > aspect_image:
                    factor = sz_widget[1] / sz_image[1]
                elif aspect_widget < aspect_image:
                    factor = sz_widget[0] / sz_image[0]
                sz_image_new = int(sz_image[0] * factor), int(sz_image[1] * factor)
            if sz_image_new[0] > 0 and sz_image_new[1] > 0:
                self.image_preview = image.resize(sz_image_new)
            else:
                self.image_preview = image
        self.photo_preview = ImageTk.PhotoImage(self.image_preview) if self.image_preview else self.icon_empty
        self.label_preview['image'] = self.photo_preview

    def handler_update_preview_image(self, event):
        self.update_preview_image()

    def show_preview(self, val: Optional[int] = None):
        def drop_image():
            self.label_preview['image'] = self.icon_empty
        n = len(self.scan.images) if self.scan else 0
        if n:
            try:
                val = int(self.combo_index_preview.get() if val is None else val)
                if val >= n:
                    val = n-1
                elif val < 0:
                    val = 0
            except ValueError:
                drop_image()
                return
            self.update_preview_image(self.scan.images[val])
        else:
            drop_image()
            return

    def update_buttons_up_dn_image(self):
        """Adjust enabled status of the up and dn buttons of the image preview tab."""
        n = len(self.scan.images) if self.scan else 0
        enable_up = False
        enable_dn = False
        try:
            val = int(self.var_combo_index_preview.get())
            if val > 0:
                enable_up = True
            if val < n-1:
                enable_dn = True
        except ValueError:
            pass
        self.button_up_image.config(state = 'normal' if enable_up else 'disabled')
        self.button_dn_image.config(state = 'normal' if enable_dn else 'disabled')

    def handler_resize_label_preview(self, event):
        self.update_preview_image()

    def handler_show_preview(self, event):
        self.update_buttons_up_dn_image()
        self.show_preview()

    def update_previews(self):
        """Parses the images list and the preview combobox and updates the preview tab accordingly."""
        n = len(self.scan.images) if self.scan else 0
        elts = (self.label_preview, self.combo_index_preview, self.button_delete_image, self.button_up_image, self.button_dn_image)
        for elt in elts:
            elt.config(state='disabled' if (n==0) else 'normal')
        if not n:
            empty = '<empty>'
            self.combo_index_preview['values'] = (empty,)
            self.var_combo_index_preview.set(empty)
        else:
            val = self.var_combo_index_preview.get()
            tpl = tuple([str(j) for j in range(n)])
            self.combo_index_preview['values'] = tpl
            if val not in tpl:
                self.var_combo_index_preview.set(tpl[-1])
            if self.var_combo_index_preview.get() == tpl[0]:
                self.button_up_image.config(state='disabled')
            if self.var_combo_index_preview.get() == tpl[-1]:
                self.button_dn_image.config(state='disabled')
        if self.thread_scan and self.thread_scan.is_alive():
            self.button_delete_image.config(state='disabled')
        self.show_preview()

    @staticmethod
    def t_wait_and_bind_events(ui):
        """Threaded function that will sleep 0.5 seconds (until all GUI objects are defined), and then add
        all local event bindings for later self.root.event_generate('..', when='tail', [state=]) commands
        that in turn will trigger the event handlers registered below in self.build_GUI."""
        time.sleep(0.5)
        # _log.info("Initializing root bind.")
        ui.root.bind_all('<<init_complete>>', ui.handler_init)
        ui.root.bind_all('<<scan_complete>>', ui.handler_scan)
        ui.root.bind_all('<<scan_complete_single_multi>>', ui.handler_scan_single_multi)

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
        text_scan = f"\n{self.scan}" if self.scan else ''
        self.print(f"Initialization complete. {len(Scan.data_devices_info)} devices have been identified.{text_scan}")
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

    def handler_scan_single_multi(self, event: tk.Event):
        """Very special interest. Triggered every time scan_adf completed another scan."""
        self.label_pages_number = len(self.scan.images)

    def handler_scan(self, event: tk.Event):
        self.enable_gui(True)
        self.enable_stop(to_stop=False, enable=True, single_scan=True)
        self.enable_stop(to_stop=False, enable=True, single_scan=False)
        self.label_pages_number = len(self.scan.images)
        self.update_previews()

    def cb_init(self):
        self.root.event_generate("<<init_complete>>", when='tail') #, state=123)

    def cb_scan_single_multi(self):
        self.root.event_generate("<<scan_complete_single_multi>>", when='tail')
    def cb_scan(self):
        self.root.event_generate("<<scan_complete>>", when='tail')  # , state=123)

    @staticmethod
    def get_time(frmt: str = "%y%m%d_%H%M%S", unix_time_s: Optional[int] = None) -> str:
        """:return Time string for introduction into file names."""
        unix_time_s = int(time.time()) if unix_time_s is None else int(unix_time_s)
        return time.strftime(frmt, time.localtime(unix_time_s))

    def print(self, msg: str):
        """Prepends a log message to the content of the self.ta_log logging textarea."""
        if not msg:
            return
        if self.ta_log:
            self.ta_log.insert(1.0, f"{self.get_time('%H:%M:%S')}: {msg}\n\n")
        else:
            print(msg)

    def threaded_initialize_Scan_object(self):
        """Start a new thread for filling self.scan."""
        if self.thread_init and self.thread_init.is_alive():
            self.print("Initialization already in progress. Won't start it a second time.")
            return
        def t_init_scan_object(ui):
            ui.scan = Scan(cb_print=self.print, cb_init=ui.cb_init)
        self.enable_gui(False)
        self.update_previews()
        self.thread_init = self.call_threaded(t_init_scan_object, (self,))

    def threaded_initialize_scan_action(self, tp_: E_ScanType) -> Thread:
        def t_init_scan_action(ui, tp: E_ScanType):
            code = ui.var_combo_device.get()
            if code not in Scan.data_devices:
                Scan.init_device(code)
            if tp == E_ScanType.ST_MULTI_ADF:
                ui.scan.scan_adf(code=code, cb_done=ui.cb_scan, cb_single_done=ui.cb_scan_single_multi)
            else:
                ui.scan.scan_flatbed(code=code, cb_done=ui.cb_scan)
        self.enable_gui(False)
        self.enable_stop(to_stop=True, enable=True, single_scan=(tp_ != E_ScanType.ST_MULTI_ADF))
        return self.call_threaded(t_init_scan_action, (self, tp_))

    def refresh_devices(self):
        if self.thread_init and self.thread_init.is_alive():
            self.print("Unable to refresh while initialization is still running.")
            return
        if self.thread_scan and self.thread_scan.is_alive():
            self.print("Unable to refresh while scan procedure in progress.")
            return
        if self.ask_ok('This will reset all device elements and reinitialize them.', 'Refresh all devices'):
            Scan.reset()
            self.enable_stop(to_stop=False, enable=False, single_scan=True)
            self.enable_stop(to_stop=False, enable=False, single_scan=False)
            self.thread_init = None
            self.thread_scan = None
            self.scan = None
            self.print("Reinitializing. Please wait ...")
            self.threaded_initialize_Scan_object()

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

    def scan_single(self):
        """Initialize flatbed-Scan, or cancel it, if such a thread is already running."""
        if self.thread_scan and self.thread_scan.is_alive():
            if self.ask_ok('Do you want to cancel the ongoing flatbed scan process?', 'Cancel flatbed scan'):
                self.scan.scan_stop(self.var_combo_device.get())
                self.enable_stop(to_stop=False, enable=False, single_scan=True)
        else:
            self.thread_scan = self.threaded_initialize_scan_action(E_ScanType.ST_SINGLE_FLATBED)

    def scan_multi(self):
        """Initialize ADF (Automatic Document Feeder) scan, or cancel it, if such a thread is already running."""
        if self.thread_scan and self.thread_scan.is_alive():
            if self.ask_ok('Do you want to cancel the ongoing ADF scan process?', 'Cancel ADF scan'):
                self.scan.scan_stop(self.var_combo_device.get())
                self.enable_stop(to_stop=False, enable=False, single_scan=False)
        else:
            self.thread_scan = self.threaded_initialize_scan_action(E_ScanType.ST_MULTI_ADF)

    def save(self):
        if self.verify_scan_object():
            return
        if not self.scan.images:
            self.print("No scanned images available for saving.")
            return
        landscape = bool(self.var_check_landscape.get())
        files = [('PDF', '*.pdf'), ('png', '*.png')]
        pfname_out = tk.filedialog.asksaveasfilename(filetypes=files, title=f'Save {len(self.scan.images)} images as document(s)', defaultextension='.pdf')
        if not pfname_out:
            return
        tp = E_OutputType.OT_PNG if pfname_out.lower().endswith('png') else E_OutputType.OT_PDF
        success = 'Failure to save' if self.scan.save_images(pfname_out, self.scan.images, tp=tp, enforce_A4=self.status_A4, landscape=landscape) else 'Successfully saved'
        self.print(f"{success} {len(self.scan.images)} images. Using base pfname '{pfname_out}'.")

    def up_image(self):
        j = int(self.var_combo_index_preview.get()) - 1
        self.var_combo_index_preview.set(str(j))
        self.show_preview()
        self.update_buttons_up_dn_image()

    def dn_image(self):
        j = int(self.var_combo_index_preview.get()) + 1
        self.var_combo_index_preview.set(str(j))
        self.show_preview()
        self.update_buttons_up_dn_image()

    def delete_image(self):
        """Drop an image from the images list and update the preview tab accordingly."""
        n = len(self.scan.images) if self.scan else 0
        if not n:
            return  # << Nothing to delete.
        try:
            val = int(self.var_combo_index_preview.get())
            if val < 0 or val >= n:
                return
            del self.scan.images[val]
            self.label_pages_number = n-1
        except ValueError:
            return
        self.update_previews()

    def delete_image_stack(self):
        """Gracefully drop all images."""
        n = len(self.scan.images) if self.scan else 0
        if n == 0:
            self.print("There are no images to delete.")
            return
        if self.thread_scan and self.thread_scan.is_alive():
            self.print("Will not delete image stack while scan in progress.")
            return
        if not self.ask_ok('This will delete all currently scanned images. Are you sure?', 'Delete image stack'):
            return
        self.scan.images.clear()
        self.update_previews()

    def enable_stop(self, *, to_stop: bool, enable: bool, single_scan: bool):
        """Modifies the scanning buttons. Enabling and/or flipping them to 'do you want to cancel'-mode.
        :param to_stop: If True, display a stop sign. Else the regular button icon.
        :param enable: Should the button be enabled or disabled?
        :param single_scan: Is this call concerned with the flatbed single scan or the ADF multiscan button?"""
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
        elts = [self.check_landscape, self.combo_A4, self.button_scan_fb, self.button_scan_adf, self.button_save]
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
        # [Note: 'clicking x to close' only calls .destroy() on the widget. '.quit' quits the application properly.]
        self.root.protocol('WM_DELETE_WINDOW', self.root.quit)
        self.icon_logo = tk.PhotoImage(file=str(pfname_png_single))
        self.icon_single = tk.PhotoImage(file=str(pfname_png_single))
        self.icon_multi = tk.PhotoImage(file=str(pfname_png_multi))
        self.icon_disk = tk.PhotoImage(file=str(pfname_png_disk))
        self.icon_stop = tk.PhotoImage(file=str(pfname_png_stop))
        self.image_empty = PIL.Image.open(str(pfname_png_empty))
        self.icon_empty = ImageTk.PhotoImage(self.image_empty)
        self.icon_up_image = tk.PhotoImage(file=str(pfname_png_up_image))
        self.icon_dn_image = tk.PhotoImage(file=str(pfname_png_dn_image))
        self.icon_delete = tk.PhotoImage(file=str(pfname_png_delete))
        self.root.iconphoto(True, self.icon_single)
        # < ----------------------------------------------------------
        # > Menu. ----------------------------------------------------
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)

        menu_files = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='File', menu=menu_files)
        menu_files.add_command(label='Save All ...', command=self.save)
        menu_files.add_separator()
        menu_files.add_command(label='Exit', command=self.root.quit)

        menu_tools = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Tools', menu=menu_tools)
        menu_tools.add_command(label='Delete Image Stack', command=self.delete_image_stack)
        menu_tools.add_command(label='Refresh Devices', command=self.refresh_devices)

        menu_help = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Help', menu=menu_help)
        menu_help.add_command(label='About ...', command=self.mb_about)
        # < ----------------------------------------------------------
        # > Tabs. ----------------------------------------------------
        self.tabControl = ttk.Notebook(self.root)

        self.tab1 = ttk.Frame(self.tabControl)
        self.tab1.columnconfigure(0, weight=1)
        self.tab1.columnconfigure(1, weight=1)
        # [Note: Vertical expansion shall be done around row 2, where the log textarea is.]
        self.tab1.rowconfigure(2, weight=1)
        self.tab1.pack(fill=tk.BOTH, expand=True)

        self.tab2 = ttk.Frame(self.tabControl)
        self.tab2.columnconfigure(0, weight=1)
        self.tab2.columnconfigure(1, weight=1)
        # [Note: Vertical expansion shall be done around row 0, where the large preview widget is.]
        self.tab2.rowconfigure(0, weight=1)
        self.tab2.pack(fill=tk.BOTH, expand=True)

        self.tabControl.add(self.tab1, text="Main Functions")
        self.tabControl.add(self.tab2, text="Previews")
        self.tabControl.pack(expand=1, fill=tk.BOTH)
        # < ----------------------------------------------------------
        # > Control elements tab1. -----------------------------------
        # https://www.pythontutorial.net/tkinter/tkinter-combobox/
        # [Note: The var for the combobox needs to be a persistent variable.]
        self.var_combo_device = tk.StringVar()
        self.combo_device = ttk.Combobox(self.tab1, textvariable=self.var_combo_device, width=self.width_column)
        self.combo_device.grid(row=1,column=0, columnspan=2, sticky='ew')
        self.combo_device['values'] = '<empty>',
        self.combo_device['state'] = 'readonly'
        self.combo_device.current(0)
        Hovertip(self.combo_device, 'Once initialized, select the scanning device intended for usage.')

        self.var_check_landscape = tk.IntVar()
        self.check_landscape = tk.Checkbutton(self.tab1, anchor=tk.W, text='Landscape', variable=self.var_check_landscape, command=self.update_preview_image)
        self.check_landscape.grid(row=0, column=0, sticky='ew')
        Hovertip(self.check_landscape, 'Normally files will be saved seascape (AKA portrait, i.e., long edge is vertical). Check this to get landscape mode.')

        self.var_combo_A4 = tk.StringVar()
        self.combo_A4 = ttk.Combobox(self.tab1, textvariable=self.var_combo_A4)
        self.combo_A4.grid(row=0, column=1, sticky='ew')
        self.combo_A4['values'] = 'force A4: none', 'force A4: padding', 'force A4: stretching'
        self.combo_A4['state'] = 'readonly'
        self.combo_A4.current(0)
        self.combo_A4.bind('<<ComboboxSelected>>', self.handler_update_preview_image)
        Hovertip(self.combo_A4, 'Enforce A4 format, either by stretching or by padding. This usually is unnecessary.')

        self.ta_log = tk.Text(self.tab1, height=10, width=self.width_column, state='normal', wrap=tk.WORD)
        self.ta_log.grid(row=2, column=0, columnspan=2, sticky='ewns')
        self.print('Initializing. Please wait.')

        self.button_scan_fb = tk.Button(self.tab1, image=self.icon_single, command=self.scan_single)
        self.button_scan_fb.grid(row=3, column=0, sticky='ew')
        Hovertip(self.button_scan_fb, 'Initialize a single flatbed scan.')

        self.button_scan_adf = tk.Button(self.tab1, image=self.icon_multi, command=self.scan_multi)
        self.button_scan_adf.grid(row=3, column=1, sticky='ew')
        Hovertip(self.button_scan_adf, 'Initialize a potential multi-scan from the automatic document feed.')

        self.button_save = tk.Button(self.tab1, image=self.icon_disk, command=self.save)
        self.button_save.grid(row=4, column=0, columnspan=2, sticky='ew')
        Hovertip(self.button_save, 'Save the current images list to disk.')

        self.label_pages = tk.Label(self.tab1, text='Current number of pages: 0', relief=tk.RIDGE, anchor=tk.W)
        self.label_pages.grid(row=5, column=0, columnspan=2, sticky='ew')
        Hovertip(self.label_pages, 'If a document were to be saved now it should receive this many pages.')
        # < ----------------------------------------------------------
        # > Control elements tab2. -----------------------------------
        self.label_preview = tk.Label(self.tab2, relief=tk.RIDGE, anchor=tk.W)
        self.label_preview['image'] = self.icon_empty
        self.label_preview.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.label_preview.bind('<Configure>', self.handler_resize_label_preview)

        self.var_combo_index_preview = tk.StringVar()
        self.combo_index_preview = ttk.Combobox(self.tab2, textvariable=self.var_combo_index_preview)
        self.combo_index_preview.grid(row=1,column=0, sticky='ewn')
        self.combo_index_preview['values'] = '<empty>',
        self.combo_index_preview['state'] = 'readonly'
        self.combo_index_preview.current(0)
        self.combo_index_preview.bind('<<ComboboxSelected>>', self.handler_show_preview)
        Hovertip(self.combo_index_preview, 'Select the image index to review the respective scan.')

        self.button_up_image = tk.Button(self.tab2, image=self.icon_up_image, command=self.up_image)
        self.button_up_image.grid(row=2, column=0, sticky='ew')

        self.button_dn_image = tk.Button(self.tab2, image=self.icon_dn_image, command=self.dn_image)
        self.button_dn_image.grid(row=3, column=0, sticky='ew')

        self.button_delete_image = tk.Button(self.tab2, image=self.icon_delete, command=self.delete_image)
        self.button_delete_image.grid(row=1, column=1, rowspan=3, sticky='nsew')
        Hovertip(self.button_delete_image, 'Delete the currently visible image.')

        self.label_pages2 = tk.Label(self.tab2, text='Current number of pages: 0', relief=tk.RIDGE, anchor=tk.W)
        self.label_pages2.grid(row=4, column=0, columnspan=2, sticky='ew')
        Hovertip(self.label_pages2, 'If a document were to be saved now it should receive this many pages.')

        # < ----------------------------------------------------------

if __name__ == '__main__':
    if print(tk.Tcl().eval('puts $tcl_platform(threaded)')) == '0':
        _log.warning("Local TCL installation (a dependency of tkinter, the GUI package) is non-threaded. However, "+
                     "'threaded' is needed for this UI. The command line tool 'scan.py' should still work though.")
    else:
        ScanGui()
    Scan.close_all()
    sane.exit()
    print("\nDone.")
