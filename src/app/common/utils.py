import re


def to_snake_case(s):
    # Replace spaces and hyphens with underscores
    s = s.replace(" ", "_").replace("-", "_")
    # Convert CamelCase or PascalCase to snake_case
    s = re.sub(r"(?<!^)(?=[A-Z][a-z])", "_", s)
    # Handle numbers and mixed characters
    s = re.sub(r"(?<=[a-zA-Z])(?=\d)", "_", s)
    s = re.sub(r"(?<=\d)(?=[a-zA-Z])", "_", s)
    # Handle consecutive underscores
    s = re.sub(r"__+", "_", s)
    # Remove special characters
    s = re.sub(r"[^\w\s]", "", s)
    # Convert to lowercase
    return s.lower()
