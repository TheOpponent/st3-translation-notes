# Helper functions for translation scripts.

import struct
import re

def ascii_to_sjis(input_str,break_lines=True,offset=0,*args,**kwargs):
    """Converts a string of ASCII characters to 
    byte-swapped Shift-JIS and null-terminate it.
    
    Set break_lines to false to bypass the linebreak function.
    Use this for non-dialogue text, such as menus.

    Set the offset argument to the number of tiles to skip
    from the below table. This can be used to redefine
    otherwise unused tiles for custom glyphs, such as an 
    alternate font for areas outside of the dialogue box
    with a different font size.
    
    The keyword arguments length_limit, last_row_length_limit, and 
    row_limit can be passed to linebreak function."""

    table = {'A': 0x8260,
    'B': 0x8261,
    'C': 0x8262,
    'D': 0x8263,
    'E': 0x8264,
    'F': 0x8265,
    'G': 0x8266,
    'H': 0x8267,
    'I': 0x8268,
    'J': 0x8269,
    'K': 0x826a,
    'L': 0x826b,
    'M': 0x826c,
    'N': 0x826d,
    'O': 0x826e,
    'P': 0x826f,
    'Q': 0x8270,
    'R': 0x8271,
    'S': 0x8272,
    'T': 0x8273,
    'U': 0x8274,
    'V': 0x8275,
    'W': 0x8276,
    'X': 0x8277,
    'Y': 0x8278,
    'Z': 0x8279,
    'a': 0x827a,
    'b': 0x827b,
    'c': 0x827c,
    'd': 0x827d,
    'e': 0x827e,
    'f': 0x8280,
    'g': 0x8287,
    'h': 0x8288,
    'i': 0x8289,
    'j': 0x828a,
    'k': 0x828b,
    'l': 0x828c,
    'm': 0x828d,
    'n': 0x828e,
    'o': 0x828f,
    'p': 0x8290,
    'q': 0x8291,
    'r': 0x8292,
    's': 0x8293,
    't': 0x8294,
    'u': 0x8295,
    'v': 0x8296,
    'w': 0x8297,
    'x': 0x8298,
    'y': 0x8299,
    'z': 0x829a,
    'À': 0x829f, # These French accented letters replace hiragana starting at small ぁ. 
    'Â': 0x82a0,
    'Ä': 0x82a1,
    'Æ': 0x82a2,
    'Ç': 0x82a3,
    'È': 0x82a4,
    'É': 0x82a5,
    'Ê': 0x82a6,
    'Ë': 0x82a7,
    'Î': 0x82a8,
    'Ï': 0x82a9,
    'Ô': 0x82aa,
    'Œ': 0x82ab,
    'Ù': 0x82ac,
    'Û': 0x82ad,
    'Ü': 0x82ae,
    'à': 0x82af,
    'â': 0x82b0,
    'ä': 0x82b1,
    'æ': 0x82b2,
    'ç': 0x82b3,
    'è': 0x82b4,
    'é': 0x82b5,
    'ê': 0x82b6,
    'ë': 0x82b7,
    'î': 0x82b8,
    'ï': 0x82b9,
    'ô': 0x82ba,
    'œ': 0x82bb,
    'ù': 0x82bc,
    'û': 0x82bd,
    'ü': 0x82be,
    ' ': 0x8140,
    '.': 0x8144,
    ',': 0x8143,
    ':': 0x8146,
    ';': 0x8147,
    '?': 0x8148,
    '!': 0x8149,
    '\'': 0x814c, # Apostrophe
    '"': 0x814e,
    '—': 0x815c, # Em dash
    '–': 0x815b, # En dash
    '-': 0x815d, # Dash
    '/': 0x815e,
    '~': 0x8160,
    '‘': 0x8165, # Opening single quotation
    '’': 0x8166, # Closing single quotation
    '“': 0x8167, # Opening double quotation
    '”': 0x8168, # Closing double quotation
    '(': 0x8169,
    ')': 0x816a,
    '[': 0x816d,
    ']': 0x816e,
    '+': 0x817b,
    '×': 0x817e, # Multiplication sign
    '÷': 0x8180, # One value skipped internally for some reason.
    '=': 0x8181,
    '<': 0x8183,
    '>': 0x8184,
    '°': 0x818b,
    '$': 0x8190,
    '%': 0x8193,
    '#': 0x8194,
    '&': 0x8195,
    '*': 0x8196,
    '@': 0x8197,
    '☆': 0x8199,
    '★': 0x819a,
    '0': 0x8240,
    '1': 0x8241,
    '2': 0x8242,
    '3': 0x8243,
    '4': 0x8244,
    '5': 0x8245,
    '6': 0x8246,
    '7': 0x8247,
    '8': 0x8248,
    '9': 0x8249,
    '\\': 0x2f2f,
    '{': None, # Ignore curly brackets as they are used for control codes.
    '}': None}

    if break_lines:
        input_str = linebreak(input_str,line_id=kwargs.get("line_id",None),
                              length_limit=kwargs.get("length_limit",37),
                              last_row_length_limit=kwargs.get("last_row_length_limit",37),
                              row_limit=kwargs.get("row_limit",3))[0]

    input_str = input_str.strip()
    
    output = bytearray()

    i = 0
    while i < len(input_str):
        if input_str[i] != "{":
            output += struct.pack(">H",table[input_str[i]] + offset)
        else:
            # If { is encountered, parse as a control code and paste characters directly rather than translating them.
            while input_str[i+1] != "}": # Check next character and stop pasting when } is next.
                i += 1
                output += bytes(input_str[i],"shift_jis_2004")
            i += 1 # Skip } character.
            
        i += 1

    output += b'\x00' # Terminate string.

    return output


