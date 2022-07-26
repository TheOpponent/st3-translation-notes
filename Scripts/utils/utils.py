# Helper functions for translation scripts.

import struct
import re

table = {'A': (0x8260,12),
'B': (0x8261,12),
'C': (0x8262,12),
'D': (0x8263,12),
'E': (0x8264,12),
'F': (0x8265,12),
'G': (0x8266,12),
'H': (0x8267,12),
'I': (0x8268,6),
'J': (0x8269,12),
'K': (0x826a,12),
'L': (0x826b,12),
'M': (0x826c,12),
'N': (0x826d,12),
'O': (0x826e,12),
'P': (0x826f,12),
'Q': (0x8270,12),
'R': (0x8271,12),
'S': (0x8272,12),
'T': (0x8273,12),
'U': (0x8274,12),
'V': (0x8275,12),
'W': (0x8276,12),
'X': (0x8277,12),
'Y': (0x8278,12),
'Z': (0x8279,12),
'a': (0x827a,12),
'b': (0x827b,12),
'c': (0x827c,12),
'd': (0x827d,12),
'e': (0x827e,12),
'f': (0x8280,11),
'g': (0x8287,12),
'h': (0x8288,12),
'i': (0x8289,5),
'j': (0x828a,8),
'k': (0x828b,12),
'l': (0x828c,5),
'm': (0x828d,12),
'n': (0x828e,12),
'o': (0x828f,12),
'p': (0x8290,12),
'q': (0x8291,12),
'r': (0x8292,9),
's': (0x8293,11),
't': (0x8294,10),
'u': (0x8295,12),
'v': (0x8296,12),
'w': (0x8297,12),
'x': (0x8298,12),
'y': (0x8299,12),
'z': (0x829a,12),
'À': (0x829f,12), # These French accented letters replace hiragana starting at small ぁ. 
'Â': (0x82a0,12),
'Ä': (0x82a1,12),
'Æ': (0x82a2,12),
'Ç': (0x82a3,12),
'È': (0x82a4,12),
'É': (0x82a5,12),
'Ê': (0x82a6,12),
'Ë': (0x82a7,12),
'Î': (0x82a8,12),
'Ï': (0x82a9,12),
'Ô': (0x82aa,12),
'Œ': (0x82ab,12),
'Ù': (0x82ac,12),
'Û': (0x82ad,12),
'Ü': (0x82ae,12),
'à': (0x82af,12),
'â': (0x82b0,12),
'ä': (0x82b1,12),
'æ': (0x82b2,12),
'ç': (0x82b3,12),
'è': (0x82b4,12),
'é': (0x82b5,12),
'ê': (0x82b6,12),
'ë': (0x82b7,12),
'î': (0x82b8,12),
'ï': (0x82b9,12),
'ô': (0x82ba,12),
'œ': (0x82bb,12),
'ù': (0x82bc,12),
'û': (0x82bd,12),
'ü': (0x82be,12),
' ': (0x8140,8),
'.': (0x8144,9), # Increased space after punctuation.
',': (0x8143,9),
':': (0x8146,6),
';': (0x8147,6),
'?': (0x8148,13),
'!': (0x8149,6),
'\'': (0x814c,5), # Apostrophe
'"': (0x814e,9),
'—': (0x815c,12), # Em dash
'–': (0x815b,12), # En dash
'-': (0x815d,12), # Dash
'/': (0x815e,12),
'~': (0x8160,12),
'‘': (0x8165,5), # Opening single quotation
'’': (0x8166,5), # Closing single quotation
'“': (0x8167,9), # Opening double quotation
'”': (0x8168,9), # Closing double quotation
'(': (0x8169,12),
')': (0x816a,12),
'[': (0x816d,12),
']': (0x816e,12),
'+': (0x817b,12),
'×': (0x817e,12), # Multiplication sign
'÷': (0x8180,12), # One value skipped internally for some reason.
'=': (0x8181,12),
'<': (0x8183,12),
'>': (0x8184,12),
'°': (0x818b,12),
'$': (0x8190,12),
'%': (0x8193,12),
'#': (0x8194,12),
'&': (0x8195,12),
'*': (0x8196,12),
'@': (0x8197,12),
'☆': (0x8199,12),
'★': (0x819a,12),
'0': (0x8240,12),
'1': (0x8241,8),
'2': (0x8242,12),
'3': (0x8243,12),
'4': (0x8244,12),
'5': (0x8245,12),
'6': (0x8246,12),
'7': (0x8247,12),
'8': (0x8248,12),
'9': (0x8249,12),
'\\': (0x2f2f,12),
'{': None, # Ignore curly brackets as they are used for control codes.
'}': None}

