# Temporary workaround using calls to subprocesses instead of the library

import os
import random
import string
import struct
import subprocess
import sys
import time

COMPRESS_PROGRAM = ".\\lib\\compress.exe"
DECOMPRESS_PROGRAM = ".\\lib\\decompress.exe"


class PRSError(Exception):
    pass


def random_filename(length) -> str:
    characters = string.ascii_letters + string.digits
    return "~" + "".join(random.choice(characters) for _ in range(length)) + ".bin"


def compress(data: bytearray) -> bytes:
    """Pass a bytearray containing the relevant header to a program
    that compresses data using PRS, and adds wrapping for Sakura
    Taisen 3 to the output. Currently requires writing and reading
    temporary files.

    Returns a bytes object containing wrapped PRS-compressed data."""

    input_signature = data[0:4]
    input_length = struct.unpack("<I", data[4:8])[0]
    input_data = data[8:]
    output_data = bytearray(input_signature)

    tempin_filename = random_filename(7)
    tempout_filename = random_filename(7)

    with open(tempin_filename, "wb") as file:
        file.write(input_data)

    try:
        compressor = subprocess.Popen(
            [COMPRESS_PROGRAM, tempin_filename, tempout_filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = compressor.communicate()
        if compressor.returncode != 0:
            raise PRSError(err.decode())
    except subprocess.SubprocessError as e:
        raise PRSError(e)

    with open(tempout_filename, "rb") as file:
        output_temp_data = bytearray(file.read())

    output_length = len(output_temp_data)
    if (padding := output_length % 4) != 0:
        output_temp_data.extend(b"\x00" * (4 - padding))

    # Padded length includes CPRS\x00\x00\x00\x00 footer.
    padded_length = output_length + padding + 8

    output_data.extend(struct.pack("<I", padded_length))
    output_data.extend(struct.pack("<I", input_length))
    output_data.extend(struct.pack("<I", output_length))
    output_data.extend(output_temp_data)
    output_data.extend(b"CPRS\x00\x00\x00\x00EOFC\x00\x00\x00\x00")

    os.unlink(tempin_filename)
    os.unlink(tempout_filename)

    return output_data


def decompress(data: bytearray) -> bytes:
    """Pass a bytearray of PRS-compressed data with wrapping for Sakura
    Taisen 3 to a program that decompresses PRS data. The wrapping is
    stripped before passed to the program.

    Returns a bytes object with decompressed data."""

    input_signature = data[0:4]
    input_padded_length = struct.unpack("<I", data[4:8])[0]
    input_uncompressed_length = struct.unpack("<I", data[8:12])[0]
    input_compressed_length = struct.unpack("<I", data[12:16])[0]
    input_data = data[16:]
    input_data_length = len(input_data) - 8

    if input_data_length != input_padded_length:
        raise PRSError(
            f"Padded data length in header is incorrect (Expected {input_padded_length}, got {input_data_length})"
        )

    output_data = bytearray(input_signature)

    tempin_filename = random_filename(7)
    tempout_filename = random_filename(7)

    with open(tempin_filename, "wb") as file:
        file.write(input_data)

    try:
        decompressor = subprocess.Popen(
            [DECOMPRESS_PROGRAM, tempin_filename, tempout_filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = decompressor.communicate()
        if decompressor.returncode != 0:
            raise PRSError(err.decode())
    except subprocess.SubprocessError as e:
        raise PRSError(e)

    with open(tempout_filename, "rb") as file:
        output_temp_data = bytearray(file.read())

    output_data.extend(struct.pack("<I", input_uncompressed_length))
    output_data.extend(output_temp_data)

    os.unlink(tempin_filename)
    os.unlink(tempout_filename)

    return output_data


def main():
    start_time = time.time()

    if len(sys.argv) >= 4:
        with open(sys.argv[2], "rb") as input_file:
            input_data = input_file.read()
            if len(input_data) == 0:
                print(f"{input_file}: Unable to read all bytes.")

        if sys.argv[1] == "-c":
            output_data = compress(input_data)

        elif sys.argv[1] == "-d":
            output_data = decompress(input_data)

        if output_data:
            with open(sys.argv[3], "wb") as output_file:
                output_file.write(output_data)
                print(f"Wrote {len(output_data)} bytes.")
                return

        print("Finished in ", time.time() - start_time, "seconds.")

    else:
        print("Usage: [-c] [-d] INPUT_FILE OUTPUT_FILE")


if __name__ == "__main__":
    main()
