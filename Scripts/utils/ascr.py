# ASCR functions.
#
# Parsed ASCR data is converted into strings delineated with | characters.
# Rows for the strings contain: string offset, string type ("code", "dialogue", or "lcd"), text converted to UTF-8.
# Rows for subroutine data contain: four data values, data offset, subroutine name from strings, bytes.


import re
import struct
from io import BytesIO

from utils.utils import ascii_to_sjis, read_string

KNOWN_SIGNATURES = [b"\xba\xaf\x55\xcc", b"\x24\xf7\x01\x65"]


class ParsingError(Exception):
    pass


def read_ascr(data: BytesIO, filename="") -> tuple[list,list]:
    """Parses a BytesIO stream containing an ASCR chunk. Text and
    subroutine data are processed into strings.

    Returns a tuple containing a list of text strings and a list of
    the subroutine data.
    Raises ParsingError if the data input is invalid, such as an
    unknown signature after the 8-byte header."""

    if filename != "":
        filename = filename + ": "

    # Skip header.
    data.seek(8)

    header = data.read(4)
    if header not in KNOWN_SIGNATURES:
        raise ParsingError(f"{filename}Header not recognized: {header.hex()}")

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

    If add_header is true, also add a header with ASCR signature and size
    information and the EOFC footer. If the chunk will be compressed,
    this should be false.

    filename is a string, passed to the ascii_to_sjis function for
    informational purposes when a linebreak results in overflow.

    Returns a tuple containing bytearray containing the new ASCR chunk and
    the number of warnings returned by ascii_to_sjis.
    Raises ParsingError if either the ASCR or strings input is
    invalid."""

    warnings = 0

    # Parse ASCR input.
    header = ascr_data.read(16)
    if header[0:4] != b"ASCR":
        raise ParsingError("Not an ASCR chunk.")

    if header[8:12] not in KNOWN_SIGNATURES:
        raise ParsingError(f"Header not recognized: {header[8:12].hex()}")

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
            raise ParsingError(f"Error parsing line {i[0]}: {e}")

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
            line_encoded = new_text.encode(encoding="shift_jis_2004") + b"\x00"
        else:
            raise ParsingError(f"Unknown entry type in line {i[0]}: {entry_type}")

        new_strings += line_encoded
        # Subtract 1 from current_offset to compensate for first empty string.
        new_offsets += struct.pack("<I", current_offset - 1)
        # Increase next offset by the length of the string in bytes.
        current_offset += len(line_encoded)

    new_data = bytearray()

    # Copy data preceding text offset table location.
    ascr_data.seek(8)
    new_data = ascr_data.read(offset_table_address - 8) + new_offsets + new_strings

    while True:
        new_data += b"\x40"
        if len(new_data) % 4 == 0:
            break

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
