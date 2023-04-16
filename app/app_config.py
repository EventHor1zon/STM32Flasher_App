from rich.box import HEAVY, HEAVY_EDGE, SQUARE
from rich.style import StyleType, Style


CSS_PATH = "./css/stmapp_css.css"

ENABLE_BLINK_EFFECT = True
DEFAULT_CONNECTION_BAUD = 9600

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


# build the keypress menu items
menu_items = [
    {
        "key": KEY_PORT,
        "description": "Set Port",
        "state": STATE_IDLE_DISCONNECTED,
    },
    {
        "key": KEY_BAUD,
        "description": "Set Baud",
        "state": STATE_IDLE_DISCONNECTED,
    },
    {
        "key": KEY_CONN,
        "description": "Connect",
        "state": STATE_IDLE_DISCONNECTED,
        "action": self.handle_connect_keypress,
    },
    {
        "key": KEY_EXIT,
        "description": "Exit",
        "state": STATE_ANY,
        "action": self.handle_exit_keypress,
    },
    {
        "key": KEY_CNCL,
        "description": "Cancel",
        "state": STATE_ANY,
        "action": self.handle_cancel_keypress,
    },
    {
        "key": KEY_VERS,
        "description": "Print Version",
        "state": STATE_ANY,
        "action": self.handle_vers_keypress,
    },
    {
        "key": KEY_FILE,
        "description": "set file path",
        "action": self.handle_filepath_keypress,
        "state": STATE_READ_MEM,
    },
    {
        "key": "o",
        "description": "Configure offset",
        "action": self.handle_offset_keypress,
        "state": STATE_READ_MEM,
    },
    {
        "key": "l",
        "description": "Read length",
        "action": self.handle_length_keypress,
        "state": STATE_READ_MEM,
    },
    {
        "key": KEY_RDFS,
        "description": "Read memory",
        "action": None,
        "state": STATE_READ_MEM,
    },
    {
        "key": KEY_FILE,
        "description": "set file path",
        "action": None,
        "state": STATE_UPLOAD_APP,
    },
    {
        "key": "o",
        "description": "Configure offset",
        "action": None,
        "state": STATE_UPLOAD_APP,
    },
    {
        "key": "w",
        "description": "Write file contents to flash",
        "action": None,
        "state": STATE_UPLOAD_APP,
    },
    {
        "key": KEY_RDRM,
        "description": "Read RAM to file",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": KEY_WRRM,
        "description": "Write file data to ram",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": KEY_UPLD,
        "description": "Upload application to flash",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": KEY_ERFS,
        "description": "Erase all flash",
        "state": STATE_IDLE_CONNECTED,
        "action": self.handle_erase_keypress,
    },
    {
        "key": KEY_RDFS,
        "description": "Read flash memory",
        "state": STATE_IDLE_CONNECTED,
        "action": self.handle_readflash_keypress,
    },
    {
        "key": KEY_DCON,
        "description": "Disconnect from device",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": KEY_RDPG,
        "description": "Read flash pages",
        "state": STATE_IDLE_CONNECTED,
        "action": self.handle_readpages_keypress,
    },
    {
        "key": KEY_OPTB,
        "description": "Configure Option Bytes",
        "action": self.handle_option_bytes,
        "state": STATE_IDLE_CONNECTED,
    },
]
