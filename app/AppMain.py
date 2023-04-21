#
#   Attempt to applify STM flasher with textual's tutorial
#   Going pretty well, impressed with the appearance now
#
#   Let's think state machines...
#
#       IDLE (disconnected)  -> config port
#                            -> config baud
#                            -> connect (state = IDLE_CONNECTED)
#       IDLE (connected_state)     -> config option bytes (state = CONFIG_OPT_BYTES)
#                            -> read memory (state = READ_MEM)
#                            -> upload application (state = WRITE_MEM)
#                            -> erase flash (state = ERASE_MEM)
#

import sys
import os

## TODO: remember to make serialflash a package and import
# properly here. Fix these paths.
from ..SerialFlasher.StmDevice import STMInterface
from ..SerialFlasher.constants import STM_BOOTLOADER_MAX_BAUD, STM_BOOTLOADER_MIN_BAUD

import asyncio
from asyncio.queues import Queue, QueueEmpty, QueueFull
from time import sleep

from rich.panel import Panel
from rich.table import Table
from rich.style import Style
from rich.box import HEAVY, HEAVY_EDGE, SQUARE
from rich.console import RenderableType, Group
from rich.text import Text

from textual.app import App, ComposeResult
from textual.events import Event, Key, Focus, Blur
from textual.widgets import (
    Header,
    Static,
    TextLog,
    Input,
)

from .chip_image import ChipImage, generateFlashImage
from . import app_config as config
from .textformat import (
    SuccessMessage,
    InfoMessage,
    FailMessage,
    ErrorMessage,
    MARKUP,
    binary_colour,
)

DEBUG_MODE = False


# Application Details
APPLICATION_NAME = "StmF1 Flasher Tool"

APPLICATION_VERSION = "0.0.1"

APPLICATION_BANNER = """
░█▀▀░▀█▀░█▄█░░░█▀▀░█░░░█▀█░█▀▀░█░█░█▀▀░█▀▄
░▀▀█░░█░░█░█░░░█▀▀░█░░░█▀█░▀▀█░█▀█░█▀▀░█▀▄
░▀▀▀░░▀░░▀░▀░░░▀░░░▀▀▀░▀░▀░▀▀▀░▀░▀░▀▀▀░▀░▀
"""


# Application States
# TODO: Make this an enum?
STATE_IDLE_DISCONNECTED = 0
STATE_IDLE_CONNECTED = 1
STATE_AWAITING_INPUT = 2
STATE_ERASE_MEM = 3
STATE_READ_MEM = 4
STATE_WRITE_MEM = 5
STATE_UPLOAD_APP = 6
STATE_OPTBYTE_CONFIG = 7
STATE_INVALID = 8
STATE_ANY = 255


# build the keypress menu items
menu_items = [
    {
        "key": config.KEY_PORT,
        "description": "Set Port",
        "state": STATE_IDLE_DISCONNECTED,
    },
    {
        "key": config.KEY_BAUD,
        "description": "Set Baud",
        "state": STATE_IDLE_DISCONNECTED,
    },
    {
        "key": config.KEY_CONN,
        "description": "Connect",
        "state": STATE_IDLE_DISCONNECTED,
        "action": self.handle_connect_keypress,
    },
    {
        "key": config.KEY_EXIT,
        "description": "Exit",
        "state": STATE_ANY,
        "action": self.handle_exit_keypress,
    },
    {
        "key": config.KEY_CNCL,
        "description": "Cancel",
        "state": STATE_ANY,
        "action": self.handle_cancel_keypress,
    },
    {
        "key": config.KEY_VERS,
        "description": "Print Version",
        "state": STATE_ANY,
        "action": self.handle_vers_keypress,
    },
    {
        "key": config.KEY_FILE,
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
        "key": config.KEY_RDFS,
        "description": "Read memory",
        "action": None,
        "state": STATE_READ_MEM,
    },
    {
        "key": config.KEY_FILE,
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
        "key": config.KEY_RDRM,
        "description": "Read RAM to file",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": config.KEY_WRRM,
        "description": "Write file data to ram",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": config.KEY_UPLD,
        "description": "Upload application to flash",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": config.KEY_ERFS,
        "description": "Erase all flash",
        "state": STATE_IDLE_CONNECTED,
        "action": self.handle_erase_keypress,
    },
    {
        "key": config.KEY_RDFS,
        "description": "Read flash memory",
        "state": STATE_IDLE_CONNECTED,
        "action": self.handle_readflash_keypress,
    },
    {
        "key": config.KEY_DCON,
        "description": "Disconnect from device",
        "state": STATE_IDLE_CONNECTED,
        "action": None,
    },
    {
        "key": config.KEY_RDPG,
        "description": "Read flash pages",
        "state": STATE_IDLE_CONNECTED,
        "action": self.handle_readpages_keypress,
    },
    {
        "key": config.KEY_OPTB,
        "description": "Configure Option Bytes",
        "action": self.handle_option_bytes,
        "state": STATE_IDLE_CONNECTED,
    },
]


