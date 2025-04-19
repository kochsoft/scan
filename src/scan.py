#!/usr/bin/python3
"""
User-friendly scanner tool for the Epson ET 4850. Aiming at
+ Just scanning the current page into pdf or png.
+ Concatenating more pages, if so desired.
+ Alternatively, scanning a set of pages through the automatic feed into a multipage project.
And nothing more! Please.

Why? All this can be done using xsane. However, holy mother of god!, the user interface of that time-honored thing!

Markus-Hermann Koch, https://github.com/kochsoft/scan, April 12th 2025.

Literature:
===========
[1] Main documentation of the python sane API
    https://python-sane.readthedocs.io/en/latest/
[2] Multi Scan example. Most notable line: device.source = 'ADF' to enable automatic document feeder.
    https://github.com/python-pillow/Sane/issues/23
[3] Make even multiple PIL images into one PDF.
    https://stackoverflow.com/questions/27327513/create-pdf-from-a-list-of-images
[4] Save an Image as A4 in size.
    https://stackoverflow.com/questions/27271138/python-pil-pillow-pad-image-to-desired-size-eg-a4
[5] https://github.com/alexpevzner/sane-airscan
    https://archlinux.org/packages/extra/x86_64/sane-airscan/
    Airscan driver. On my own system (Epson ET-4850) this enabled the use of ADF (Automatic Document Feed) scanning.
"""
import re
import os
import sys
import logging
import argparse
from enum import Enum
from pathlib import Path
from argparse import RawTextHelpFormatter
from typing import Optional, Union, List, Dict, Tuple, Callable, Iterable, Any
from numbers import Number
from math import log, floor, ceil, sqrt

import PIL.Image
import sane
import _sane
from PIL.Image import Image

# > config.sys. ------------------------------------------------------
# Default values for some config parameters. Adjust to your own needs.
defaults = {
    # Target device identifier. Use --list to get options. 'dev' keys are the first entries in each device tuple. E.g., 'v4l:/dev/video2'.
    'code': 'airscan', #'airscan:e0:EPSON ET-4850 Series',
    # Dots per inch.
    'dpi': 72,
    'pfname_out': os.path.expanduser(r'~/scan.pdf')
}
# < ------------------------------------------------------------------


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()

regexp_invalid_pfname_chars = r'[/\\?%*:|"<> !]'

def cb_dummy():
    """Empty function, when a callback should do nothing."""
    pass

class E_ScanType(Enum):
    ST_UNSPECIFIED = 0
    ST_SINGLE_FLATBED = 1
    ST_MULTI_FLATBED = 2
    ST_MULTI_ADF = 3


class E_OutputType(Enum):
    OT_UNSPECIFIED = 0
    OT_PDF = 1
    OT_PNG = 2

    def to_format(self) -> Optional[str]:
        """:returns a string that can be used as 'format' parameter in a Pil.Image.Image object."""
        # https://pillow.readthedocs.io/en/stable/reference/Image.html
        if self  == E_OutputType.OT_PDF:
            return 'PDF'
        elif self == E_OutputType.OT_PNG:
            return 'PNG'
        return None


class E_Status_A4(Enum):
    """How to convert an image into A4"""
    SA_NONE = 0
    SA_PAD = 1
    SA_STRETCH = 2

    @staticmethod
    def from_str(val: str):
        val = val.lower()
        if val == 'stretch':
            return E_Status_A4.SA_STRETCH
        elif val == 'pad':
            return E_Status_A4.SA_PAD
        else:
            if val != '' and val != 'none':
                _log.warning(f"Invalid A4 status code '{val}' encountered. Ignoring it.")
            return E_Status_A4.SA_NONE

