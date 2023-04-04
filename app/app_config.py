from rich.box import HEAVY, HEAVY_EDGE, SQUARE
from rich.style import StyleType, Style


KEY_EXIT = "x"  # exit the application
KEY_VERS = "v"  # print the app version
KEY_PORT = "p"  # set the serial port
KEY_BAUD = "b"  # set the serial baud rate
KEY_RDFS = "r"  # read from the flash storage
KEY_RDRM = "m"  # read from ram memory
KEY_WRRM = "w"  # write to ram memory
KEY_UPLD = "u"  # upload application to flash
KEY_ERFS = "e"  # erase the flash storage
KEY_CONN = "c"  # connect to the device
KEY_DCON = "d"  # disconnect from the device
KEY_FILE = "f"  # set the file path
KEY_CNCL = "c"  # cancel current mode
KEY_RDPG = "n"  # read flash pages
KEY_OPTB = "o"  # configure the option bytes


MIN_UPLOAD_FILE_LEN = 32  # 32b min file upload size
MAX_UPLOAD_FILE_LEN = 8000000  # 8MB max file upload size


# Style configuration

menu_template = f"""
[green]Actions[/green]
        
"""

panel_format = {
    "box": SQUARE,
    "expand": True,
    "title_align": "left",
    "border_style": Style(color="yellow"),
}


clear_table_format = {
    "show_edge": False,
    "show_header": False,
    "expand": True,
    "box": None,
    "padding": (0, 1),
}
