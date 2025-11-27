import types
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, TypeVar, Union, get_args, get_origin

import streamlit as st
from pydantic import AnyUrl, BaseModel, EmailStr, Field, SecretStr, ValidationError
from pydantic_core import PydanticUndefined

T = TypeVar("T", bound=BaseModel)


def _resolve_annotation(annotation):
    """
    Unwraps Optional[T] or Union[T, None] to get T.
    Handles standard Optional and Python 3.10+ pipe syntax (T | None).
    Returns (base_type, is_optional)
    """
    origin = get_origin(annotation)

    is_union = origin is Union
    if not is_union and hasattr(types, "UnionType"):
        is_union = origin is types.UnionType

    if is_union:
        args = get_args(annotation)

        if type(None) in args:
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                return non_none_args[0], True
    return annotation, False


def _render_field(field_name: str, field_info: Any, parent_key: str = "") -> Any:
    """
    Renders a single field based on its type.
    Recursive for nested Pydantic models.
    """

    key = f"{parent_key}_{field_name}"

    label = field_info.title if field_info.title else field_name.replace("_", " ").title()
    description = field_info.description if field_info.description else ""

    resolved_type, is_optional = _resolve_annotation(field_info.annotation)

    field_origin = get_origin(resolved_type)
    default_value = field_info.default if field_info.default is not PydanticUndefined else None

    if field_origin is Literal:
        options = get_args(resolved_type)
        return st.selectbox(label, options=options, key=key, help=description)

    if field_origin in (list, list, set, set):
        placeholder_text = "Enter comma-separated values (e.g., 1, 2, 3 or tag1, tag2)"

        if default_value is Field:
            default_value = ""
        elif isinstance(default_value, (list, set)):
            default_value = ", ".join(map(str, default_value))

        return st.text_area(
            label,
            key=key,
            help=f"{description} ({placeholder_text})",
            value=default_value,
        )

    if isinstance(resolved_type, type) and issubclass(resolved_type, Enum):
        options = [e.value for e in resolved_type]
        return st.selectbox(label, options=options, key=key, help=description)

    if isinstance(resolved_type, type) and issubclass(resolved_type, BaseModel):
        st.markdown(f"### {label}")
        if description:
            st.caption(description)

        with st.container(border=True):
            data = {}
            for name, info in resolved_type.model_fields.items():
                data[name] = _render_field(name, info, parent_key=key)
            return data

    field_type = resolved_type

    if field_type is SecretStr:
        return st.text_input(label, type="password", key=key, help=description)

    if field_type is Decimal:
        constraints = field_info.json_schema_extra if field_info.json_schema_extra else {}
        min_val = constraints.get("minimum")
        max_val = constraints.get("maximum")

        if default_value is Field:
            default_value = float(min_val) if min_val is not None else 0.0
        else:
            default_value = (
                float(default_value) if default_value is not None and default_value is not PydanticUndefined else None
            )

        return st.text_input(
            label,
            value=default_value,
            key=key,
            help=description,
        )

    if field_type in (str, EmailStr, AnyUrl):
        if default_value is Field:
            default_value = "" if not is_optional else None

        return st.text_input(label, key=key, help=description, value=default_value)

    if field_type is int or field_type is float:
        constraints = field_info.json_schema_extra if field_info.json_schema_extra else {}

        min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
        max_val = constraints.get("maximum") or constraints.get("exclusiveMaximum")

        if default_value is Field or default_value is None or default_value is PydanticUndefined:
            if field_type is int:
                default_value = min_val if min_val is not None else 0
            elif field_type is float:
                default_value = min_val if min_val is not None else 0.0

        if min_val is not None and max_val is not None:
            return st.slider(
                label,
                min_value=min_val,
                max_value=max_val,
                value=default_value,
                step=1 if field_type is int else 0.01,
                key=key,
                help=description,
            )

        return st.number_input(
            label,
            value=default_value,
            step=1 if field_type is int else 0.01,
            format="%d" if field_type is int else "%.2f",
            key=key,
            help=description,
        )

    if field_type is bool:
        return st.checkbox(
            label,
            key=key,
            help=description,
            value=field_info.default if field_info.default is not None else False,
        )

    if field_type is date:
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

    with st.form(key=form_key):
        st.subheader(f"{model.__name__} Form")

        form_data = {}

        for name, field_info in model.model_fields.items():
            form_data[name] = _render_field(name, field_info, parent_key=form_key)

        submitted = st.form_submit_button("Submit")

        if submitted:
            try:
                instance = model(**form_data)
                st.success("Validation Successful!")
            except ValidationError as e:
                st.error("Validation Error")

                for error in e.errors():
                    loc = " -> ".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    st.error(f"**{loc}**: {msg}")
                return None
            else:
                return instance

    return None
