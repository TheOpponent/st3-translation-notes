from utils import utils


def test_linebreak():
    # Test line breaking.
    test_string1 = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod labore et dolor magna aliqua."
    assert utils.linebreak(test_string1) == (
        r"Lorem ipsum dolor sit amet,\consectetur adipiscing elit, sed do\eiusmod labore et dolor magna aliqua.",
        3,
        0,
    )

    # Test a forced line break, which will cause overflow and generate 1 warning.
    test_string2 = r"Lorem ipsum//dolor sit amet, consectetur adipiscing elit, sed do eiusmod labore et dolor magna aliqua."
    assert utils.linebreak(test_string2) == (
        r"Lorem ipsum\dolor sit amet, consectetur\adipiscing elit, sed do eiusmod\labore et dolor magna aliqua.",
        4,
        1,
    )
