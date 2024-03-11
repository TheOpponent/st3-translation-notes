# This script separates ESM files into files containing each data region.
# When run without arguments, the subdirectory 'esm' will be checked for ESM files.
# Otherwise, ESM files are expected as arguments.
#
# Due to the large number of chunks that can be extracted from a single ESM file,
# the script will create an 'esm/extracted' subdirectory containing the files written.
# A text file will also be written with statistics on the chunks extracted.
#
# Each output file can be edited individually and then concatenated.

import os
import struct
import sys


def main():
    path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
    source_path = os.path.join(path, "esm")
    extracted_path = os.path.join(source_path, "extracted")

    os.makedirs(source_path, exist_ok=True)

    if len(sys.argv) > 1:
        inputs = sys.argv[1:]
    else:
        inputs = [i for i in os.listdir(source_path) if i.lower().endswith((".esm"))]
        if len(inputs) == 0:
            print(f"Place ESM files in {source_path}.")
            return

    os.makedirs(extracted_path, exist_ok=True)

    for input_file in inputs:
        esm_stats = []
        chunk_number = 0

        with open(os.path.join(source_path, input_file), "rb") as esm_file:
            while True:
                buffer = bytearray()
                header = esm_file.read(4)
                size_info = esm_file.read(4)

                if not header or not size_info:
                    break

                buffer = header + size_info
                size = struct.unpack("<I", size_info)[0]

                if size > 0:
                    bytes_remaining = size
                    while bytes_remaining > 0:
                        chunk = esm_file.read(4)
                        bytes_remaining -= 4

                        if not chunk:
                            break

                        buffer += chunk

                output_filename = input_file + "." + str(chunk_number).zfill(3)
                output_file = os.path.join(extracted_path, output_filename)
                with open(output_file, "wb") as file:
                    file.write(buffer)
                    print(
                        f"{output_filename}: {header.decode()} chunk at {hex(esm_file.tell())}. Length: {len(buffer)} bytes."
                    )

                esm_stats.append(
                    (chunk_number, hex(esm_file.tell()), header.decode(), len(buffer))
                )

                if len(buffer) < size:
                    break

                chunk_number += 1

        print(f"{input_file}: Wrote {str(chunk_number + 1)} files.")

        # Write stats text file.
        stats_file_name = os.path.join(extracted_path, input_file + ".txt")
        with open(stats_file_name, "w") as file:
            file.write("Chunk | Offset     | Type | Length\n")
            file.write("----------------------------------\n")
            for i in esm_stats:
                file.write("{:<5} | {:<10} | {:<4} | {:<6}\n".format(*i))

            print(f"Stats report written to {file.name}.\n")


if __name__ == "__main__":
    main()