# Text Formatting functions
# TODO: Move these to their own file


# Application Sections
# TODO: Move these to their own file
# TODO: Make attributes configurable


class TextBox(Static):
    def __init__(
        self,
        renderable: RenderableType = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name=None,
        id=None,
        classes=None,
    ) -> None:
        super().__init__(
            renderable,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
        )


class OptBytesDisplay(Static):
    def __init__(
        self,
        renderable: RenderableType = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name=None,
        id=None,
        classes=None,
    ) -> None:
        super().__init__(
            renderable,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
        )
        self.styles.background = "black"

    def _on_focus(self, event: Focus) -> None:
        self.styles.background = "blue"
        return super()._on_focus(event)


class OptBytesRaw(Static):
    def __init__(
        self,
        renderable: RenderableType = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str = None,
        id: str = None,
        classes: str = None,
    ) -> None:
        super().__init__(
            renderable,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
        )
        self.styles.background = "black"


class StringGetter(Input):
    def __init__(
        self,
        value=None,
        placeholder: str = "",
        highlighter=None,
        password: bool = False,
        name=None,
        id=None,
        classes=None,
    ) -> None:
        super().__init__(
            value=value,
            placeholder=placeholder,
            highlighter=highlighter,
            password=password,
            name=name,
            id=id,
            classes=classes,
        )
        self.styles.background = "black"

    async def action_submit(self) -> None:
        await super().action_submit()
        self.reset_focus()
        self.value = ""


class StringPutter(TextLog):
    """!@class StringPutter
    @brief class to display text feedback from the application
    """

    def __init__(
        self,
        *,
        max_lines=None,
        min_width: int = 78,
        wrap: bool = False,
        highlight: bool = False,
        markup: bool = False,
        name=None,
        id=None,
        classes=None,
    ) -> None:
        super().__init__(
            max_lines=max_lines,
            min_width=min_width,
            wrap=wrap,
            highlight=highlight,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
        )

    def on_mount(self):
        self.write(f"Application Initialising....")
        self.write(f"{APPLICATION_NAME} v{APPLICATION_VERSION}")
        return super().on_mount()


class MainSections(Static):
    """class to display the top three columns of the app
    display and update information about the device
    and commands
    added extra init args so we can populate the widgets
    as we yield them
    """

    def __init__(
        self,
        menu: RenderableType = "",
        info: RenderableType = "",
        opts: RenderableType = "",
        renderable: RenderableType = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name=None,
        id=None,
        classes=None,
    ) -> None:
        self.menu = menu
        self.info = info
        self.opts = opts
        super().__init__(
            renderable,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
        )

    def compose(self) -> ComposeResult:
        yield TextBox(self.menu, id="menu")
        yield TextBox(self.info, id="info")
        yield OptBytesDisplay(self.opts, id="opts")


