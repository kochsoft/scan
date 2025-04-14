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
"""
import os
import sys
import logging
import argparse
from enum import Enum
from pathlib import Path
from argparse import RawTextHelpFormatter
from typing import Optional, List, Dict, Tuple, Callable
import sane
import _sane
from PIL.Image import Image

# > config.sys. ------------------------------------------------------
# Default values for some config parameters. Adjust to your own needs.
defaults = {
    # Target device identifier. Use --list to get options. 'dev' keys are the first entries in each device tuple. E.g., 'v4l:/dev/video2'.
    'code': 'airscan:e0:EPSON ET-4850 Series',
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


class Scan:
    """Main class for the command line script of this project."""
    data_init = None  # type: Optional[Tuple[int,int,int,int]]
    data_devices_info = list()  # type: List[Tuple[str,str,str,str]]
    data_devices = dict()  # type: Dict[str, sane.SaneDev]

    @staticmethod
    def init_static():
        if Scan.data_init is None:
            Scan.data_init = sane.init()
            Scan.data_devices_info = sane.get_devices()

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
            device.close()
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
        self.enforce_A4 = arguments.a4
        self.code_hint = arguments.dev
        self.code = Scan.complete_code_hint(self.code_hint) if self.code_hint else None
        self.images = list()  # type: List[Image]

        if __name__ == '__main__':
            scan_tp = E_ScanType.ST_MULTI_ADF if arguments.multi else E_ScanType.ST_SINGLE_FLATBED
            Scan.init_device(self.code)
            self.scan(scan_tp)
            if self.images and arguments.pfname_out:
                self.print(f"Attempting to write {len(self.images)} images to file: '{arguments.pfname_out}'.")
                self.save_images(arguments.pfname_out, self.images, tp=self.format_output, enforce_A4=self.enforce_A4)
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
    def convert_to_A4(im_input: Image) -> Optional[Image]:
        """:param im_input: Input Image.
        :returns a new image that has been up-scaled to match A4 format.
        Note: Google tells me, DIN A4 is 210 mm x 297 mm (8.27 in x 11.69 in)."""
        # https://stackoverflow.com/questions/27271138/python-pil-pillow-pad-image-to-desired-size-eg-a4
        if 'dpi' not in im_input.info:
            im_input.info['dpi'] = defaults['dpi'], defaults['dpi']
        res_xy_input = im_input.info['dpi']
        dim_A4_px = int(res_xy_input[0] * 8.27), int(res_xy_input[1] * 11.69)
        im_out = im_input.copy().resize(dim_A4_px)
        im_out = im_out.resize(dim_A4_px)
        # a4im.paste(im, im.getbbox())
        return im_out

    @staticmethod
    def save_images(pfname: str, images: List[Image], *, tp: E_OutputType = E_OutputType.OT_PDF, enforce_A4: bool = False) -> int:
        if not images:
            _log.warning(f"Failure to write target file '{pfname}': Given image list is empty.")
            return 1
        if enforce_A4:
            images_A4 = list()  # type: List[Image]
            for img in images:
                images_A4.append(Scan.convert_to_A4(img))
            images = images_A4
        if len(images) > 1:
            images[0].save(pfname, tp.to_format(), dpi=(defaults['dpi'],defaults['dpi']), save_all=True, append_images=images[1:])
        else:
            images[0].save(pfname, tp.to_format(), dpi=(defaults['dpi'],defaults['dpi']))
        return 0

    def scan_adf(self, images: Optional[List[Image]] = None) -> List[Image]:
        """Perform an ADF (Automatic Document Feeder) multi-scan and write temporary png graphics."""
        if images is None:
            images = self.images
        device = self.device
        if not device:
            _log.warning(f"Device '{self.code}' not available.")
            return images
        device.source = "ADF"
        for image in device.multi_scan():
            images.append(image.copy())
        return images

    def scan_flatbed(self, images: Optional[List[Image]] = None) -> List[Image]:
        if images is None:
            images = self.images
        device = self.device
        if not device:
            _log.warning(f"Device '{self.code}' not available.")
            return images
        device.source = "Flatbed"
        try:
            image = device.scan()
            images.append(image)
        except _sane.error as err:
            print(f"Failure to scan from device '{device}': {err}")
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
$ python3 {Path(sys.argv[0]).name}"""
        parser = argparse.ArgumentParser(prog='scan.py', description=desc, epilog=epilog, formatter_class=RawTextHelpFormatter)
        parser.add_argument('--list', action='store_true', help="Identify all available devices and print the list.")
        parser.add_argument('--dev', type=str, help="At least part of a device name. From known devices will use the "+\
                            f"first one that fits. If none is given, default '{defaults['code']}' will be used.", default=defaults['code'])
        parser.add_argument('--png', action='store_true', help='Produce a set of png graphics rather than a comprehensive pdf file.')
        parser.add_argument('--a4', action='store_true', help="Enforce A4 format.")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--scan', action='store_true', help='Do a single flatbed scan.')
        #group.add_argument('--scans', action='store_true', help='Do multiple single flatbed scans.')
        group.add_argument('--multi', action='store_true', help='Do an Automatic Document Feeder (ADF) scan.')
        parser.add_argument('pfname_out', nargs='?', type=str, help="Target pfname for scanner output.", default=defaults['pfname_out'])
        parsed = parser.parse_args(args)
        return parsed


if __name__ == '__main__':
    scanner = Scan()
    scanner.close_all()
    print("Done.")
