from app.common.utils import to_snake_case


def test_camel_case():
    assert to_snake_case("CamelCase") == "camel_case"


def test_pascal_case():
    assert to_snake_case("PascalCase") == "pascal_case"


def test_mixed_case():
    assert to_snake_case("mixedCaseString") == "mixed_case_string"
    assert (
        to_snake_case("trailingAnnualDividendRate") == "trailing_annual_dividend_rate"
    )


def test_with_spaces():
    assert to_snake_case("string with spaces") == "string_with_spaces"


def test_with_hyphens():
    assert to_snake_case("string-with-hyphens") == "string_with_hyphens"


def test_with_underscores():
    assert to_snake_case("string_with_underscores") == "string_with_underscores"


def test_with_numbers():
    assert to_snake_case("stringWith123Numbers") == "string_with_123_numbers"


def test_all_lowercase():
    assert to_snake_case("alllowercase") == "alllowercase"


def test_all_uppercase():
    assert to_snake_case("ALLUPPERCASE") == "alluppercase"


def test_mixed_characters():
    assert to_snake_case("Mixed_Characters-123") == "mixed_characters_123"


def test_consecutive_underscores():
    assert (
        to_snake_case("string__with__consecutive__underscores")
        == "string_with_consecutive_underscores"
    )


def test_special_characters():
    assert (
        to_snake_case("string_with_special_characters!@#$%^&*()")
        == "string_with_special_characters"
    )
