from enum import IntFlag

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 as __wrapper_module__
from comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 import (
    OLE_XSIZE_PIXELS, OLE_HANDLE, IEnumVARIANT, DISPPROPERTY, BSTR,
    _check_version, OLE_XPOS_PIXELS, StdPicture, OLE_YPOS_HIMETRIC,
    OLE_COLOR, DISPPARAMS, FONTITALIC, FONTNAME, OLE_YSIZE_HIMETRIC,
    OLE_YPOS_CONTAINER, OLE_XSIZE_CONTAINER, OLE_ENABLEDEFAULTBOOL,
    HRESULT, VARIANT_BOOL, StdFont, OLE_XPOS_CONTAINER,
    IFontEventsDisp, FONTSTRIKETHROUGH, Checked, FONTBOLD, _lcid,
    FONTUNDERSCORE, FONTSIZE, OLE_XSIZE_HIMETRIC, Unchecked, Color,
    Monochrome, Default, CoClass, OLE_YSIZE_CONTAINER, IPicture,
    OLE_YPOS_PIXELS, typelib_path, OLE_XPOS_HIMETRIC, IFontDisp,
    OLE_CANCELBOOL, OLE_YSIZE_PIXELS, IDispatch, COMMETHOD,
    IPictureDisp, Font, OLE_OPTEXCLUSIVE, IUnknown, VgaColor,
    DISPMETHOD, Picture, IFont, EXCEPINFO, Gray, FontEvents, Library,
    GUID, dispid
)


class OLE_TRISTATE(IntFlag):
    Unchecked = 0
    Checked = 1
    Gray = 2


class LoadPictureConstants(IntFlag):
    Default = 0
    Monochrome = 1
    VgaColor = 2
    Color = 4


__all__ = [
    'IPicture', 'OLE_XSIZE_PIXELS', 'LoadPictureConstants',
    'OLE_HANDLE', 'OLE_YPOS_PIXELS', 'typelib_path',
    'OLE_XPOS_HIMETRIC', 'IFontDisp', 'OLE_CANCELBOOL',
    'OLE_XPOS_PIXELS', 'StdPicture', 'OLE_YPOS_HIMETRIC',
    'OLE_YSIZE_PIXELS', 'IPictureDisp', 'OLE_COLOR', 'FONTITALIC',
    'FONTNAME', 'Font', 'OLE_OPTEXCLUSIVE', 'OLE_YSIZE_HIMETRIC',
    'VgaColor', 'OLE_YPOS_CONTAINER', 'OLE_XSIZE_CONTAINER',
    'OLE_ENABLEDEFAULTBOOL', 'Picture', 'IFont', 'StdFont', 'Gray',
    'IFontEventsDisp', 'FONTSTRIKETHROUGH', 'FontEvents',
    'OLE_XPOS_CONTAINER', 'Checked', 'FONTBOLD', 'Library',
    'OLE_TRISTATE', 'FONTUNDERSCORE', 'FONTSIZE',
    'OLE_XSIZE_HIMETRIC', 'Unchecked', 'Color', 'Monochrome',
    'Default', 'OLE_YSIZE_CONTAINER'
]

