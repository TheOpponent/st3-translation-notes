import utils

def test_linebreak():

    # Test line breaking.
    test_string1 = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do tempor. Aliquet feugiat in metus sagittis."
    assert utils.linebreak(test_string1) == (r"Lorem ipsum dolor sit amet,\consectetur adipiscing elit,\sed do tempor. Aliquet feugiat\in metus sagittis.",4)

    # Test a forced line break, which will cause overflow.
    test_string2 = r"Lorem ipsum\ndolor sit amet, consectetur adipiscing elit, sed do tempor. Aliquet feugiat in metus sagittis."
    assert utils.linebreak(test_string2) == (r"Lorem ipsum\dolor sit amet, consectetur\adipiscing elit, sed do\tempor. Aliquet feugiat in\metus sagittis.",5)