def ascii_to_sjis(input_str,break_lines=True,offset=0,vwf=True,*args,**kwargs):
    """Converts a string of ASCII characters to 
    byte-swapped Shift-JIS and null-terminate it.
    
    Set break_lines to false to bypass the linebreak function.
    Use this for non-dialogue text, such as menus.

    Set the offset argument to the number of tiles to skip
    from the below table. This can be used to redefine
    otherwise unused tiles for custom glyphs, such as an 
    alternate font for areas outside of the dialogue box
    with a different font size.

    The vwf argument adds control codes before each character to
    adjust font offset dynamically. Set this to False in areas where
    this is not desirable.
    
    The keyword arguments length_limit, last_row_length_limit, and 
    row_limit can be passed to linebreak function."""

    warnings = 0

    if break_lines:
        if vwf:
            input_str, _, warnings = linebreak_vwf(input_str,line_id=kwargs.get("line_id",None),
                                filename=kwargs.get("filename",None),
                                length_limit=kwargs.get("length_limit",407),
                                last_row_length_limit=kwargs.get("last_row_length_limit",396),
                                row_limit=kwargs.get("row_limit",3))
        else:
            input_str, _, warnings = linebreak(input_str,line_id=kwargs.get("line_id",None),
                    filename=kwargs.get("filename",None),
                    length_limit=kwargs.get("length_limit",37),
                    last_row_length_limit=kwargs.get("last_row_length_limit",37),
                    row_limit=kwargs.get("row_limit",3))

    input_str = input_str.strip()
    
    output = bytearray()

    i = 0
    while i < len(input_str):
        if input_str[i] != "{":
            try:
                output += struct.pack(">H",table[input_str[i]][0] + offset)
            # Exit if a script file contains a character not in table, continue if run from command line.
            except KeyError as e:
                if kwargs.get("filename") is not None:
                    print(f"Error reading {kwargs['filename']} at line ID {kwargs['line_id']}: Invalid character {e}.")
                    exit()
                else:
                    print(f"Error: Invalid character {e}.")
                    return (b'',1)

        else:
            # If { is encountered, parse as a control code and paste characters directly rather than translating them.
            while input_str[i+1] != "}": # Check next character and stop pasting when } is next.
                i += 1
                output += bytes(input_str[i],"shift_jis_2004")
            i += 1 # Skip } character.
            
        i += 1

    output += b'\x00' # Terminate string.

    return (output,warnings)


def linebreak(input_str,filename=None,line_id=None,length_limit=37,last_row_length_limit=37,row_limit=3):
    """Break lines into rows according to length_limit. 
    Default length is 37.
    A backslash character is inserted at line breaks, 
    which is translated in ascii_to_sjis to byte 2F2F.
    
    Control code sequences are not counted in word length,
    assuming they consist of {} containing only letters, numbers,
    commas, and @. Because of the need for non-printable control 
    codes, the standard text wrapping functions cannot be used.
    
    Returns a tuple containing the output string, the number of 
    rows, and the number of warnings generated.
    """
    
    output = ""
    current_length = 0
    rows = 1
    warnings = 0

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
                rows += 1
                current_length = word_length
            # Add a space if there are more words remaining, or break otherwise.
            if i[0] < len(input_str):
                output += " "
            else:
                break
        else:
            output = output.rstrip() + "\\" # Remove space inserted by previous word.
            rows += 1
            current_length = 0

    if rows == row_limit and current_length > last_row_length_limit:
        if filename is not None and line_id is not None:
            print(f"WARNING: Last row limit overflow in {filename} at line {line_id}: {output}")
        else:
            print(f"WARNING: Last row limit overflow: {output}")
        warnings += 1

    if rows > row_limit:
        if line_id is not None:
            print(f"WARNING: Line break overflow at line {line_id}: {output}")
        else:
            print(f"WARNING: Line break overflow: {output}")
        warnings += 1

    return (output,rows,warnings)


