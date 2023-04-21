from rich.text import Text


def SuccessMessage(msg) -> Text:
    return Text.from_markup(
        f"[bold][[green]+[/green]][/bold] {msg}",
    )


def InfoMessage(msg) -> Text:
    return Text.from_markup(f"[bold][[yellow]@[/yellow]][/bold] {msg}")


def FailMessage(msg) -> Text:
    return Text.from_markup(f"[bold][[magenta]-[/magenta]][/bold] {msg}")


def ErrorMessage(msg) -> Text:
    return Text.from_markup(f"[bold][[red]![/red]][/bold] {msg}")


def MARKUP(msg) -> Text:
    return Text.from_markup(msg)


def binary_colour(
    condition: bool,
    true_str: str,
    false_str: str,
    true_fmt: str = "green",
    false_fmt: str = "red",
) -> Text:
    """! @function binary_colour
    @brief returns a Rich Text object coloured depending on a binary condition
    @parameter condition condition on which string is coloured
    @parameter true_str print this string if condition is true
    @parameter false_str print this string if condition is false
    @parameter true_fmt format string thusly if true (default green)
    @parameter false_fmt format string thusly if false (default red)
    @return formatted Rich Text object
    """
    true_msg = str(condition) if true_str is None else true_str
    false_msg = str(condition) if false_str is None else false_str
    return Text.from_markup(
        f"[{true_fmt if condition else false_fmt}]{true_msg if condition else false_msg}[/{true_fmt if condition else false_fmt}]"
    )
