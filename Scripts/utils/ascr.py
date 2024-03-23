# ASCR functions.
#
# Parsed ASCR data is converted into strings delineated with | characters.
# Rows for the strings contain: string offset, string type ("code", "dialogue", or "lcd"), text converted to UTF-8.
# Rows for subroutine data contain: four data values, data offset, subroutine name from strings, bytes.


import re
import struct
from io import BytesIO

KNOWN_SIGNATURES = [b"\xba\xaf\x55\xcc", b"\x24\xf7\x01\x65"]
SJIS_DICT = {
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
        "ß": 0x82BF,  # Reni Milchstraße
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


class ASCRError(Exception):
    pass


def ascii_to_sjis(
    input_str, break_lines=True, offset=0, *args, **kwargs
) -> tuple[bytearray, int]:
    """Converts a string of ASCII characters to byte-swapped Shift-JIS
    and null-terminate it.

    Set break_lines to false to bypass the linebreak function.
    Use this for non-dialogue text, such as menus.

    Set the offset argument to the number of tiles to skip from the
    SJIS_DICT. This can be used to redefine otherwise unused tiles
    for custom glyphs, such as an alternate font for areas outside of
    the dialogue box with a different font size.

    The keyword arguments filename, length_limit, last_row_length_limit,
    and row_limit can be passed to the linebreak function.

    Returns a tuple containing a bytearray of the encoded string and
    the number of linebreak warnings generated."""

    warnings = 0

    if break_lines:
        input_str, _, warnings = _linebreak(
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
                output += struct.pack(">H", SJIS_DICT[input_str[i]] + offset)
            except KeyError as e:
                if kwargs.get("filename") is not None:
                    raise ASCRError(
                        f"At line ID {kwargs['line_id']}: Invalid character {e}."
                    )
                    
                else:
                    print(f"[Error] Invalid character {e}.")
                    raise e

        else:
            # If { is encountered, parse as a control code and paste characters directly rather than translating them.
            while input_str[i + 1] != "}":  # Check next character and stop pasting when } is next.
                i += 1
                output += bytes(input_str[i], "shift_jis")
            i += 1  # Skip } character.

        i += 1

    output += b"\x00"

    return (output, warnings)


def _linebreak(
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
    input_str = [i for i in input_str.replace(r"\n", " \\ ").replace("//", " \\ ").split(" ") if i != ""]

    for i in enumerate(input_str):
        word = i[1]
        # Do not count control code sequences in word length.
        word_length = len(i[1]) - sum(
            [len(p) for p in re.findall("{[a-zA-Z0-9,@!=]+}", word)]
        )

        # Insert word that is not a forced line break.
        if word != "\\":
            if current_length + word_length + 1 <= length_limit:
                output += word
                current_length += word_length + 1
            else:
                # Do not break line if the length exactly matches the limit.
                if current_length + word_length == length_limit:
                    output = output + word + "\\"
                    current_length = 0
                else:
                    output = output.rstrip() + "\\" + word
                    current_length = word_length
                rows += 1
            # Add a space if there are more words remaining and the last character in the buffer is not "\", or break otherwise.
            if i[0] < len(input_str):
                if output[-1] != "\\":
                    output += " "
                else:
                    current_length = 0
            else:
                break
        else:
            # Attempt to avoid a line break on an empty line.
            if current_length == 0:
                continue
            output = output.rstrip() + "\\"  # Remove space inserted by previous word.
            rows += 1
            current_length = 0

    if rows == row_limit and current_length > last_row_length_limit:
        if filename is not None and line_id is not None:
            print(
                f"[Warning] {filename}: Last row limit overflow at line {line_id}: {output}"
            )
        else:
            print(f"[Warning] Last row limit overflow: {output}")
        warnings += 1

    if rows > row_limit:
        if filename is not None and line_id is not None:
            print(
                f"[Warning] {filename}: Line break overflow at line {line_id}: {output}"
            )
        else:
            print(f"[Warning] Line break overflow: {output}")
        warnings += 1

    return (output, rows, warnings)


def read_string(file, encoding="shift_jis") -> bytearray:
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


def read_ascr(data: BytesIO, filename="") -> tuple[list,list]:
    """Parses a BytesIO stream containing an ASCR chunk. Text and
    subroutine data are processed into strings.

    Returns a tuple containing a list of text strings and a list of
    the subroutine data.
    Raises ASCRError if the data input is invalid, such as an
    unknown signature after the 8-byte header."""

    if filename != "":
        filename += ": "

    # Skip header.
    data.seek(8)

    header = data.read(4)
    if header not in KNOWN_SIGNATURES:
        raise ASCRError(f"{filename}Header not recognized: {header.hex()}")

    # Location of table of offsets for text area at the end of this chunk.
    text_location = struct.unpack("<I", data.read(4))[0] + 8
    # Number of strings in this chunk.
    text_count = struct.unpack("<I", data.read(4))[0]
    # Location of table of offsets for binary data associated with subroutines.
    subroutines_location = struct.unpack("<I", data.read(4))[0] + 8
    # Number of entries in the binary data table.
    subroutines_count = struct.unpack("<I", data.read(4))[0]

    # Strings are referenced during the writing of the binary data table.
    text_decoded = []

    # First offset is equal to the location of the offset table
    # added to the total length of the offsets in this table.
    text_entries = []
    data_location = text_location + (text_count * 4)

    for i in range(text_count):
        data.seek(text_location + (i * 4))  # Seek to location of offset table.
        data_location = struct.unpack("<I", data.read(4))[0] + text_location

        # Retrieve text.
        data.seek(data_location)
        text = read_string(data)
        if text.isascii():
            entry_type = "code"
        else:
            if "　　▼" in text:
                entry_type = "lcd"
            else:
                entry_type = "dialogue"

        text_entries.append([str(i) for i in [hex(data_location), entry_type, text]])
        text_decoded.append(text)

    # Read the binary data table and output raw values in a separate CSV file.
    subroutines_data = []
    data_location = subroutines_location + (subroutines_count * 16)

    for i in range(subroutines_count):
        data.seek(subroutines_location + (i * 16))
        data_index = struct.unpack("<I", data.read(4))[0]
        # Data values 2-4 are currently unknown.
        data2 = struct.unpack("<I", data.read(4))[0]
        data3 = struct.unpack("<I", data.read(4))[0]
        data4 = struct.unpack("<I", data.read(4))[0]

        # Retrieve data.
        data.seek(data_location)
        byte_string = bytearray()
        while True:
            # Read 4 bytes at a time.
            # If the last 2 bytes are 40 40, continue with the next data chunk.
            bytes = data.read(4)
            byte_string += bytes
            if bytes[2:] == b"\x40\x40":
                data_raw = byte_string.hex(" ")
                break

        subroutines_data.append(
            [
                str(i)
                for i in [
                    data_index,
                    data2,
                    data3,
                    data4,
                    hex(data_location),
                    text_decoded[-(subroutines_count - i)],
                    data_raw,
                ]
            ]
        )

        # As there is no offset table for the binary data, reset data_location for next chunk by using the end of the current chunk.
        data_location = data.tell()

    print(
        f"{filename}Text offset table location: {hex(text_location)}, entries: {text_count}.",
        f"Subroutine table location: {hex(subroutines_location)}, entries: {subroutines_count}.",
        f"Text start location: {text_entries[0][0]}.",
    )

    return (text_entries, subroutines_data)


def write_ascr(
    ascr_data: BytesIO, strings: list, add_header=True, filename: str = None
) -> tuple[bytearray, int]:
    """Given a source ASCR data chunk, create a new chunk from a list
    of strings injected after the subroutine data. Offsets are
    recalculated, and all other data is retained.

    If add_header is true, also add a header with ASCR signature and 
    size information and the EOFC footer. If the chunk will be 
    compressed, this should be false.

    filename is a string, passed to the ascii_to_sjis function for
    informational purposes when a linebreak results in overflow.

    Returns a tuple containing bytearray containing the new ASCR chunk 
    and the number of warnings returned by ascii_to_sjis.
    Raises ASCRError if either the ASCR or strings input is
    invalid."""

    warnings = 0

    # Parse ASCR input.
    header = ascr_data.read(16)
    if header[0:4] != b"ASCR":
        raise ASCRError("Not an ASCR chunk.")

    if header[8:12] not in KNOWN_SIGNATURES:
        raise ASCRError(f"Header not recognized: {header[8:12].hex()}")

    # Set address and limits.
    ascr_data.seek(12)
    offset_table_address = struct.unpack("<I", ascr_data.read(4))[0] + 8

    # The first string is empty, which will cause the second offset
    # to be 1 greater than the first.
    new_offsets = bytearray()
    new_strings = bytearray()

    # Assume first offset is located in second 4-byte value of first entry
    # in offset table.
    # Skip next 4 bytes, which is the line count.
    ascr_data.seek(offset_table_address + 4)
    current_offset = struct.unpack("<I", ascr_data.read(4))[0]

    # Parse strings.
    for i in enumerate(strings, start=1):
        try:
            offset, entry_type, new_text = i[1]
        except ValueError as e:
            ascr_data.close()
            raise ASCRError(f"Error parsing line {i[0]}: {e}")

        if entry_type != "code" and re.fullmatch(
            r'[A-zÀ-ÿ0-9œ`~!@#$%^&*(){}_|+\-×÷=?;:<>°\'",.\[\]/—–‘’“”☆★ ]+',
            new_text,
            re.I,
        ):
            # Only translate strings that are not type "code" and contain only non-Japanese characters.
            # ascii_to_sjis will pass warning counts, which will be reported at the end of this script's execution.
            line_encoded, warning = ascii_to_sjis(
                new_text, line_id=i[0], filename=filename
            )
            warnings += warning
        elif entry_type in ["code", "lcd", "dialogue"]:
            line_encoded = new_text.encode(encoding="shift_jis") + b"\x00"
        else:
            raise ASCRError(f"Unknown entry type in line {i[0]}: {entry_type}")

        new_strings += line_encoded
        # Subtract 1 from current_offset to compensate for first empty string.
        new_offsets += struct.pack("<I", current_offset - 1)
        # Increase next offset by the length of the string in bytes.
        current_offset += len(line_encoded)

    new_data = bytearray()

    # Copy data preceding text offset table location.
    ascr_data.seek(8)
    new_data = ascr_data.read(offset_table_address - 8) + new_offsets + new_strings

    if (padding := len(new_data) % 4) != 0:
        new_data += b"\x40" * padding

    if add_header:
        output_binary = (
            b"ASCR"
            + struct.pack("<I", len(new_data))
            + new_data
            + b"EOFC\x00\x00\x00\x00"
        )
    else:
        output_binary = new_data

    return (output_binary, warnings)


def main():
    """When run as a script, encode strings to binary Shift_JIS
    without line breaks."""

    while True:
        input_str = input("String (Input blank string to exit): ")
        if input_str != "":
            print(ascii_to_sjis(input_str, break_lines=True)[0].hex(), "\n")
        else:
            break


if __name__ == "__main__":
    main()
