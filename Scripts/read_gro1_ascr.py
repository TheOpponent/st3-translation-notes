# This script reads files that contain one GRO1 chunk with ASCR chunks provided as arguments.
# Subdirectories named for the input files are created in the 'source', 'translate', 'backup', and
# 'subroutines' subdirectories.
#
# ASCR files are written in the 'source' subdirectory containing each ASCR chunk.
# These files are required for repacking the translated scripts.
#
# CSV files are written in the 'translate' and 'subroutine' subdirectories, using pipe characters | as delimiters.
#
# Subdirectories named for the input files are created in the 'translate' and 'subroutines' subdirectories.
# CSV files are written into these subdirectories containing strings and the subroutine binary data.

import os
import struct
import sys
from io import BytesIO
from shutil import copyfile

from utils.ascr import ParsingError, read_ascr


def main():
    if len(sys.argv) == 1:
        print("Specify input files from read_esm.py containing ASCR chunks.")
        return

    path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
    source_path = os.path.join(path, "source")
    translate_path = os.path.join(path, "translate")
    backups_path = os.path.join(path, "backups")
    subroutines_path = os.path.join(path, "subroutines")

    total_ascr_raw_files_written = 0
    total_translate_csv_files_written = 0
    total_backup_files_written = 0
    total_subroutine_files_written = 0
    errors = 0
    warnings = 0

    os.makedirs(source_path, exist_ok=True)
    os.makedirs(translate_path, exist_ok=True)
    os.makedirs(backups_path, exist_ok=True)
    os.makedirs(subroutines_path, exist_ok=True)

    for input_file in [i for i in sys.argv[1:]]:
        input_basename = os.path.basename(input_file)
        ascr_raw_path = os.path.join(source_path, input_basename)
        translate_subpath = os.path.join(translate_path, input_basename)
        backups_subpath = os.path.join(backups_path, input_basename)
        subroutines_subpath = os.path.join(subroutines_path, input_basename)

        ascr_raw_files_written = 0
        translate_csv_files_written = 0
        backup_files_written = 0
        subroutine_files_written = 0

        os.makedirs(ascr_raw_path, exist_ok=True)
        os.makedirs(translate_subpath, exist_ok=True)
        os.makedirs(backups_subpath, exist_ok=True)
        os.makedirs(subroutines_subpath, exist_ok=True)

        with open(input_file, "rb") as gro1_file:
            ascr_chunks = []

            _header = gro1_file.read(4)
            _size_info = gro1_file.read(4)
            _pointer1 = gro1_file.read(4)
            ascr_count = struct.unpack("<I", gro1_file.read(4))[0]

            gro1_file.seek(32)
            _pointer2 = gro1_file.read(4)

            gro1_file.seek(48)

            ascr_offsets = []
            for _ in range(ascr_count):
                ascr_offsets.append(gro1_file.read(4))

            print(f"{input_file}: {ascr_count} ASCR chunk(s) in this file.")

            for i in range(len(ascr_offsets)):
                current_offset = struct.unpack("<I", ascr_offsets[i])[0]
                # Skip blank offsets, but write an empty file for them.
                if current_offset == 0:
                    ascr_chunks.append(b"")
                    continue

                # Get next offset that is not 0.
                next = 1
                while True:
                    if i + next < ascr_count:
                        next_offset = struct.unpack("<I", ascr_offsets[i + next])[0]
                        if next_offset > 0:
                            chunk_size = next_offset - current_offset
                            break
                        else:
                            next += 1
                    else:
                        chunk_size = -1
                        break

                # Add 8 to each offset.
                gro1_file.seek(current_offset + 8)
                chunk = gro1_file.read(chunk_size)
                ascr_chunks.append(chunk)

            for i in enumerate(ascr_chunks):
                ascr_raw_filename = (
                    f"{os.path.basename(input_file)}.{str(i[0]).zfill(3)}.ascr"
                )
                ascr_raw_file = os.path.join(ascr_raw_path, ascr_raw_filename)

                if os.path.exists(ascr_raw_file):
                    print(
                        f"{input_file}: {ascr_raw_filename} for chunk {i[0]} already exists; skipping this chunk."
                    )
                    continue

                with open(ascr_raw_file, "wb") as file:
                    file.write(i[1])
                    ascr_raw_files_written += 1
                    total_ascr_raw_files_written += 1

                csv_name = ascr_raw_filename + ".csv"
                translate_csv_file = os.path.join(translate_subpath, csv_name)
                backup_csv_file = os.path.join(backups_subpath, csv_name)
                subroutine_csv_name = ascr_raw_filename + "_16.csv"
                subroutine_file = os.path.join(subroutines_subpath, subroutine_csv_name)

                if i[1] != b"":
                    ascr_data = BytesIO(i[1])
                    try:
                        output_text, output_subroutines = read_ascr(
                            ascr_data,
                            filename=f"{input_file} chunk {str(i[0]).zfill(3)}",
                        )
                    except ParsingError as e:
                        print(f"Error: {e}")
                        errors += 1
                        continue

                    if os.path.exists(translate_csv_file):
                        print(f"Warning: {translate_csv_file} already exists; not overwriting.")
                        warnings += 1
                        continue

                    with open(
                        translate_csv_file,
                        "w",
                        encoding="utf8",
                    ) as file:
                        for j in output_text:
                            output = "|".join(j)
                            file.write(output + "\n")
                        translate_csv_files_written += 1
                        total_translate_csv_files_written += 1

                    with open(
                        subroutine_file,
                        "w",
                        encoding="utf8",
                    ) as file:
                        for j in output_subroutines:
                            output = "|".join(j)
                            file.write(output + "\n")
                        subroutine_files_written += 1
                        total_subroutine_files_written += 1
                else:
                    with open(translate_csv_file, "wb") as file:
                        file.write(b"")
                        translate_csv_files_written += 1
                        total_translate_csv_files_written += 1

                    with open(subroutine_file, "wb") as file:
                        file.write(b"")
                        subroutine_files_written += 1
                        total_subroutine_files_written += 1

                    print(f"{input_file} chunk {i[0]} is blank.")

                if not os.path.exists(backup_csv_file):
                    copyfile(
                        translate_csv_file,
                        backup_csv_file,
                    )
                backup_files_written += 1
                total_backup_files_written += 1

            if ascr_raw_files_written > 0:
                print(
                    f"\n{input_file}:\n{ascr_raw_files_written} ASCR file(s) written to {ascr_raw_path}."
                )

            else:
                print(f"Notice: {input_file}: No files written.")
                return

            if translate_csv_files_written > 0:
                print(
                    f"{translate_csv_files_written} text CSV file(s) written to {translate_subpath}."
                )

            if backup_files_written > 0:
                print(
                    f"{backup_files_written} backup CSV file(s) written to {backups_subpath}."
                )

            if subroutine_files_written > 0:
                print(
                    f"{subroutine_files_written} subroutines CSV file(s) written to {subroutines_subpath}."
                )

    if total_ascr_raw_files_written > 0:
        print(f"\n{total_ascr_raw_files_written} ASCR file(s) written.")

    else:
        print("Notice: No files written.")
        return

    if total_translate_csv_files_written > 0:
        print(f"{total_translate_csv_files_written} text CSV file(s) written.")

    if total_backup_files_written > 0:
        print(f"{total_backup_files_written} backup CSV file(s) written.")

    if total_subroutine_files_written > 0:
        print(f"{total_subroutine_files_written} subroutines CSV file(s) written.")

    if errors > 0 or warnings > 0:
        print(f"\n{errors} error(s) and {warnings} warning(s) raised. See output for details.")


if __name__ == "__main__":
    main()