def linebreak_vwf(input_str,filename=None,line_id=None,length_limit=407,last_row_length_limit=396,row_limit=3):
    """Variable-width version of linebreak.
    Break lines into rows according to length_limit, which
    is a width in pixels rather than characters. 
    Default length is 407.
    A control code @fm is inserted before each character where
    the width is different from the previous character.
    
    Control code sequences are not counted in word length,
    assuming they consist of {} containing only letters, numbers,
    commas, and @. Because of the need for non-printable control 
    codes, the standard text wrapping functions cannot be used.
    
    Returns a tuple containing the output string, the number of 
    rows, and the number of warnings generated.
    """
    
    output = ""
    current_length = 0
    word_length = 0
    prev_char_width = 8 # Default value is length of space.
    rows = 1
    warnings = 0

    # Split input string into an enumerated list of each word. Forced line breaks are split into their own word.
    input_str = list(enumerate(input_str.replace(r"\n"," \\ ").replace("//"," \\ ").split(" "),1))

    for i in input_str:

        # word_length = len(i[1]) - sum([len(p) for p in re.findall("{[a-zA-Z0-9,@!=]+}",i[1])]) # Do not count control code sequences in word length.

        # Insert word that is not a forced line break.
        if i[1] != "\\":
            word = i[1]
            new_word = ""
            word_length = 0

            j = 0
            while j < len(word):    
                char = word[j]
                if char != "{":
                    char_width = table[char][1]
                    word_length += char_width
                    # Insert control codes before each character to set fm.
                    if char_width != prev_char_width:
                        new_word += "{@fm" + str(char_width) + ",0}" + char
                    else:
                        new_word += char
                    prev_char_width = char_width
                else:
                    # If { is encountered, parse as a control code and paste characters directly rather than translating them.
                    new_word += word[j] # Insert { character.
                    while word[j+1] != "}": # Check next character and stop pasting when } is next.
                        j += 1
                        new_word += word[j]
                    else:
                        j += 1
                        new_word += word[j]
                
                j += 1

            if current_length + word_length + 8 <= length_limit:
                output += new_word
                current_length += word_length + 8
            else:
                output = output.rstrip() + "\\" + new_word
                rows += 1
                current_length = word_length
            # Add a space if there are more words remaining, or break otherwise.
            if i[0] < len(input_str):
                if prev_char_width != 8:
                    output += "{@fm8,0}"
                    prev_char_width = 8
                output += " "
            else:
                break
        else:
            output = output.rstrip() + "\\" # Remove space inserted by previous word.
            rows += 1
            current_length = 0

    if rows == row_limit and current_length > last_row_length_limit:
        if filename is not None and line_id is not None:
            print(f"WARNING: Last row limit overflow in {filename} at line {line_id}: {output}")
        else:
            print(f"WARNING: Last row limit overflow: {output}")
        warnings += 1

    if rows > row_limit:
        if line_id is not None:
            print(f"WARNING: Line break overflow at line {line_id}: {output}")
        else:
            print(f"WARNING: Line break overflow: {output}")
        warnings += 1

    # Review inserted control codes from command line.
    if __name__ == "__main__":
        print(output)

    return (output,rows,warnings)


def swap_bytes(value):
    """Convert hex string to little-endian bytes."""

    str = hex(value)[2:].zfill(8)

    return str[6:8] + str[4:6] + str[2:4] + str[0:2]    


def read_string(file,encoding="shift_jis_2004"):
    """Read a null-terminated string from a file object opened in 
    binary mode, using the codec given by the encoding argument. 

    Script text is read as Shift_JIS-2004, which is the default encoding.
    https://en.wikipedia.org/wiki/Shift_JIS#Shift_JISx0213_and_Shift_JIS-2004
    
    If encoding is None, the string is not decoded."""

    byte_string = bytearray()
    while True:
        bytes = file.read(1)
        if bytes == b'':
            raise ValueError("Unable to read bytes.")
        if bytes == b'\x00': # Strings are terminated with single byte 00.
            if encoding is not None:
                return byte_string.decode(encoding)
            else:
                return byte_string
        byte_string += bytes


def main():
    """When run as a script, encode strings to binary Shift_JIS-2004
    using the default linebreak arguments."""

    while True:
        input_str = input("String (Input blank string to exit): ")
        if input_str != "" :
            output_str = ascii_to_sjis(input_str)
            print(output_str[0].hex(),"\n")
            if output_str[1] > 0:
                print(f"{output_str[1]} warning(s) generated.")
        else:
            break
        

if __name__ == "__main__":
    main()