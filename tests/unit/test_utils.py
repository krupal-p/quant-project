from app.common.utils import to_snake_case


def test_to_snake_case():
    assert to_snake_case("CamelCase") == "camel_case"
    assert to_snake_case("PascalCase") == "pascal_case"
    assert to_snake_case("mixedCaseString") == "mixed_case_string"
    assert (
        to_snake_case("trailing Annual DividendRate") == "trailing_annual_dividend_rate"
    )
    assert to_snake_case("string with spaces") == "string_with_spaces"
    assert to_snake_case("string-with-hyphens") == "string_with_hyphens"
    assert to_snake_case("string_with_underscores") == "string_with_underscores"
    assert to_snake_case("stringWith123Numbers") == "string_with_123_numbers"
    assert to_snake_case("alllowercase") == "alllowercase"
    assert to_snake_case("ALLUPPERCASE") == "alluppercase"
    assert to_snake_case("Mixed_Characters-123") == "mixed_characters_123"
    assert (
        to_snake_case("string__with__consecutive__underscores")
        == "string_with_consecutive_underscores"
    )
    assert (
        to_snake_case("string_with_special_characters!@#$%^&*()")
        == "string_with_special_characters"
    )

    assert to_snake_case("ex-date") == "ex_date"
