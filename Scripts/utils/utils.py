# Helper functions for translation scripts.

import re
import struct


def ascii_to_sjis(
    input_str, break_lines=True, offset=0, *args, **kwargs
) -> tuple[bytearray, int]:
    """Converts a string of ASCII characters to byte-swapped Shift-JIS
    and null-terminate it.

    Set break_lines to false to bypass the linebreak function.
    Use this for non-dialogue text, such as menus.

    Set the offset argument to the number of tiles to skip from the
    below table. This can be used to redefine otherwise unused tiles
    for custom glyphs, such as an alternate font for areas outside of
    the dialogue box with a different font size.

    The keyword arguments filename, length_limit, last_row_length_limit,
    and row_limit can be passed to the linebreak function.

    Returns a tuple containing a bytearray of the encoded string and
    the number of linebreak warnings generated."""

    table = {
        "A": 0x8260,
        "B": 0x8261,
        "C": 0x8262,
        "D": 0x8263,
        "E": 0x8264,
        "F": 0x8265,
        "G": 0x8266,
        "H": 0x8267,
        "I": 0x8268,
        "J": 0x8269,
        "K": 0x826A,
        "L": 0x826B,
        "M": 0x826C,
        "N": 0x826D,
        "O": 0x826E,
        "P": 0x826F,
        "Q": 0x8270,
        "R": 0x8271,
        "S": 0x8272,
        "T": 0x8273,
        "U": 0x8274,
        "V": 0x8275,
        "W": 0x8276,
        "X": 0x8277,
        "Y": 0x8278,
        "Z": 0x8279,
        "a": 0x827A,
        "b": 0x827B,
        "c": 0x827C,
        "d": 0x827D,
        "e": 0x827E,
        "f": 0x8280,
        "g": 0x8287,
        "h": 0x8288,
        "i": 0x8289,
        "j": 0x828A,
        "k": 0x828B,
        "l": 0x828C,
        "m": 0x828D,
        "n": 0x828E,
        "o": 0x828F,
        "p": 0x8290,
        "q": 0x8291,
        "r": 0x8292,
        "s": 0x8293,
        "t": 0x8294,
        "u": 0x8295,
        "v": 0x8296,
        "w": 0x8297,
        "x": 0x8298,
        "y": 0x8299,
        "z": 0x829A,
        "À": 0x829F,  # These French accented letters replace hiragana starting at small ぁ.
        "Â": 0x82A0,
        "Ä": 0x82A1,
        "Æ": 0x82A2,
        "Ç": 0x82A3,
        "È": 0x82A4,
        "É": 0x82A5,
        "Ê": 0x82A6,
        "Ë": 0x82A7,
        "Î": 0x82A8,
        "Ï": 0x82A9,
        "Ô": 0x82AA,
        "Œ": 0x82AB,
        "Ù": 0x82AC,
        "Û": 0x82AD,
        "Ü": 0x82AE,
        "à": 0x82AF,
        "â": 0x82B0,
        "ä": 0x82B1,
        "æ": 0x82B2,
        "ç": 0x82B3,
        "è": 0x82B4,
        "é": 0x82B5,
        "ê": 0x82B6,
        "ë": 0x82B7,
        "î": 0x82B8,
        "ï": 0x82B9,
        "ô": 0x82BA,
        "œ": 0x82BB,
        "ù": 0x82BC,
        "û": 0x82BD,
        "ü": 0x82BE,
        " ": 0x8140,
        ".": 0x8144,
        ",": 0x8143,
        ":": 0x8146,
        ";": 0x8147,
        "?": 0x8148,
        "!": 0x8149,
        "'": 0x814C,  # Apostrophe
        '"': 0x814E,
        "—": 0x815C,  # Em dash
        "–": 0x815B,  # En dash
        "-": 0x815D,  # Dash
        "/": 0x815E,
        "~": 0x8160,
        "‘": 0x8165,  # Opening single quotation
        "’": 0x8166,  # Closing single quotation
        "“": 0x8167,  # Opening double quotation
        "”": 0x8168,  # Closing double quotation
        "(": 0x8169,
        ")": 0x816A,
        "[": 0x816D,
        "]": 0x816E,
        "+": 0x817B,
        "×": 0x817E,  # Multiplication sign
        "÷": 0x8180,  # One value skipped internally for some reason.
        "=": 0x8181,
        "<": 0x8183,
        ">": 0x8184,
        "°": 0x818B,
        "$": 0x8190,
        "%": 0x8193,
        "#": 0x8194,
        "&": 0x8195,
        "*": 0x8196,
        "@": 0x8197,
        "☆": 0x8199,
        "★": 0x819A,
        "0": 0x8240,
        "1": 0x8241,
        "2": 0x8242,
        "3": 0x8243,
        "4": 0x8244,
        "5": 0x8245,
        "6": 0x8246,
        "7": 0x8247,
        "8": 0x8248,
        "9": 0x8249,
        "９": 0x8258,  # Control character for playtime counter in OpOptionSave.bin.
        "\\": 0x2F2F,
        "{": None,  # Ignore curly brackets as they are used for control codes.
        "}": None,
    }

    warnings = 0

    if break_lines:
        input_str, _, warnings = linebreak(
            input_str,
            line_id=kwargs.get("line_id", None),
            filename=kwargs.get("filename", None),
            length_limit=kwargs.get("length_limit", 37),
            last_row_length_limit=kwargs.get("last_row_length_limit", 37),
            row_limit=kwargs.get("row_limit", 3),
        )

    input_str = input_str.strip()

    output = bytearray()

    i = 0
    while i < len(input_str):
        if input_str[i] != "{":
            try:
                output += struct.pack(">H", table[input_str[i]] + offset)
            # Exit if a script file contains a character not in table, continue if run from command line.
            except KeyError as e:
                if kwargs.get("filename") is not None:
                    print(
                        f"Error reading {kwargs['filename']} at line ID {kwargs['line_id']}: Invalid character {e}."
                    )
                    exit()
                else:
                    print(f"Error: Invalid character {e}.")
                    return (b"", 1)

        else:
            # If { is encountered, parse as a control code and paste characters directly rather than translating them.
            while (
                input_str[i + 1] != "}"
            ):  # Check next character and stop pasting when } is next.
                i += 1
                output += bytes(input_str[i], "shift_jis_2004")
            i += 1  # Skip } character.

        i += 1

    output += b"\x00"  # Terminate string.

    return (output, warnings)