def linebreak(input_str,line_id=None,length_limit=37,last_row_length_limit=37,row_limit=3):
    """Break lines according to length_limit. Default length is 37.
    A backslash character is inserted at line breaks, 
    which is translated in ascii_to_sjis to byte 2F2F.
    
    Control code sequences are not counted in word length,
    assuming they consist of {} containing only letters, numbers,
    commas, and @. Because of the need for non-printable control 
    codes, the standard text wrapping functions cannot be used.
    
    Returns a tuple containing the output string and the number of 
    lines.
    """
    
    output = ""
    current_length = 0
    lines = 1

    # Split input string into an enumerated list of each word. Forced line breaks are split into their own word.
    input_str = list(enumerate(input_str.replace(r"\n"," \\ ").replace("//"," \\ ").split(" "),1))

    for i in input_str:
        word_length = len(i[1]) - sum([len(p) for p in re.findall("{[a-zA-Z0-9,@!=]+}",i[1])]) # Do not count control code sequences in word length.

        # Insert word that is not a forced line break.
        if i[1] != "\\":
            if current_length + word_length + 1 <= length_limit:
                output += i[1]
                current_length += word_length + 1
            else:
                output = output.rstrip() + "\\" + i[1]
                lines += 1
                current_length = word_length
            # Add a space if there are more words remaining, or break otherwise.
            if i[0] < len(input_str):
                output += " "
            else:
                break
        else:
            output = output.rstrip() + "\\" # Remove space inserted by previous word.
            lines += 1
            current_length = 0

    if lines == row_limit and current_length > last_row_length_limit:
        if line_id is not None:
            print(f"WARNING: Last row limit overflow at line {line_id}: {output}")
        else:
            print(f"WARNING: Last row limit overflow: {output}")

    if lines > row_limit:
        if line_id is not None:
            print(f"WARNING: Line break overflow at line {line_id}: {output}")
        else:
            print(f"WARNING: Line break overflow: {output}")

    return (output,lines)


def swap_bytes(value):
    """Convert hex string to little-endian bytes."""

    str = hex(value)[2:].zfill(8)

    return str[6:8] + str[4:6] + str[2:4] + str[0:2]    


def main():

    while True:
        input_str = input("String (Input blank string to exit): ")
        if input_str != "":
            print(ascii_to_sjis(input_str).hex(),"\n")
        else:
            break
        

if __name__ == "__main__":
    main()