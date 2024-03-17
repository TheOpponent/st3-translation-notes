# ruff: noqa: F403, F405

# PRS functions, with wrapping needed by Sakura Taisen 3 added.

import platform
import struct
import sys
import time
from ctypes import *

start_time = time.time()

PLATFORM = platform.system()
IS_64BITS = sys.maxsize > 2**32

if PLATFORM == "Windows":
    lib = cdll.LoadLibrary("./lib/prs.dll")
elif PLATFORM == "Linux":
    lib = cdll.LoadLibrary("./lib/prs.so")
else:
    print("Cannot determine platform.")
    exit(1)

lib.prs_compress.argtypes = [
    POINTER(c_char),
    c_int,
    POINTER(POINTER(c_char)),
]
lib.prs_compress.restype = c_int
lib.prs_decompress.argtypes = [
    POINTER(c_char),
    c_int,
    POINTER(c_char),
    c_int,
]
lib.prs_decompress.restype = c_int


class PRSError(Exception):
    pass


def compress(input_data: bytes):
    """Apply PRS compression to a data chunk starting with a four-byte
    signature and size information."""

    input_signature = input_data[0:4]
    uncompressed_length = len(input_data) - 8
    uncompressed_data_array = create_string_buffer(input_data[8:])
    compressed_data_ptr = POINTER(c_char)()

    compressed_length = lib.prs_compress(
        uncompressed_data_array,
        uncompressed_length,
        byref(compressed_data_ptr),
    )

    if compressed_length > 0:
        compressed_data = bytearray(string_at(compressed_data_ptr, compressed_length))

        # Pad compressed data.
        compressed_data.extend(b"\x00\x00")
        if (padding := len(compressed_data) % 4) != 0:
            compressed_data.extend(b"\x00" * (4 - padding))

        padded_length = compressed_length + padding + 10

        # The header of the output includes the padded length, input length, and unpadded length.
        output_data = bytearray(input_signature)
        output_data.extend(struct.pack("<I", padded_length))
        output_data.extend(struct.pack("<I", uncompressed_length))
        output_data.extend(struct.pack("<I", compressed_length))
        output_data.extend(compressed_data)
        output_data.extend(b"CPRS\x00\x00\x00\x00EOFC\x00\x00\x00\x00")
        return output_data
    else:
        raise PRSError("PRS compression failed.")


def decompress(input_data: bytes):
    """Decompress a PRS-compressed data chunk."""

    input_signature = input_data[0:4]
    compressed_length = struct.unpack("<I", input_data[12:16])[0]
    compressed_data_array = create_string_buffer(input_data[16:16 + compressed_length])
    decompressed_length = struct.unpack("<I", input_data[8:12])[0]
    decompressed_data_array = create_string_buffer(decompressed_length)

    result = lib.prs_decompress(
        compressed_data_array,
        compressed_length,
        decompressed_data_array,
        decompressed_length,
    )

    if result == 0:
        decompressed_data = bytearray(
            string_at(decompressed_data_array, decompressed_length)
        )

        # The header of the output includes the padded length, input length, and unpadded length.
        output_data = bytearray(input_signature)
        output_data.extend(struct.pack("<I", decompressed_length))
        output_data.extend(decompressed_data)
        return output_data
    else:
        raise PRSError("PRS decompression failed.")


def main():
    if len(sys.argv) >= 4 and sys.argv[1] in ["-c","-d"]:
        with open(sys.argv[2], "rb") as f:
            input_data = f.read()

        try:
            if sys.argv[1] == "-c":
                output = compress(input_data)
            elif sys.argv[1] == "-d":
                output = decompress(input_data)
        except PRSError as e:
            print(e)
            exit(1)

        with open(sys.argv[3], "wb") as f:
            f.write(output)
            print(f"Wrote {len(output)} bytes.")
            print("Finished in", time.time() - start_time, "seconds.")

    else:
        print("Usage: [-c] [-d] INPUT_FILE OUTPUT_FILE")


if __name__ == "__main__":
    main()