class Scan:
    """Main class for the command line script of this project."""
    data_request_stop = False  # type: bool
    data_init = None  # type: Optional[Tuple[int,int,int,int]]
    data_devices_info = list()  # type: List[Tuple[str,str,str,str]]
    data_devices = dict()  # type: Dict[str, sane.SaneDev]

    @staticmethod
    def init_static():
        if Scan.data_init is None:
            Scan.data_init = sane.init()
            Scan.data_devices_info = sane.get_devices()

    @staticmethod
    def reset():
        """Closes all devices and resets all global properties."""
        Scan.close_all()
        Scan.data_init = None
        Scan.data_devices_info = list()
        Scan.data_devices = dict()

    @staticmethod
    def complete_code_hint(code_hint: Optional[str] = None) -> Optional[str]:
        """:returns a proper code for sane.open. Or None, in case of failure."""
        if code_hint is None:
            code_hint = defaults['code']
        for code_dev in Scan.data_devices_info:
            code = code_dev[0].lower()
            if code_hint.lower() == code:
                return code_dev[0]
        for code_dev in Scan.data_devices_info:
            code = code_dev[0].lower()
            if code_hint.lower() in code:
                return code_dev[0]
        return None

    @staticmethod
    def get_available_codes() -> List[str]:
        res = list()  # type: List[str]
        for code_list in Scan.data_devices_info:
            res.append(code_list[0])
        return res

    @staticmethod
    def available_codes2str(line_prefix: str = '') -> str:
        """:returns human-readable string representation of currently available device code tuples."""
        if not Scan.data_devices_info:
            return f'{line_prefix}<empty>'
        res = ""
        for codes in Scan.data_devices_info:
            res += f"{line_prefix}{codes[2]}: {codes[0]}\n"
        return res[:-1]

    @staticmethod
    def init_device(code_hint: str) -> int:
        code = Scan.complete_code_hint(code_hint)
        if code is None:
            _log.warning(f"Failure to obtain code from code hint '{code_hint}'. Available codes: {Scan.get_available_codes()}")
            return 1
        if code in Scan.data_devices:
            Scan.data_devices[code].close()
        try:
            Scan.data_devices[code] = sane.open(code)
        except _sane.error:
            _log.warning(f"Failure to open device from code '{code}'. Available codes: {Scan.get_available_codes()}")
            return 2
        return 0

    @staticmethod
    def close_all():
        for device in Scan.data_devices.values():
            try:
                device.close()
            except _sane.error:
                pass
        Scan.data_devices = dict()

    def __init__(self, *, cb_print: Callable[[str], None] = print,
                 cb_init: Callable[[], None] = cb_dummy,
                 args: Optional[List[str]] = None):
        self.cb_print = cb_print  # type: Callable[[str], None]
        arguments = self.parse_arguments(args)
        self.init_static()

        if arguments.list:
            self.print(Scan.available_codes2str())
            sys.exit(0)

        self.format_output = E_OutputType.OT_PNG if arguments.png else E_OutputType.OT_PDF
        self.code_hint = arguments.dev
        self.code = Scan.complete_code_hint(self.code_hint) if self.code_hint else None
        self.images = list()  # type: List[Image]

        if __name__ == '__main__':
            scan_tp = E_ScanType.ST_MULTI_ADF if arguments.multi else E_ScanType.ST_SINGLE_FLATBED
            Scan.init_device(self.code)
            self.scan(scan_tp)
            if self.images and arguments.pfname_out:
                self.print(f"Attempting to write {len(self.images)} images to file: '{arguments.pfname_out}'.")
                self.save_images(arguments.pfname_out, self.images, dpi=arguments.dpi, tp=self.format_output,
                                 enforce_A4=E_Status_A4.from_str(arguments.a4), landscape=True if arguments.landscape else False)
            else:
                (self.print(f"Failure to scan any images."))
        else:
            cb_init()

    @property
    def device(self) -> Optional[sane.SaneDev]:
        return Scan.data_devices[self.code] if self.code in Scan.data_devices else None

    def __str__(self) -> str:
        #  (sane_ver, ver_maj, ver_min, ver_patch).
        res = f"Sane version: {'.'.join([str(j) for j in Scan.data_init])}\n"
        res += f"Known devices: \n{Scan.available_codes2str('  ')}"
        res += f"Requested device: {self.code}"
        return res

    def print(self, msg):
        """Local print function taking a callable. Intended for updating some statusbar in a GUI."""
        self.cb_print(msg)

    @staticmethod
    def dpi2tuple(dpi: Optional[Union[Number, Tuple[Number, Number]]] = None, *, min_dpi=0.01) -> Tuple[Number, Number]:
        """Converts a rather general expression into a 2-tuple of numbers >=min_dpi. Intended as (dpi_x, dpi_y)."""
        if not dpi:
            dpi = defaults['dpi']
        if isinstance(dpi, str):
            dpi = re.sub(r'[)\]]\s*$', '', re.sub(r'^\s*[[(]','',dpi))
            dpi = tuple(float(d) for d in dpi.split(',')) if ',' in dpi else float(dpi)
        if isinstance(dpi, Number):
            dpi = dpi, dpi
        if isinstance(dpi, Iterable) and not isinstance(dpi, tuple):
            dpi = tuple(dpi)
        return max(min_dpi, dpi[0]), max(min_dpi, dpi[1])

    @staticmethod
    def convert_to_A4(im_input: Image, *, dpi: Optional[Any] = None, stretch_content: bool = False,
                      bg_color: Tuple[int,int,int] = (255,255,255)) -> Optional[Image]:
        """:param im_input: Input Image.
        :param dpi: dpi value. If not given the images intrinsic value will be used. If not present, falling back to default.
        :param stretch_content: If True the image will be stretched to fill the entire A4 canvas. Else it will merely be pasted.
        :param bg_color: Only relevant if stretch_content == False. Background color for padded area as RGB in {0,255}^3.
        :returns a new image that has been up-scaled to match A4 format.
        Note: Google tells me, DIN A4 is 210 mm x 297 mm (8.27 in x 11.69 in)."""
        # https://stackoverflow.com/questions/27271138/python-pil-pillow-pad-image-to-desired-size-eg-a4
        if ('dpi' not in im_input.info) or (dpi is not None):
            im_input.info['dpi'] = Scan.dpi2tuple(defaults['dpi'] if dpi is None else dpi)
        width_px, height_px = im_input.size
        dpi_x, dpi_y = im_input.info['dpi']
        width_inch = width_px / dpi_x
        height_inch = height_px / dpi_y
        im_out = im_input.copy()
        if stretch_content:
            # [Portrait DIN A4 aspect ratio is 1/sqrt(2).]
            factor_x = 8.27 / width_inch
            factor_y = 11.69 / height_inch
            dim_A4_px = round(width_px * factor_x), round(height_px * factor_y)
            im_out = im_out.resize(dim_A4_px)
        else:
            # [Note: The width of a DINA4 in ich (8.27) * sqrt(2) equals the height of 11.69 inches.]
            width_is_dominant = (width_px * sqrt(2) >= height_px)
            factor_x = 1.0
            factor_y = 1.0
            if width_is_dominant:
                factor = 8.27 / width_inch
                dim_A4_px_content = round(width_px * factor), round(height_px * factor)
                # Now there will be a blank bar below.
                factor_y = 11.69 * dpi_y / dim_A4_px_content[1]
            else:
                factor = 11.69 / height_inch
                dim_A4_px_content = round(width_px * factor), round(height_px * factor)
                # Now there will be a blank bar to the right.
                factor_x = 8.27 * dpi_x / dim_A4_px_content[0]
            im_out = im_out.resize(dim_A4_px_content)
            dim_A4_px = round(factor_x * dim_A4_px_content[0]), round(factor_y * dim_A4_px_content[1])
            a4im = PIL.Image.new('RGB', dim_A4_px, bg_color)
            a4im.paste(im_out, im_out.getbbox())  # Not centered, top-left corner
            im_out = a4im
        return im_out

    @staticmethod
    def save_images(pfname: str, images: List[Image], *, tp: E_OutputType = E_OutputType.OT_PDF,
                    dpi: Optional[Union[Number, Tuple[Number, Number]]] = None, enforce_A4: E_Status_A4 = E_Status_A4.SA_NONE, landscape = False) -> int:
        if not images:
            _log.warning(f"Failure to write target file '{pfname}': Given image list is empty.")
            return 1
        if not pfname:
            _log.warning(f"Failure to write {len(images)} to target file with empty fname.")
            return 2
        dpi = Scan.dpi2tuple(dpi)
        if enforce_A4 != E_Status_A4.SA_NONE:
            images_A4 = list()  # type: List[Image]
            for img in images:
                images_A4.append(Scan.convert_to_A4(img, dpi=dpi, stretch_content=(enforce_A4==E_Status_A4.SA_STRETCH)))
            images = images_A4
        if landscape:
            images_landscape = list()  # type: List[Image]
            for img in images:
                images_landscape.append(img.rotate(90, expand=True))
            images = images_landscape
        if len(images) > 1:
            if tp == E_OutputType.OT_PDF:
                images[0].save(pfname, tp.to_format(), dpi=dpi, save_all=True, append_images=images[1:])
            else:
                # [Note: PNG does not support multi-page documents. Write enumerated individual files instead.]
                n_digits = floor(log(len(images),10)) + 1
                for j in range(len(images)):
                    pname = Path(pfname).parent
                    fname = Path(pfname).name
                    pfn = Path(pname).joinpath(f'{j:0{n_digits}d}_{fname}')
                    images[j].save(pfn, tp.to_format(), dpi=dpi)
        else:
            images[0].save(pfname, tp.to_format(), dpi=dpi)
        return 0

    def scan_stop(self, code: Optional[str] = None):
        if code is None:
            code = self.code
        device = Scan.data_devices[code] if code in Scan.data_devices else None  # type: Optional[sane.SaneDev]
        if device:
            self.print(f"Requesting stop of device '{code}'.")
            Scan.data_request_stop = True
        else:
            self.print(f"Canceling scan from device '{code}' is unnecessary. Device does not seem to exist.")

    def scan_adf(self, code: Optional[str] = None, images: Optional[List[Image]] = None, *, cb_done: Optional[callable] = None) -> List[Image]:
        """Perform an ADF (Automatic Document Feeder) multi-scan and write temporary png graphics."""
        if code is None:
            code = self.code
        device = Scan.data_devices[code] if code in Scan.data_devices else None  # type: Optional[sane.SaneDev]
        if images is None:
            images = self.images
        if not device:
            self.print(f"Device '{code}' not available.")
            return images
        device.source = "ADF"
        n0 = len(self.images)
        Scan.data_request_stop = False
        while True:
            if Scan.data_request_stop:
                self.print("Stop request received. Breaking acquisition loop.")
                break
            try:
                image = device.scan()
                images.append(image.copy())
            except Exception as e:
                if str(e) == 'Document feeder out of documents':
                    self.print('Document feeder is empty.')
                else:
                    self.print(f"Stopping ADF processing: {str(e)}")
                break
        device.close()
        if code in Scan.data_devices:
            del Scan.data_devices[code]
        n1 = len(self.images) - n0
        self.print(f"Scanned {n1} new images.")
        if cb_done:
            cb_done()
        return images

    def scan_flatbed(self, code: Optional[str] = None, images: Optional[List[Image]] = None, *, cb_done: Optional[callable] = None) -> List[Image]:
        if code is None:
            code = self.code
        device = Scan.data_devices[code] if code in Scan.data_devices else None  # type: Optional[sane.SaneDev]
        if images is None:
            images = self.images
        if not device:
            self.print(f"Device '{code}' not available.")
            return images
        # device.source = 'Flatbed'
        Scan.data_request_stop = False
        try:
            image = device.scan()
            if Scan.data_request_stop:
                self.print("Scan has been completed. However, stop was requested. Ignoring the image.")
            else:
                images.append(image)
        except _sane.error as err:
            print(f"Failure to scan from device '{device}': {err}")
        device.close()
        if code in Scan.data_devices:
            del Scan.data_devices[code]
        if cb_done:
            cb_done()
        return images

    def scan(self, scan_tp: E_ScanType, *, clear_images: bool = False):
        if clear_images:
            self.images.clear()
        if scan_tp in (E_ScanType.ST_SINGLE_FLATBED, E_ScanType.ST_MULTI_FLATBED):
            self.scan_flatbed()
        elif scan_tp == E_ScanType.ST_MULTI_ADF:
            self.scan_adf()
        else:
            _log.warning(f"Unsupported scan type '{scan_tp.name}' encountered.")

    @staticmethod
    def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
        if args is None:
            args = sys.argv[1:]
        desc = """Smallish UI project for offering the most common scanner functions of an Epson ET 4850 device."""
        epilog = f"""Example call:
$ python3 scan.py --list"""
        parser = argparse.ArgumentParser(prog='scan.py', description=desc, epilog=epilog, formatter_class=RawTextHelpFormatter)
        parser.add_argument('--list', action='store_true', help="Identify all available devices and print the list.")
        parser.add_argument('--dev', type=str, help="At least part of a device name. From known devices will use the "+\
                            f"first one that fits. If none is given, default '{defaults['code']}' will be used.", default=defaults['code'])
        parser.add_argument('--dpi', type=str, help=f"Either one or two dpi numbers for dpi_x and dpi_y. Default: {defaults['dpi']}", default=str(defaults['dpi']))
        parser.add_argument('--png', action='store_true', help='Produce a set of png graphics rather than a comprehensive pdf file.')
        parser.add_argument('--a4', type=str, help="Enforce A4 format. Give 'stretch' or 'pad' for stretching or merely pasting the original image content.", default='none')
        parser.add_argument('--landscape', action='store_true', help='Do a 90 degree rotation for landscape orientation (as opposed to portrait, AKA seascape).')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--scan', action='store_true', help='Do a single flatbed scan.')
        group.add_argument('--multi', action='store_true', help='Do an Automatic Document Feeder (ADF) scan.')
        parser.add_argument('pfname_out', nargs='?', type=str, help="Target pfname for scanner output.", default=defaults['pfname_out'])
        parsed = parser.parse_args(args)
        return parsed


if __name__ == '__main__':
    scanner = Scan()
    Scan.close_all()
    sane.exit()