class StmApp(App):
    """StmApp - the application class for the application
    Application structure as follows:

    ```
        --------------------------------------
        [                Banner              ]
        --------------------------------------
        [   menu  ][  user info  ][  opts    ]
        [   sect  ][  dev info   ][  sect    ]
        [   quit  ][  chip img   ][          ]
        --------------------------------------
        [          Output                    ]
        [                                    ]
        --------------------------------------
        [           Input                    ]
        --------------------------------------

    ```
    Nomenclature - for sanity's sake, refer to
                   each of the 3 display sections
                   as "sections"
                 - refer to each panel within those
                    sections as a "panel"
                 - For menu section, only one panel
                (menu items) is required
                 - For Info section (middle), 3 panels are
                reuired: Connection panel/rw panel(now known as 'user' panel),
                 device panel and image panel
                - For Opts section, 2 panels are required:
                the option table and the option bytes


    """

    # Path to CSS - used mostly for layout
    # Try to use config variables for easier styling
    CSS_PATH = config.CSS_PATH

    # application state & previous state
    state = STATE_INVALID
    prev_state = STATE_INVALID

    # Device model
    stm_device = STMInterface()

    # internal state variables
    # TODO: use less of these
    #   Need - connect-opts
    #        - io opts

    connected_state = False

    # user supplied details
    # TODO: Put into a dictionary
    conn_port = ""
    conn_baud = 9600
    address = None
    length = 0
    offset = 0
    filepath = None

    # Default tables & widget definitions
    conn_table = None
    dev_table = None
    chip_image = ""
    chip = None

    state_menu_items = []
    all_menu_items = [item for item in menu_items if item["state"] == STATE_ANY]

    banner = Static(APPLICATION_BANNER, expand=True, id="banner")
    msg_log = StringPutter(max_lines=8, name="msg_log", id="msg_log")
    input_box = StringGetter(placeholder=">>>")

    def __init__(self, driver_class=None, css_path=None, watch_css: bool = False):
        # Declare a custom message queue
        self.msg_queue = Queue(10)

        # set the start app states - update here might break
        self.state = STATE_IDLE_DISCONNECTED
        self.connected_state = False

        self.build_menu_section()
        self.build_opts_section()
        self.build_info_section()

        # initialise the panel contents
        self.info_panels = MainSections(
            menu=self.menu,
            info=self.info,
            opts=self.opts,
        )

        # initialise parent class
        super().__init__(driver_class, css_path, watch_css)

    ## State mechanics

    def idle_state(self) -> int:
        """get the specific idle state from connection state

        Returns:
            int: idle state
        """
        return (
            STATE_IDLE_DISCONNECTED
            if not self.connected_state
            else STATE_IDLE_CONNECTED
        )

    def change_state(self, new_state: int) -> None:
        """change state and update contents

        Args:
            new_state (int): state to transition to
        """
        if self.state == new_state or new_state >= STATE_INVALID:
            return
        else:
            self.prev_state = self.state
            self.state = new_state
            # don't update any sections if we're just awaiting input
            # the state transition back after will update info
            if self.state != STATE_AWAITING_INPUT:
                self.update_all_sections()

    def restore_previous_state(self) -> None:
        """restore the previous state"""
        self.change_state(self.prev_state)

    def menu_items_from_state(self) -> list:
        """returns a list of menu items filtered by current state

        Returns:
            list: list of menu items
        """
        return [item for item in menu_items if item["state"] == self.state]

    ## Widgets & tables updates

    def compose(self) -> ComposeResult:
        """overwrite the default application compose method

        Returns:
            ComposeResult: the composed windows

        Yields:
            Iterator[ComposeResult]: none
        """
        yield Header()
        yield self.banner
        yield self.info_panels
        yield self.msg_log
        yield self.input_box

    ## build sections

    def build_menu_section(self) -> Panel:
        """Build the menu section panel from the active menu

        Returns:
            Panel: menu section panel
        """
        menu = config.menu_template

        self.state_menu_items = self.menu_items_from_state()

        for opt in self.state_menu_items:
            menu += f"[bold]{opt['key']}[/bold]: {opt['description']}\n"

        menu += "\n"
        for opt in self.all_menu_items:
            menu += f"[bold]{opt['key']}[/bold]: {opt['description']}\n"

        self.menu = Panel(
            Text.from_markup(menu),
            title="[bold red]Menu[/bold red]",
            **config.panel_format,
        )

        return self.menu

    def build_info_section(self) -> Panel:
        """generate info section content

        Returns:
            Group: group of panels for the central info section
        """
        self.info = Panel(
            Group(
                self.build_user_panel(),
                self.build_device_panel(),
                self.build_image_panel(),
            ),
            **config.panel_format,
        )

        return self.info

    def build_opts_section(self) -> Panel:
        """build the option bytes section panel

        Returns:
            Panel: option bytes panels grouped
        """
        self.opts = Panel(
            Group(
                self.build_opts_panel(),
                self.build_opts_raw_panel(),
            ),
            **config.panel_format,
        )

        return self.opts

    ## build panels
    #   Info section
    #   - image panel: chip image
    #   - user panel: user-supplied data relection
    #   - device panel: device information
    #   Options section
    #   - opts table panel
    #   - opts bytes panel
    #

    def build_image_panel(self) -> Panel:
        """build the chip image panel, if not connected then
        this returns an empty panel.

        Returns:
            Panel: The chip image content in a panel
        """
        content = ""

        if self.connected_state == True:
            content = self.chip.chip_image

        return Panel(
            content,
            **config.panel_format,
        )

    def build_user_panel(self) -> Panel:
        """builds the connection state table wrapped in a panel

        Returns:
            Panel: the panel containing state table
        """
        title = ""
        content = Table("", "", **config.clear_table_format)
        content.add_row("", "")

        if self.state == STATE_READ_MEM or self.state == STATE_WRITE_MEM:
            title = "Memory I/O"
            content.add_row(
                "Operation     ",
                binary_colour(
                    True if self.state == STATE_READ_MEM else False,
                    true_str="Read",
                    false_str="Write",
                    true_fmt="green",
                    false_fmt="blue",
                ),
            )
            content.add_row("Address       ", f"{hex(self.address)}")
            content.add_row("Length        ", f"{self.read_len}")
            content.add_row("Offset        ", f"{self.offset}")
            content.add_row("File path     ", f"{self.filepath}")

        elif self.state == STATE_ERASE_MEM:
            content.add_row("Operation     ", "Erase Flash")
            content.add_row("Address       ", f"{hex(self.address)}")
            content.add_row("Length        ", f"{self.erase_len}")
        else:
            title = "Connection"
            content.add_row(
                "Connected    ",
                binary_colour(self.connected_state, "Connected", "Disconnected"),
            )
            content.add_row("", "")
            content.add_row("Port", f"{self.conn_port}")
            content.add_row("Baud", f"{self.conn_baud}")

        return Panel(
            content,
            title=title,
            **config.panel_format,
        )

    def build_opts_panel(self) -> Panel:
        """builds the option bytes table panel

        Returns:
            Panel: the option bytes table
        """
        opts_table = Table(
            "Option Byte",
            "Value",
            padding=(0, 1),
            expand=True,
            show_edge=False,
            box=None,
        )
        opts_table.add_row("", "")

        if self.connected_state == True:
            opts_table.add_row(
                "Read Protect",
                binary_colour(
                    self.stm_device.device.opt_bytes.readProtect,
                    true_str="enabled",
                    false_str="disabled",
                    false_fmt="blue",
                ),
            )
            opts_table.add_row(
                "Watchdog Type",
                binary_colour(
                    self.stm_device.device.opt_bytes.watchdogType,
                    false_str="Hardware",
                    true_str="Software",
                    false_fmt="blue",
                ),
            )
            opts_table.add_row(
                "Rst on Standby",
                binary_colour(
                    self.stm_device.device.opt_bytes.resetOnStandby,
                    true_str="enabled",
                    false_str="disabled",
                    false_fmt="blue",
                ),
            )
            opts_table.add_row(
                "Rst on Stop",
                binary_colour(
                    self.stm_device.device.opt_bytes.resetOnStop,
                    true_str="enabled",
                    false_str="disabled",
                    false_fmt="blue",
                ),
            )
            opts_table.add_row(
                "Data Byte 0", f"{hex(self.stm_device.device.opt_bytes.dataByte0)}"
            )
            opts_table.add_row(
                "Data Byte 1", f"{hex(self.stm_device.device.opt_bytes.dataByte1)}"
            )
            opts_table.add_row(
                "Write Prot 0", str(self.stm_device.device.opt_bytes.writeProtect0)
            )
            opts_table.add_row(
                "Write Prot 1", str(self.stm_device.device.opt_bytes.writeProtect1)
            )
            opts_table.add_row(
                "Write Prot 2", str(self.stm_device.device.opt_bytes.writeProtect2)
            )
            opts_table.add_row(
                "Write Prot 3", str(self.stm_device.device.opt_bytes.writeProtect3)
            )

        return Panel(
            opts_table,
            title="[bold cyan]Flash Option bytes[/bold cyan]",
            **config.panel_format,
        )

    def build_device_panel(self) -> Panel:
        """build the device info panel, when disconnected
        get a blinky "disconnected" panel, else device information

        Returns:
            Panel: device info panel
        """
        device_content = Table("", "", **config.clear_table_format)
        device_content.add_row("", "")  # spacer
        if self.connected_state == True:
            device_content.add_row("Device Type   ", f"{self.stm_device.device.name}")
            device_content.add_row(
                "Device ID     ", f"{hex(self.stm_device.getDeviceId())}"
            )
            device_content.add_row(
                "Bootloader v  ", f"{str(self.stm_device.getDeviceBootloaderVersion())}"
            )
            device_content.add_row(
                "Flash Size    ", f"{hex(self.stm_device.device.flash_memory.size)}"
            )
            device_content.add_row(
                "Flash Pages   ",
                f"{self.stm_device.device.flash_page_num} Pages of {self.stm_device.device.flash_page_size}b",
            )
            device_content.add_row(
                "RAM Size      ", f"{hex(self.stm_device.device.ram.size)}"
            )
        else:
            device_content = (
                Text.from_markup(
                    "No Device",
                    style=Style(
                        color="red",
                        bold=True,
                        italic=True,
                        blink=config.ENABLE_BLINK_EFFECT,
                    ),
                ),
            )

        return Panel(
            device_content,
            title="[bold yellow]Device[/bold yellow]",
            **config.panel_format,
        )

    def build_opts_raw_panel(self) -> Panel:
        raw_bytes_string = MARKUP(self.stm_device.device.opt_bytes.rawBytesToString())
        return Panel(raw_bytes_string, **config.panel_format)

    ## UI Updates: update the three central sections
    #   or all at once!

    def update_menu_section(self) -> None:
        """update the menu section content"""
        menu = self.get_widget_by_id("menu")
        menu_content = self.build_menu_section()
        menu.update(menu_content)

    def update_info_section(self) -> None:
        """update the info section content"""
        info = self.get_widget_by_id("info")
        info_content = self.build_info_section()
        info.update(info_content)

    def update_option_section(self) -> None:
        """update the option section content"""
        opts = self.get_widget_by_id("opts")
        opts_content = self.build_opts_section()
        opts.update(opts_content)
        self.info_panels = MainSections()

    def update_all_sections(self) -> None:
        """update all three main display sections"""
        self.update_menu_section()
        self.update_info_section()
        self.update_option_section()

    def handle_connected(self) -> None:
        """handle the initial connection to the device
        This function sets the chip image object
        TODO: Clean up, assign all objects here?
        """
        self.msg_log.write(SuccessMessage("Successfully connected_state!"))
        self.msg_log.write(
            SuccessMessage(f"Found device: {self.stm_device.device.name}")
        )
        self.msg_log.write(
            SuccessMessage(
                f"Flash start: {hex(self.stm_device.device.flash_memory.start)}"
            )
        )
        self.msg_log.write(
            SuccessMessage(
                f"Flash size: {hex(self.stm_device.device.flash_memory.size)}"
            )
        )
        self.chip = ChipImage(self.stm_device.device.name)
        self.update_state(STATE_IDLE_CONNECTED)

    def connect_to_device(self) -> bool:
        """Attempt to connect to the device using the supplied parameters

        Returns:
            bool: success
        """
        success = False
        try:
            self.msg_log.write(
                InfoMessage(
                    f"Connecting to device on {self.conn_port} at {self.conn_baud}bps"
                )
            )
            success = self.stm_device.connectAndReadInfo(
                self.conn_port, baud=self.conn_baud, readOptBytes=True
            )
        except Exception as e:
            self.msg_log.write(e)
        finally:
            return success

    ## OPERATIONS #

    async def long_running_task(self, function, *func_args, colour: str = "red"):
        """Wrapper for performing a long-running task whilst cycling the chip image
        animation. This is very very fun.
        TODO: Don't use the 'run in executor' function, asyncio.run might work
        Args:
            function (func): long-running task
            colour (str, optional): chip animation colour. Defaults to "red".

        Returns:
            Any: task result
        """
        info_widget = self.get_widget_by_id("info")
        task = asyncio.get_running_loop().run_in_executor(None, function, *func_args)
        user_panel = self.build_user_panel()
        device_panel = self.build_device_panel()

        while not task.done():
            info_widget.update(
                Panel(
                    Group(
                        user_panel,
                        device_panel,
                        next(self.chip, colour=colour),
                    ),
                    **config.panel_format,
                )
            )
            await asyncio.sleep(0.1)

        self.update_info_section()
        return task.result()

    async def input_to_attribute(self, msg: str, attribute: str, ex_type=str) -> None:
        """take a user-supplied input and assign it to a class attribute

        TODO: This is not smart, assign to a dict

        Args:
            msg (str): _description_
            attribute (str): _description_
            ex_type (_type_, optional): _description_. Defaults to str.
        """

        self.change_state(STATE_AWAITING_INPUT)
        self.msg_log.write(InfoMessage(f"{msg}"))
        self.set_focus(self.input_box)

        msg = await self.msg_queue.get()
        try:
            msg_fmtd = ex_type(msg)
            setattr(self, attribute, msg_fmtd)
            self.msg_log.write(InfoMessage(f"Set {attribute} to {msg_fmtd}"))
        except ValueError:
            self.msg_log.write(ErrorMessage(f"Invalid type: expected {ex_type}"))
        finally:
            self.restore_previous_state()

    ## KEYPRESS HANDLERS ##

    async def handle_vers_keypress(self):
        """handle print version keypress"""
        self.msg_log.write(
            InfoMessage(f"{APPLICATION_NAME} Version {APPLICATION_VERSION}")
        )
        self.change_state(self.idle_state())

    async def handle_port_keypress(self):
        """handle port input keypress"""
        await self.input_to_attribute("Enter connection port", "conn_port")
        self.update_info_section()

    async def handle_baud_keypress(self):
        """handle baud input keypress"""
        await self.input_to_attribute("Enter connection baud", "conn_baud")
        self.update_info_section()

    async def handle_connect_keypress(self):
        """handle the 'connect' keypress
        check parameters are set and connect to
        the STM device bootloader
        """
        if len(self.conn_port) == 0:
            self.msg_log.write(FailMessage("Must configure port first"))
        elif (
            self.conn_baud < STM_BOOTLOADER_MIN_BAUD
            or self.conn_baud > STM_BOOTLOADER_MAX_BAUD
        ):
            self.msg_log.write(
                FailMessage(
                    f"Invalid baud - min: {STM_BOOTLOADER_MIN_BAUD} max: {STM_BOOTLOADER_MAX_BAUD}"
                )
            )
        else:
            self.connected_state = self.connect_to_device()
            if self.connected_state == True:
                self.handle_connected()

    async def handle_readflash_keypress(self):
        """handle the 'read flash' keypress
        update menu to readwrite and update tables
        """
        self.change_state(STATE_READ_MEM)
        self.address = self.stm_device.device.flash_memory.start

    async def handle_erase_keypress(self):
        """handle the erase keypress
        calls the globalErase operation on the device
        """
        self.msg_log.write(InfoMessage("Erasing flash memory..."))
        await self.long_running_task(self.stm_device.globalEraseFlash)
        self.msg_log.write(SuccessMessage("Succesfully erased all flash pages"))

    async def handle_readpages_keypress(self):
        self.msg_log.write(InfoMessage("Reading flash pages..."))
        occupied = 0
        empty = 0
        errors = 0

        for i in range(self.stm_device.device.flash_page_num):
            self.msg_log.write(InfoMessage(f"Reading flash pages {i}"))
            success, rx = await self.long_running_task(
                self.stm_device.readFromFlash,
                self.stm_device.device.flash_pages[i].start,
                self.stm_device.device.flash_page_num,
            )
            if not success:
                self.msg_log.write(FailMessage(f"Error reading flash page {i}"))
                errors += 1
            else:
                page_empty = True
                for b in rx:
                    if b != 0xFF:
                        page_empty = False
                        occupied += 1
                        break
                if page_empty == True:
                    empty += 1

        self.msg_log.write(
            InfoMessage(
                f"Read {self.stm_device.device.flash_page_num} pages (errors: {errors})"
            )
        )
        self.msg_log.write(
            InfoMessage(f"Page status-> Occupied pages: {occupied} Free pages: {empty}")
        )

    async def handle_length_keypress(self):
        await self.input_to_attribute("Enter length", "length", int)
        self.update_info_section()

    async def handle_filepath_keypress(self):
        await self.input_to_attribute("Enter file path", "filepath")
        if not os.path.exists(self.filepath):
            self.msg_log.write(
                ErrorMessage(f"Error: invalid file path {self.filepath}")
            )
            self.filepath = ""
        self.update_info_section()

    async def handle_offset_keypress(self):
        await self.input_to_attribute("Enter offset from start address", "offset", int)
        self.update_info_section()

    async def handle_upload_keypress(self):
        """run sanity checks then upload application"""
        if (
            self.length > config.MAX_UPLOAD_FILE_LEN
            or self.length < config.MIN_UPLOAD_FILE_LEN
        ):
            self.msg_log.write(
                FailMessage(
                    f"Error - invalid file length (min {config.MIN_UPLOAD_FILE_LEN} max {config.MAX_UPLOAD_FILE_LEN})"
                )
            )
            self.length = 0
            self.update_info_section()
            return

        if not self.stm_device.device.flash_memory.is_valid(self.address + self.offset):
            self.msg_log.write(FailMessage(f"Error - invalid address with offset"))
            self.offset = 0
            self.update_info_section()
            return

        status = await self.long_running_task(
            self.stm_device.writeApplicationFileToFlash,
            self.filepath,
            self.offset,
            colour="green",
        )

    async def handle_cancel_keypress(self):
        """TODO: Cancel the current task here"""
        self.change_state(self.idle_state())

    async def handle_option_bytes(self):
        """TODO: This :)"""
        pass

    def handle_exit_keypress(self) -> None:
        """TODO: make sure there are no long-running tasks, and cancel them if
        they are running
        TODO: Prompt the user if there are long-running tasks
        """
        print("Bye!")
        sys.exit()

    async def handle_key(self, key: str):
        # debug keybindings
        if key == "@":
            self.action_screenshot()

        if DEBUG_MODE:
            if key == "l":
                await self.long_running_task(sleep, 5)

        # menu commands
        for command in self.state_menu_items:
            if key == command["key"] and command["action"] is not None:
                asyncio.create_task(command["action"]())

    async def _on_key(self, event: Key) -> None:
        await super()._on_key(event)
        await self.handle_key(event.char)

    async def read_from_flash(self):
        """TODO: rename function aligned with the others, task_NAME"""
        if self.filepath is not None and self.read_len > 0:
            success = True
            chunks = int(self.read_len / 256)
            rem = int(self.read_len % 256)

            with open(self.filepath, "wb") as f:
                for i in range(chunks):
                    self.msg_log.write(InfoMessage(f"Reading chunk {i+1}"))
                    success, rx = self.stm_device.readFromFlash(
                        self.stm_device.device.flash_memory.start + self.offset,
                        256,
                    )
                    if success:
                        f.write(rx)
                    else:
                        self.msg_log.write(ErrorMessage(f"Error Reading chunk {i+1}"))
                        break

                if rem > 0 and success == True:
                    self.msg_log.write(InfoMessage(f"Reading chunk {chunks+1}"))
                    success, rx = self.stm_device.readFromFlash(
                        self.stm_device.device.flash_memory.start
                        + self.offset
                        + (chunks * 256),
                        rem,
                    )
                    if success:
                        f.write(rx)
                    else:
                        self.msg_log.write(
                            ErrorMessage(f"Error Reading chunk {chunks+1}")
                        )
            if success:
                self.msg_log.write(
                    SuccessMessage(
                        f"Succesfully read {self.read_len} bytes from flash into file {self.filepath}"
                    )
                )

        # clear the self variables
        self.read_len = 0
        self.filepath = None
        self.offset = 0

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        """handle input received from the input box

        Args:
            message (Input.Submitted): the user input
        """
        if self.state != STATE_AWAITING_INPUT:
            # we are not expecting any inputs so ignore here
            pass
        else:
            # send to message queue
            await self.msg_queue.put(message.value)


if __name__ == "__main__":
    app = StmApp()
    app.run()
