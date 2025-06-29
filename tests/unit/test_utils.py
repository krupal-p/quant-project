from app.common.utils import to_snake_case


def test_to_snake_case() -> None:
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
    assert to_snake_case("RatecodeID") == "ratecode_id"
    assert to_snake_case("!Special@Characters#") == "special_characters"

    # Basic CamelCase conversions
    assert to_snake_case("CamelCase") == "camel_case"
    assert to_snake_case("PascalCase") == "pascal_case"
    assert to_snake_case("mixedCaseString") == "mixed_case_string"
    assert to_snake_case("XMLHttpRequest") == "xml_http_request"
    assert to_snake_case("HTMLParser") == "html_parser"

    # Strings with spaces
    assert to_snake_case("string with spaces") == "string_with_spaces"
    assert to_snake_case("multiple   spaces   between") == "multiple_spaces_between"
    assert to_snake_case(" leading space") == "leading_space"
    assert to_snake_case("trailing space ") == "trailing_space"
    assert (
        to_snake_case("  multiple  leading  trailing  ") == "multiple_leading_trailing"
    )

    # Strings with hyphens
    assert to_snake_case("string-with-hyphens") == "string_with_hyphens"
    assert to_snake_case("multiple---hyphens") == "multiple_hyphens"
    assert to_snake_case("-leading-hyphen") == "leading_hyphen"
    assert to_snake_case("trailing-hyphen-") == "trailing_hyphen"

    # Mixed separators
    assert to_snake_case("mixed-case with_spaces") == "mixed_case_with_spaces"
    assert to_snake_case("CamelCase-with-hyphens") == "camel_case_with_hyphens"
    assert to_snake_case("snake_case_already") == "snake_case_already"

    # Numbers
    assert to_snake_case("stringWith123Numbers") == "string_with_123_numbers"
    assert to_snake_case("number123InMiddle") == "number_123_in_middle"
    assert to_snake_case("123StartingNumber") == "123_starting_number"
    assert to_snake_case("endingNumber123") == "ending_number_123"
    assert to_snake_case("Version2Point0") == "version_2_point_0"
    assert to_snake_case("HTML5Parser") == "html_5_parser"

    # All lowercase/uppercase
    assert to_snake_case("alllowercase") == "alllowercase"
    assert to_snake_case("ALLUPPERCASE") == "alluppercase"
    assert to_snake_case("MixedCASEString") == "mixed_case_string"

    # Special characters
    assert (
        to_snake_case("string_with_special_characters!@#$%^&*()")
        == "string_with_special_characters"
    )
    assert to_snake_case("!Special@Characters#") == "special_characters"
    assert to_snake_case("email@domain.com") == "email_domain_com"
    assert to_snake_case("path/to/file.txt") == "path_to_file_txt"
    assert to_snake_case("key:value;pair") == "key_value_pair"

    # Consecutive underscores
    assert (
        to_snake_case("string__with__consecutive__underscores")
        == "string_with_consecutive_underscores"
    )
    assert (
        to_snake_case("___multiple___leading___trailing___")
        == "multiple_leading_trailing"
    )

    # Edge cases
    assert to_snake_case("") == ""
    assert to_snake_case("a") == "a"
    assert to_snake_case("A") == "a"
    assert to_snake_case("1") == "1"
    assert to_snake_case("_") == ""
    assert to_snake_case("___") == ""
    assert to_snake_case("!@#$%^&*()") == ""

    # Acronyms and abbreviations
    assert to_snake_case("HTTPSConnection") == "https_connection"
    assert to_snake_case("URLParser") == "url_parser"
    assert to_snake_case("JSONData") == "json_data"
    assert to_snake_case("XMLToHTML") == "xml_to_html"
    assert to_snake_case("PDFToWordConverter") == "pdf_to_word_converter"

    # Real-world examples
    assert to_snake_case("firstName") == "first_name"
    assert to_snake_case("lastName") == "last_name"
    assert to_snake_case("emailAddress") == "email_address"
    assert to_snake_case("phoneNumber") == "phone_number"
    assert to_snake_case("dateOfBirth") == "date_of_birth"
    assert to_snake_case("createdAt") == "created_at"
    assert to_snake_case("updatedAt") == "updated_at"
    assert to_snake_case("userId") == "user_id"
    assert to_snake_case("companyName") == "company_name"
    assert to_snake_case("isActive") == "is_active"

    # Database column examples
    assert to_snake_case("ex-date") == "ex_date"
    assert to_snake_case("RatecodeID") == "ratecode_id"
    assert to_snake_case("CustomerID") == "customer_id"
    assert to_snake_case("OrderDate") == "order_date"
    assert to_snake_case("UnitPrice") == "unit_price"

    # Complex cases
    assert (
        to_snake_case("trailing Annual DividendRate") == "trailing_annual_dividend_rate"
    )
    assert to_snake_case("Mixed_Characters-123") == "mixed_characters_123"
    assert to_snake_case("APIKey2024Version") == "api_key_2024_version"
    assert to_snake_case("OAuth2TokenExpiry") == "o_auth_2_token_expiry"

    # Unicode and international characters (if supported)
    assert to_snake_case("café") == "cafe"
    assert to_snake_case("naïve") == "naive"
    assert to_snake_case("résumé") == "resume"
