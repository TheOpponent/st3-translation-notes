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

    table = {'A': 33376,
    'B': 33377,
    'C': 33378,
    'D': 33379,
    'E': 33380,
    'F': 33381,
    'G': 33382,
    'H': 33383,
    'I': 33384,
    'J': 33385,
    'K': 33386,
    'L': 33387,
    'M': 33388,
    'N': 33389,
    'O': 33390,
    'P': 33391,
    'Q': 33392,
    'R': 33393,
    'S': 33394,
    'T': 33395,
    'U': 33396,
    'V': 33397,
    'W': 33398,
    'X': 33399,
    'Y': 33400,
    'Z': 33401,
    'a': 33402,
    'b': 33403,
    'c': 33404,
    'd': 33405,
    'e': 33406,
    'f': 33408,
    'g': 33415,
    'h': 33416,
    'i': 33417,
    'j': 33418,
    'k': 33419,
    'l': 33420,
    'm': 33421,
    'n': 33422,
    'o': 33423,
    'p': 33424,
    'q': 33425,
    'r': 33426,
    's': 33427,
    't': 33428,
    'u': 33429,
    'v': 33430,
    'w': 33431,
    'x': 33432,
    'y': 33433,
    'z': 33434,
    ' ': 33088,
    '.': 33092,
    ',': 33091,
    ':': 33094,
    ';': 33095,
    '?': 33096,
    '!': 33097,
    '\'': 33100, # Apostrophe
    '"': 33102,
    '—': 33116, # Em dash
    '–': 33115, # En dash
    '-': 33117, # Dash
    '/': 33118,
    '~': 33120,
    '‘': 33125, # Opening single quotation
    '’': 33126, # Closing single quotation
    '“': 33127, # Opening double quotation
    '”': 33128, # Closing double quotation
    '(': 33129,
    ')': 33130,
    '[': 33133,
    ']': 33134,
    '+': 33147,
    '×': 33150, # Multiplication sign
    '÷': 33152, # One value skipped internally for some reason.
    '=': 33153,
    '<': 33155,
    '>': 33156,
    '°': 33163,
    '$': 33168,
    '%': 33171,
    '#': 33172,
    '&': 33173,
    '*': 33174,
    '@': 33175,
    '☆': 33177,
    '★': 33178,
    '0': 33344,
    '1': 33345,
    '2': 33346,
    '3': 33347,
    '4': 33348,
    '5': 33349,
    '6': 33350,
    '7': 33351,
    '8': 33352,
    '9': 33353,
    '\\': 12079, # 2F2F
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
    """Break lines according to length_limit. Default length is 30.
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


if __name__ == "__main__":
    input_str = input("String: ")
    print(ascii_to_sjis(input_str).hex())