def linebreak(
    input_str,
    filename=None,
    line_id=None,
    length_limit=37,
    last_row_length_limit=37,
    row_limit=3,
) -> tuple[str, int, int]:
    """Break lines into rows according to length_limit.
    Default length is 37.
    A backslash character is inserted at line breaks,
    which is translated in ascii_to_sjis to byte 2F2F.

    Control code sequences are not counted in word length,
    assuming they consist of {} containing only letters, numbers,
    commas, and @. Because of the need for non-printable control
    codes, the standard text wrapping functions cannot be used.

    Returns a tuple containing the output string, the number of
    rows, and the number of warnings generated.
    """

    output = ""
    current_length = 0
    rows = 1
    warnings = 0

    # Split input string into an enumerated list of each word. Forced line breaks are split into their own word.
    input_str = list(
        enumerate(input_str.replace(r"\n", " \\ ").replace("//", " \\ ").split(" "), 1)
    )

    for i in input_str:
        word_length = len(i[1]) - sum(
            [len(p) for p in re.findall("{[a-zA-Z0-9,@!=]+}", i[1])]
        )  # Do not count control code sequences in word length.

        # Insert word that is not a forced line break.
        if i[1] != "\\":
            if current_length + word_length + 1 <= length_limit:
                output += i[1]
                current_length += word_length + 1
            else:
                output = output.rstrip() + "\\" + i[1]
                rows += 1
                current_length = word_length
            # Add a space if there are more words remaining, or break otherwise.
            if i[0] < len(input_str):
                output += " "
            else:
                break
        else:
            output = output.rstrip() + "\\"  # Remove space inserted by previous word.
            rows += 1
            current_length = 0

    if rows == row_limit and current_length > last_row_length_limit:
        if filename is not None and line_id is not None:
            print(
                f"Warning: Last row limit overflow in {filename} at line {line_id}: {output}"
            )
        else:
            print(f"Warning: Last row limit overflow: {output}")
        warnings += 1

    if rows > row_limit:
        if filename is not None and line_id is not None:
            print(f"Warning: Line break overflow in {filename} at line {line_id}: {output}")
        else:
            print(f"Warning: Line break overflow: {output}")
        warnings += 1

    return (output, rows, warnings)


def swap_bytes(value):
    """Convert hex string to little-endian bytes."""

    str = hex(value)[2:].zfill(8)

    return str[6:8] + str[4:6] + str[2:4] + str[0:2]


def read_string(file, encoding="shift_jis_2004") -> bytearray:
    """Read a null-terminated string from a file object opened in
    binary mode, using the codec given by the encoding argument.

    Script text is read as Shift_JIS-2004, which is the default encoding.
    https://en.wikipedia.org/wiki/Shift_JIS#Shift_JISx0213_and_Shift_JIS-2004

    If encoding is None, the string is not decoded."""

    byte_string = bytearray()
    while True:
        bytes = file.read(1)
        if bytes == b"":
            raise ValueError("Unable to read bytes.")
        if bytes == b"\x00":  # Strings are terminated with single byte 00.
            if encoding is not None:
                return byte_string.decode(encoding)
            else:
                return byte_string
        byte_string += bytes


def main():
    """When run as a script, encode strings to binary Shift_JIS-2004
    without line breaks."""

    while True:
        input_str = input("String (Input blank string to exit): ")
        if input_str != "":
            print(ascii_to_sjis(input_str, break_lines=False)[0].hex(), "\n")
        else:
            break


if __name__ == "__main__":
    main()
