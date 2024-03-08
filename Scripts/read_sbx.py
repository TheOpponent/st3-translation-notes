# Based on the scripts from http://chief-net.ru/forum/topic.php?forum=2&topic=77&postid=1527319695#1527319695 by ZetpeR xax007@yandex.ru.
#
# This script reads compressed SBX files and uncompressed SBN files in the 'source' subdirectory.
# It outputs CSV files in the 'translate' and 'subroutine' subdirectories, using pipe characters | as delimiters.
#
# Decompressed SBX files are saved in the 'source/sbxu' subdirectory with a SBXU extension.
# These files are required for repacking the translated scripts and recompression to SBX.
#
# Two CSV files are written for each SBX/SBN file, one for the strings and one for the subroutine binary data.

import os
import sys
from io import BytesIO
from shutil import copyfile

from utils import prs
from utils.ascr import ParsingError, read_ascr


def main():
    path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
    source_path = os.path.join(path, "source")
    sbxu_path = os.path.join(source_path, "sbxu")
    translate_path = os.path.join(path, "translate")
    backups_path = os.path.join(path, "backups")
    subroutines_path = os.path.join(path, "subroutines")

    files_written1 = 0
    backup_files_written = 0
    files_written2 = 0
    errors = 0

    if not os.path.exists(source_path):
        os.makedirs(source_path)
        print(f"Place SBX and SBN script files in {source_path}.")
        return

    if not os.path.exists(translate_path):
        os.makedirs(translate_path)
    if not os.path.exists(backups_path):
        os.makedirs(backups_path)
    if not os.path.exists(subroutines_path):
        os.makedirs(subroutines_path)

    for file in [
        i for i in os.listdir(source_path) if i.lower().endswith((".sbx", ".sbn"))
    ]:
        # If a CSV for the file already exists, do not process.
        if os.path.exists(os.path.join(translate_path, file + ".csv")):
            print(
                f"{os.path.join(translate_path, file + '.csv')} already exists; not overwriting."
            )
            continue

        with open(os.path.join(source_path, file), "rb") as f:
            # Read files in working directory. SBX files must be decompressed first.
            # After decompressing the SBX file, save it in the source subdirectory for later repacking.
            if file.lower().endswith((".sbx")):
                if not os.path.exists(sbxu_path):
                    os.makedirs(sbxu_path)
                input_data = prs.decompress(f.read())
                with open(
                    os.path.join(sbxu_path, os.path.splitext(file)[0]) + ".SBXU", "wb"
                ) as uncompressed_file:
                    uncompressed_file.write(input_data)
                    print(f"Wrote uncompressed SBX file to {uncompressed_file.name}.")

                input_data = BytesIO(input_data)

            elif file.lower().endswith((".sbn")):
                input_data = f
            else:
                continue

            try:
                strings, subroutines = read_ascr(input_data, file)
            except ParsingError as e:
                print(f"Error: {f}: {e}")
                errors += 1
                input_data.close()
                continue

            with open(
                os.path.join(translate_path, file + ".csv"), "w", encoding="utf-8"
            ) as output_file:
                for i in strings:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                files_written1 += 1

            # Create backup copies of the script CSV files, but do not overwrite existing copies.
            if not os.path.exists(os.path.join(backups_path, file + ".csv")):
                copyfile(
                    os.path.join(translate_path, file + ".csv"),
                    os.path.join(backups_path, file + ".csv"),
                )
                backup_files_written += 1

            with open(
                os.path.join(subroutines_path, file + "_16.csv"), "w", encoding="utf-8"
            ) as output_file:
                for i in subroutines:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                files_written2 += 1

        input_data.close()

    if files_written1 > 0:
        print(f"\n{files_written1} CSV file(s) written to {translate_path}.")

    else:
        print("No files written.")
        return

    if backup_files_written > 0:
        print(f"{files_written1} CSV file(s) written to {backups_path}.")

    if files_written2 > 0:
        print(f"{files_written2} CSV file(s) written to {subroutines_path}.")

    if errors > 0:
        print(f"\n{errors} error(s) during processing. See output for details.")


if __name__ == "__main__":
    main()
