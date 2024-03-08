# This script reads a VMU executable and attempts to decode strings.
# It will output the strings into a CSV file based on the filename of the input file.
#
# The dictionary is based on the character order in the font sheet at 0x4010 in the
# S3vm_*.bin files in SYSLIST.AFS.

import os
import sys


def read_binary(file, offset=0):
    table = {
        b"\x01": "A",
        b"\x02": "B",
        b"\x03": "C",
        b"\x04": "D",
        b"\x05": "E",
        b"\x06": "F",
        b"\x07": "G",
        b"\x08": "H",
        b"\x09": "I",
        b"\x0a": "J",
        b"\x0b": "K",
        b"\x0c": "L",
        b"\x0d": "M",
        b"\x0e": "N",
        b"\x0f": "O",
        b"\x10": "P",
        b"\x11": "Q",
        b"\x12": "R",
        b"\x13": "S",
        b"\x14": "T",
        b"\x15": "U",
        b"\x16": "V",
        b"\x17": "W",
        b"\x18": "X",
        b"\x19": "Y",
        b"\x1a": "Z",
        b"\x1b": "a",
        b"\x1c": "b",
        b"\x1d": "c",
        b"\x1e": "d",
        b"\x1f": "e",
        b"\x20": "f",
        b"\x21": "g",
        b"\x22": "h",
        b"\x23": "i",
        b"\x24": "j",
        b"\x25": "k",
        b"\x26": "l",
        b"\x27": "m",
        b"\x28": "n",
        b"\x29": "o",
        b"\x2a": "p",
        b"\x2b": "q",
        b"\x2c": "r",
        b"\x2d": "s",
        b"\x2e": "t",
        b"\x2f": "u",
        b"\x30": "v",
        b"\x31": "w",
        b"\x32": "x",
        b"\x33": "t",
        b"\x34": "z",
        b"\x35": "0",
        b"\x36": "1",
        b"\x37": "2",
        b"\x38": "3",
        b"\x39": "4",
        b"\x3a": "5",
        b"\x3b": "6",
        b"\x3c": "7",
        b"\x3d": "8",
        b"\x3e": "9",
        b"\x3f": "⓪",
        b"\x40": "①",
        b"\x41": "②",
        b"\x42": "③",
        b"\x43": "④",
        b"\x44": "⑤",
        b"\x45": "⑥",
        b"\x46": "⑦",
        b"\x47": "⑧",
        b"\x48": "⑨",
        b"\x49": "⁰",
        b"\x4a": "¹",
        b"\x4b": "²",
        b"\x4c": "³",
        b"\x4d": "⁴",
        b"\x4e": "⁵",
        b"\x4f": "⁶",
        b"\x50": "⁷",
        b"\x51": "⁸",
        b"\x52": "⁹",
        b"\x53": "㏂",
        b"\x54": "㏘",
        b"\x55": ":",
        b"\x56": "!",
        b"\x57": "、",
        b"\x58": "。",
        b"\x59": "？",
        b"\x5a": "⁉",
        b"\x5b": "…",
        b"\x5c": "ー",
        b"\x5d": "~",
        b"\x5e": "゛",
        b"\x5f": "゜",
        b"\x60": "あ",
        b"\x61": "ぁ",
        b"\x62": "い",
        b"\x63": "ぃ",
        b"\x64": "う",
        b"\x65": "ぅ",
        b"\x66": "え",
        b"\x67": "ぇ",
        b"\x68": "お",
        b"\x69": "ぉ",
        b"\x6a": "か",
        b"\x6b": "き",
        b"\x6c": "く",
        b"\x6d": "け",
        b"\x6e": "こ",
        b"\x6a\x5e": "が",
        b"\x6b\x5e": "ぎ",
        b"\x6c\x5e": "ぐ",
        b"\x6d\x5e": "げ",
        b"\x6e\x5e": "ご",
        b"\x6f": "さ",
        b"\x70": "し",
        b"\x71": "す",
        b"\x72": "せ",
        b"\x73": "そ",
        b"\x6f\x5e": "ざ",
        b"\x70\x5e": "じ",
        b"\x71\x5e": "ず",
        b"\x72\x5e": "ぜ",
        b"\x73\x5e": "ぞ",
        b"\x74": "た",
        b"\x75": "ち",
        b"\x76": "つ",
        b"\x77": "っ",
        b"\x78": "て",
        b"\x79": "と",
        b"\x74\x5e": "だ",
        b"\x75\x5e": "ぢ",
        b"\x76\x5e": "づ",
        b"\x78\x5e": "で",
        b"\x79\x5e": "ど",
        b"\x7a": "な",
        b"\x7b": "に",
        b"\x7c": "ぬ",
        b"\x7d": "ね",
        b"\x7e": "の",
        b"\x7f": "は",
        b"\x80": "ひ",
        b"\x81": "ふ",
        b"\x82": "へ",
        b"\x83": "ほ",
        b"\x7f\x5e": "ば",
        b"\x80\x5e": "び",
        b"\x81\x5e": "ぶ",
        b"\x82\x5e": "べ",
        b"\x83\x5e": "ぼ",
        b"\x7f\x5f": "ぱ",
        b"\x80\x5f": "ぴ",
        b"\x81\x5f": "ぷ",
        b"\x82\x5f": "ぺ",
        b"\x83\x5f": "ぽ",
        b"\x84": "ま",
        b"\x85": "み",
        b"\x86": "む",
        b"\x87": "め",
        b"\x88": "も",
        b"\x89": "や",
        b"\x8a": "ゃ",
        b"\x8b": "ゆ",
        b"\x8c": "ゅ",
        b"\x8d": "よ",
        b"\x8e": "ょ",
        b"\x8f": "ら",
        b"\x90": "り",
        b"\x91": "る",
        b"\x92": "れ",
        b"\x93": "ろ",
        b"\x94": "わ",
        b"\x95": "を",
        b"\x96": "ん",
        b"\x97": "ア",
        b"\x98": "ァ",
        b"\x99": "イ",
        b"\x9a": "ィ",
        b"\x9b": "ウ",
        b"\x9c": "ゥ",
        b"\x9d": "エ",
        b"\x9e": "ェ",
        b"\x9f": "オ",
        b"\xa0": "ォ",
        b"\xa1": "カ",
        b"\xa2": "キ",
        b"\xa3": "ク",
        b"\xa4": "ケ",
        b"\xa5": "コ",
        b"\xa1\x5e": "ガ",
        b"\xa2\x5e": "ギ",
        b"\xa3\x5e": "グ",
        b"\xa4\x5e": "ゲ",
        b"\xa5\x5e": "ゴ",
        b"\xa6": "サ",
        b"\xa7": "シ",
        b"\xa8": "ス",
        b"\xa9": "セ",
        b"\xaa": "ソ",
        b"\xa6\x5e": "ザ",
        b"\xa7\x5e": "ジ",
        b"\xa8\x5e": "ズ",
        b"\xa9\x5e": "ゼ",
        b"\xaa\x5e": "ゾ",
        b"\xab": "タ",
        b"\xac": "チ",
        b"\xad": "ツ",
        b"\xae": "ッ",
        b"\xaf": "テ",
        b"\xb0": "ト",
        b"\xab\x5e": "ダ",
        b"\xac\x5e": "ヂ",
        b"\xad\x5e": "ヅ",
        b"\xaf\x5e": "デ",
        b"\xb0\x5e": "ド",
        b"\xb1": "ナ",
        b"\xb2": "ニ",
        b"\xb3": "ヌ",
        b"\xb4": "ネ",
        b"\xb5": "ニ",
        b"\xb6": "ハ",
        b"\xb7": "ヒ",
        b"\xb8": "フ",
        b"\xb9": "ヘ",
        b"\xba": "ホ",
        b"\xb6\x5e": "バ",
        b"\xb7\x5e": "ビ",
        b"\xb8\x5e": "ブ",
        b"\xb9\x5e": "ベ",
        b"\xba\x5e": "ボ",
        b"\xb6\x5f": "パ",
        b"\xb7\x5f": "ピ",
        b"\xb8\x5f": "プ",
        b"\xb9\x5f": "ペ",
        b"\xba\x5f": "ポ",
        b"\xbb": "マ",
        b"\xbc": "ミ",
        b"\xbd": "ム",
        b"\xbe": "メ",
        b"\xbf": "モ",
        b"\xc0": "ヤ",
        b"\xc1": "ャ",
        b"\xc2": "ユ",
        b"\xc3": "ュ",
        b"\xc4": "ヨ",
        b"\xc5": "ョ",
        b"\xc6": "ラ",
        b"\xc7": "リ",
        b"\xc8": "ル",
        b"\xc9": "レ",
        b"\xca": "ロ",
        b"\xcb": "ワ",
        b"\xcc": "ヲ",
        b"\xcd": "ン",
        b"\xd3": "♥",
        b"\xd4": "♡",
        b"\xd5": "‼",
        b"\xfe": "　",
    }

    file.seek(offset)
    position = hex(file.tell())
    string = ""
    string_count = 0
    output = ""

    while True:
        i = file.read(1)
        if i == b"":
            break

        # TODO: The area for strings is preceded by eight 00 bytes.
        elif i == b"\x00":
            position = hex(file.tell())
            string = ""
            continue

        elif i == b"\xff" and len(string):
            output += f"{position}|{string}\n"
            position = hex(file.tell())
            string = ""
            string_count += 1

        # Byte 0xfc is a control code that reads the next two bytes and forms a
        # voiced kana character by writing the on pixels of the second byte 
        # over the first.
        elif i == b"\xfc":
            i = file.read(2)
            string += table.get(i, "")

        else:
            string += table.get(i, "")

    filename = os.path.split(sys.argv[1])[1].split(".")[0] + ".csv"
    with open(filename, "w", encoding="utf8") as file:
        file.write(output)
        print(f"Wrote {string_count} strings to {filename}.")


def main():
    with open(sys.argv[1], "rb") as file:
        if len(sys.argv) > 2:
            read_binary(file, sys.argv[2])
        elif len(sys.argv) == 2:
            read_binary(file)
        else:
            print("Specify input file and optional offset.")


if __name__ == "__main__":
    main()
