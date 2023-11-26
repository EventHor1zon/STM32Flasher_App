from rich.text import Text

CHIP_IMG_OFFSET = 12
FLASH_IMG_OFFSET = 4
CHIP_VALUE_WIDTH = 13
CHIP_IMG_WIDTH = 15
CHIP_IMG_HEIGHT = 8

CHIP_IMG = f"""
{" "*CHIP_IMG_OFFSET}  █ █ █ █ █ █
{" "*CHIP_IMG_OFFSET}▄             ▄
{" "*CHIP_IMG_OFFSET}▄             ▄
{" "*CHIP_IMG_OFFSET}▄             ▄
{" "*CHIP_IMG_OFFSET}▄             ▄
{" "*CHIP_IMG_OFFSET}▄             ▄
{" "*CHIP_IMG_OFFSET}▄             ▄
{" "*CHIP_IMG_OFFSET}  █ █ █ █ █ █
"""


FLASH_IMAGE = """
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄
"""


def generateFlashImage(
    num_pages: int, start_addr: int = 0x20000000, end_addr: int = 0x20001FFF
):
    fa = start_addr
    fe = end_addr
    out = ""
    block = "▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄\n"
    out += f"{' ' * FLASH_IMG_OFFSET}▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄  {hex(fe)}\n"
    out += (" " * FLASH_IMG_OFFSET + block) * (num_pages - 16)
    out += f"{' ' * FLASH_IMG_OFFSET}▄ ▄ ▄ ▄ ▄ ▄ ▄ ▄  {hex(fa)}\n"

    return out


class ChipImage:

    step = 0

    def __init__(self, name: str, colour: str = "red"):
        self.colour = colour
        self.name = name
        self.dev_type = self.get_device_name_short()
        self.density = self.get_device_dens_string()
        self.chip_image = self.generateChipImage()

    def __iter__(self):
        self.step = 0
        return self

    def generateChipImage(self):

        dev_type = self.dev_type
        density = self.density
        r = CHIP_IMG.split("\n")
        # format the name row
        if len(dev_type) > CHIP_VALUE_WIDTH:
            dev_type = dev_type[:CHIP_VALUE_WIDTH]
        spaces = CHIP_VALUE_WIDTH - len(dev_type)
        name = (
            (" " * CHIP_IMG_OFFSET)
            + ("▄")
            + (" " * int(spaces / 2))
            + dev_type
            + (" " * (int(spaces / 2) + 1 if spaces % 2 == 1 else int(spaces / 2)))
            + ("▄")
        )
        r[4] = name
        # format the density row
        if len(density) > 13:
            density = density[:13]

        spaces = CHIP_VALUE_WIDTH - len(density)
        dens = (
            (" " * CHIP_IMG_OFFSET)
            + ("▄")
            + (" " * int(spaces / 2))
            + density
            + (" " * (int(spaces / 2) + 1 if spaces % 2 == 1 else int(spaces / 2)))
            + ("▄")
        )

        r[5] = dens

        return "\n".join(r)[1:]

    def get_device_name_short(self):
        return self.name.split("xxx")[0] + "xxx"

    def get_device_dens_string(self):
        density = self.name.split("xxx")[1].split("Density")
        return density[0] + ("VAL" if len(density) > 1 and len(density[1]) > 1 else "")

    def __next__(self, colour: str = None):

        if colour is not None:
            self.colour = colour
        lines = self.chip_image.split("\n")
        if self.step < 5:
            line = lines[0]
            elements = line.split(" ")
            # ['', '', '█', '█', '█', '█', '█', '█', '', '']
            elements[
                CHIP_IMG_OFFSET + self.step + 2
            ] = f"[{self.colour}]{elements[CHIP_IMG_OFFSET + self.step + 2]}[/{self.colour}]"

            newline = " ".join(elements)

            lines[0] = newline

        elif self.step < 12:
            line = lines[self.step - 5]
            elements = line.split(" ")
            elements[-1] = f"[{self.colour}]{elements[-1]}[/{self.colour}]"

            newline = " ".join(elements)
            lines[self.step - 5] = newline

        elif self.step < 18:
            line = lines[-2]
            elements = line.split(" ")
            # ['', '', '█', '█', '█', '█', '█', '█', '', '']
            elements[
                -(self.step - 11)
            ] = f"[{self.colour}]{elements[-(self.step - 11)]}[/{self.colour}]"
            newline = " ".join(elements)

            lines[-2] = newline

        elif self.step < 24:
            line = lines[-(self.step - 17) - 2]
            elements = line.split(" ")
            elements[
                CHIP_IMG_OFFSET
            ] = f"[{self.colour}]{elements[CHIP_IMG_OFFSET]}[/{self.colour}]"

            newline = " ".join(elements)
            lines[-(self.step - 17) - 2] = newline

        else:
            self.step = -1

        self.step += 1

        out = "\n".join(lines)
        return Text.from_markup(out)
