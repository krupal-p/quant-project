import types
from datetime import date, datetime, time
from decimal import Decimal  # Import Decimal
from enum import Enum
from typing import Any, Literal, TypeVar, Union, get_args, get_origin

import streamlit as st
from pydantic import AnyUrl, BaseModel, EmailStr, Field, SecretStr, ValidationError
from pydantic_core import PydanticUndefined

# ==========================================
# 1. CORE LOGIC: Form Rendering Engine
# ==========================================

T = TypeVar("T", bound=BaseModel)


def _resolve_annotation(annotation):
    """
    Unwraps Optional[T] or Union[T, None] to get T.
    Handles standard Optional and Python 3.10+ pipe syntax (T | None).
    Returns (base_type, is_optional)
    """
    origin = get_origin(annotation)

    # Check for both typing.Union and types.UnionType (for Python 3.10+ | syntax)
    is_union = origin is Union
    if not is_union and hasattr(types, "UnionType"):
        is_union = origin is types.UnionType

    if is_union:
        args = get_args(annotation)
        # Check if NoneType is in the union (implies Optional)
        if type(None) in args:
            # Filter out None and take the first remaining type
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                # If the remaining type is still a collection/literal, return it unresolved
                return non_none_args[0], True
    return annotation, False


def _render_field(field_name: str, field_info: Any, parent_key: str = "") -> Any:
    """
    Renders a single field based on its type.
    Recursive for nested Pydantic models.
    """
    # Create a unique key for Streamlit widgets to avoid collisions
    key = f"{parent_key}_{field_name}"

    # Get the display label (use title or capitalize field name)
    label = field_info.title if field_info.title else field_name.replace("_", " ").title()
    description = field_info.description if field_info.description else ""

    # Resolve types (handle Optional[int], etc.)
    resolved_type, is_optional = _resolve_annotation(field_info.annotation)

    # Check for collection or literal origins on the resolved type
    field_origin = get_origin(resolved_type)
    default_value = field_info.default if field_info.default is not PydanticUndefined else None
    # --- New Type Support ---

    # 1. Handle Literals (Literal[...])
    if field_origin is Literal:
        options = get_args(resolved_type)
        return st.selectbox(label, options=options, key=key, help=description)

    # 2. Handle Lists and Sets (Collections)
    if field_origin in (list, list, set, set):
        # Use text_area and rely on Pydantic's validation to parse the collection
        # from comma-separated input.
        placeholder_text = "Enter comma-separated values (e.g., 1, 2, 3 or tag1, tag2)"

        if default_value is Field:
            default_value = ""  # No default value defined
        elif isinstance(default_value, (list, set)):
            default_value = ", ".join(map(str, default_value))

        return st.text_area(
            label,
            key=key,
            help=f"{description} ({placeholder_text})",
            value=default_value,
        )

    # --- Existing Type Support (using resolved_type) ---

    # 3. Handle Enums (Selectbox)
    if isinstance(resolved_type, type) and issubclass(resolved_type, Enum):
        options = [e.value for e in resolved_type]
        return st.selectbox(label, options=options, key=key, help=description)

    # 4. Handle Nested Pydantic Models (Recursion)
    if isinstance(resolved_type, type) and issubclass(resolved_type, BaseModel):
        st.markdown(f"### {label}")
        if description:
            st.caption(description)

        # Recurse: Create a container for the nested model
        with st.container(border=True):
            data = {}
            for name, info in resolved_type.model_fields.items():
                data[name] = _render_field(name, info, parent_key=key)
            return data

    # Use the base resolved_type for standard checks
    field_type = resolved_type

    # 5. Handle Secrets (SecretStr)
    if field_type is SecretStr:
        return st.text_input(label, type="password", key=key, help=description)

    # 6. Handle Decimal (Precise Number Input)
    if field_type is Decimal:
        # Pydantic 2 uses json_schema_extra for constraints like min/max
        constraints = field_info.json_schema_extra if field_info.json_schema_extra else {}
        min_val = constraints.get("minimum")
        max_val = constraints.get("maximum")

        # Determine initial value and convert to float for st.number_input
        if default_value is Field:
            # Default to 0.0 or min_val if constraints exist
            default_value = float(min_val) if min_val is not None else 0.0
        else:
            # Ensure Decimal is converted to float for st.number_input
            default_value = (
                float(default_value) if default_value is not None and default_value is not PydanticUndefined else None
            )

        # Decimal requires high precision format
        return st.text_input(
            label,
            value=default_value,
            # min_value=float(min_val) if min_val is not None else None,
            # max_value=float(max_val) if max_val is not None else None,
            # step=0.0000000001,  # Provide a very small step for high precision
            # format="%.10f",  # Display 10 decimal places
            key=key,
            help=description,
        )

    # 7. Handle Specialized Strings (EmailStr, AnyUrl, str)
    # if field_type is str or field_type is EmailStr or field_type is AnyUrl:
    if field_type in (str, EmailStr, AnyUrl):
        # Default value handling for strings
        if default_value is Field:
            default_value = "" if not is_optional else None

        return st.text_input(label, key=key, help=description, value=default_value)

    # 8. Handle Constrained Numbers (int, float) - Slider/Number Input
    if field_type is int or field_type is float:
        constraints = field_info.json_schema_extra if field_info.json_schema_extra else {}

        min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
        max_val = constraints.get("maximum") or constraints.get("exclusiveMaximum")

        # Determine initial value

        # FIX: Check for PydanticUndefinedType or explicit None and set a type-consistent default
        if default_value is Field or default_value is None or default_value is PydanticUndefined:
            if field_type is int:
                # Default to 0 or min_val
                default_value = min_val if min_val is not None else 0
            elif field_type is float:
                # CRUCIAL FIX: Ensure default for float is a float (0.0) when step is float (0.01)
                default_value = min_val if min_val is not None else 0.0

        if min_val is not None and max_val is not None:
            # Use a slider if both min and max are defined (Constrained Number)
            return st.slider(
                label,
                min_value=min_val,
                max_value=max_val,
                value=default_value,
                step=1 if field_type is int else 0.01,
                key=key,
                help=description,
            )
        # Fallback to number_input
        return st.number_input(
            label,
            value=default_value,
            step=1 if field_type is int else 0.01,
            format="%d" if field_type is int else "%.2f",
            key=key,
            help=description,
        )

    # 9. Handle remaining Standard Types (bool, date, time, datetime)

    if field_type is bool:
        return st.checkbox(
            label,
            key=key,
            help=description,
            value=field_info.default if field_info.default is not None else False,
        )

    if field_type is date:
        # Use field_info.default if available, otherwise rely on st.date_input default
        default_date = field_info.default if isinstance(field_info.default, date) else None
        return st.date_input(label, key=key, help=description, value=default_date)

    if field_type is time:
        default_time = field_info.default if isinstance(field_info.default, time) else None
        return st.time_input(label, key=key, help=description, value=default_time)

    if field_type is datetime:
        d = st.date_input(f"{label} (Date)", key=f"{key}_date", help=description)
        t = st.time_input(f"{label} (Time)", key=f"{key}_time")
        if d and t:
            return datetime.combine(d, t)
        return None

    # Fallback for unhandled types
    st.warning(f"Field '{label}' has unsupported type: {field_type}. Returning None.")
    return None


def render_pydantic_form[T: BaseModel](model: type[T], form_key: str = "pydantic_form") -> T | None:
    """
    Generates a Streamlit form from a Pydantic model class.

    Args:
        model: The Pydantic model class (not an instance).
        form_key: Unique key for the st.form.

    Returns:
        An instance of the model if submitted and valid, otherwise None.
    """
    # Initialize the container for the form
    with st.form(key=form_key):
        # Set the title
        st.subheader(f"{model.__name__} Form")

        form_data = {}

        # Loop through all fields in the model and render widgets
        for name, field_info in model.model_fields.items():
            form_data[name] = _render_field(name, field_info, parent_key=form_key)

        submitted = st.form_submit_button("Submit")

        if submitted:
            try:
                # Attempt to validate and create the model instance
                # NOTE: When passing data to the model, it handles the conversion
                # from the float input (from Streamlit) back to Decimal.
                instance = model(**form_data)
                st.success("Validation Successful!")
            except ValidationError as e:
                st.error("Validation Error")
                # Format validation errors nicely
                for error in e.errors():
                    loc = " -> ".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    st.error(f"**{loc}**: {msg}")
                return None
            else:
                return instance

    return None
