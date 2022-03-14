def test_hello_world():
    lower_case_string = "hello testing world"
    expected_upper_case_string = "Hello testing world"

    upper_case_string = lower_case_string.capitalize()

    assert upper_case_string == expected_upper_case_string