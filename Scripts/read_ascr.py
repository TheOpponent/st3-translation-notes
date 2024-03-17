# Based on the scripts from http://chief-net.ru/forum/topic.php?forum=2&topic=77&postid=1527319695#1527319695 by ZetpeR xax007@yandex.ru.
#
# When run without arguments, this script reads compressed SBX files,  
# uncompressed SBN, and ASCR files in the 'source' subdirectory, recursively.
# Otherwise, SBX, SBN, and ASCR files are expected as arguments.
# It outputs CSV files in the 'translate' and 'subroutine' subdirectories, 
# using pipe characters | as delimiters.
#
# Decompressed SBX files are saved in the 'source/sbxu' subdirectory with a SBXU extension.
# These files are required for repacking the translated scripts and recompression to SBX.
#
# Two CSV files are written for each SBX/SBN file, one for the strings and one for the subroutine binary data.

import os
import sys
from io import BytesIO
from shutil import copyfile

from utils.prs import decompress, PRSError
from utils.ascr import ASCRError, read_ascr


def main():
    path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
    source_path = os.path.join(path, "source")
    sbxu_path = os.path.join(source_path, "sbxu")
    translate_path = os.path.join(path, "translate")
    backups_path = os.path.join(path, "backups")
    subroutines_path = os.path.join(path, "subroutines")

    translate_csv_files_written = 0
    backup_files_written = 0
    subroutine_files_written = 0
    warnings = 0
    errors = 0

    os.makedirs(source_path, exist_ok=True)

    if len(sys.argv) > 1:
        file_list = sys.argv[1:]
    else:
        file_list = [
            i for i in os.listdir(source_path) if i.lower().endswith((".sbx", ".sbn"))
        ]
        if len(file_list) == 0:
            print(f"Place SBX, SBN, and ASCR script files in {source_path}.")
            return

    os.makedirs(translate_path, exist_ok=True)
    os.makedirs(backups_path, exist_ok=True)
    os.makedirs(subroutines_path, exist_ok=True)

    for file in file_list:
        translate_csv_file = os.path.join(translate_path, file + ".csv")

        # If a CSV for the file already exists, do not process.
        if os.path.exists(translate_csv_file):
            print(f"[Warning] {translate_csv_file} already exists; not overwriting.")
            warnings += 1
            continue

        with open(os.path.join(source_path, file), "rb") as f:
            # Read files in working directory. SBX files must be decompressed first.
            # After decompressing the SBX file, save it in the source subdirectory for later repacking.
            if file.lower().endswith((".sbx")):
                os.makedirs(sbxu_path, exist_ok=True)

                sbxu_file = os.path.join(sbxu_path, os.path.splitext(file)[0]) + ".SBXU"
                if os.path.exists(sbxu_file):
                    print(f"[Warning] {sbxu_file} already exists; not overwriting.")
                    warnings += 1
                    continue

                try:
                    input_data = decompress(f.read())
                except PRSError as e:
                    print(f"[Error] {file}: e")
                    errors += 1
                    continue

                with open(sbxu_file, "wb") as sbxu_out_file:
                    sbxu_out_file.write(input_data)
                    print(f"{file}: Wrote uncompressed SBX file to {sbxu_file}.")

                input_data = BytesIO(input_data)

            elif file.lower().endswith((".sbn")):
                input_data = f
            else:
                continue

            try:
                strings, subroutines = read_ascr(input_data, file)
            except ASCRError as e:
                print(f"[Error] {f}: {e}")
                errors += 1
                input_data.close()
                continue

            with open(translate_csv_file, "w", encoding="utf-8") as output_file:
                for i in strings:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                translate_csv_files_written += 1

            backup_csv_file = os.path.join(backups_path, file + ".csv")
            # Create backup copies of the script CSV files, but do not overwrite existing copies.
            if not os.path.exists(backup_csv_file):
                copyfile(
                    translate_csv_file,
                    backup_csv_file,
                )
                backup_files_written += 1

            subroutine_csv_file = os.path.join(subroutines_path, file + "_16.csv")
            with open(subroutine_csv_file, "w", encoding="utf-8") as output_file:
                for i in subroutines:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                subroutine_files_written += 1

        input_data.close()

    if translate_csv_files_written > 0:
        print(
            f"\n{translate_csv_files_written} CSV file(s) written to {translate_path}."
        )

    else:
        print("No files written.")

    if backup_files_written > 0:
        print(f"{backup_files_written} CSV file(s) written to {backups_path}.")

    if subroutine_files_written > 0:
        print(f"{subroutine_files_written} CSV file(s) written to {subroutines_path}.")

    if errors > 0 or warnings > 0:
        print(
            f"\n{errors} error(s) and {warnings} warning(s) raised. See output for details."
        )


if __name__ == "__main__":
    main()
