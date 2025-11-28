import types
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, TypeVar, Union, get_args, get_origin

import streamlit as st
from pydantic import AnyUrl, BaseModel, EmailStr, SecretStr, ValidationError
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


def _get_default_value(field_info: Any, current_value: Any, field_type: Any) -> Any:
    """Helper to determine the default value for a widget."""
    if current_value is not None:
        return current_value

    if field_info.default is not PydanticUndefined:
        return field_info.default

    # Fallbacks for types if no default is provided
    if field_type in (int, float, Decimal):
        constraints = field_info.json_schema_extra or {}
        min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
        if min_val is not None:
            return float(min_val) if field_type is float else int(min_val)
        return 0 if field_type is int else 0.0

    if field_type in (str, EmailStr, AnyUrl, SecretStr):
        return ""

    if field_type is bool:
        return False

    if field_type in (list, set):
        return []

    return None


def _render_field(field_name: str, field_info: Any, parent_key: str = "", current_value: Any = None) -> Any:
    """
    Renders a single field based on its type.
    Recursive for nested Pydantic models.
    """

    key = f"{parent_key}_{field_name}"

    label = field_info.title if field_info.title else field_name.replace("_", " ").title()
    description = field_info.description if field_info.description else ""

    resolved_type, _ = _resolve_annotation(field_info.annotation)

    field_origin = get_origin(resolved_type)

    # Determine the value to display
    default_value = _get_default_value(field_info, current_value, resolved_type)

    if field_origin is Literal:
        options = get_args(resolved_type)
        # Ensure default_value is in options, else default to first option
        idx = options.index(default_value) if default_value in options else 0
        return st.selectbox(label, options=options, index=idx, key=key, help=description)

    if field_origin in (list, set):
        # Check for List[BaseModel]
        args = get_args(resolved_type)
        is_nested_model = False
        if args:
            try:
                if issubclass(args[0], BaseModel):
                    is_nested_model = True
            except TypeError:
                pass

        if is_nested_model:
            item_model = args[0]
            st.markdown(f"**{label}**")
            if description:
                st.caption(description)

            items = current_value if isinstance(current_value, list) else []

            # Control number of items
            col_cnt, col_btn = st.columns([3, 1])
            with col_cnt:
                num_items = st.number_input(
                    f"Count ({label})",
                    min_value=0,
                    value=len(items),
                    step=1,
                    key=f"{key}_count",
                    help=f"Adjust count and click Update to update the list of {label}",
                )
            with col_btn:
                st.write("")
                st.write("")
                st.form_submit_button(f"Update {label}")

            result_list = []
            for i in range(int(num_items)):
                item_val = items[i] if i < len(items) else None

                with st.expander(f"{item_model.__name__} #{i + 1}", expanded=False):
                    item_data = {}
                    nested_values = item_val.model_dump() if isinstance(item_val, BaseModel) else (item_val or {})

                    for name, info in item_model.model_fields.items():
                        item_data[name] = _render_field(
                            name,
                            info,
                            parent_key=f"{key}_{i}",
                            current_value=nested_values.get(name),
                        )
                    result_list.append(item_data)
            return result_list

        placeholder_text = "Enter comma-separated values (e.g., 1, 2, 3 or tag1, tag2)"

        display_value = ""
        if isinstance(default_value, (list, set)):
            display_value = ", ".join(map(str, default_value))

        raw_input = st.text_area(
            label,
            key=key,
            help=f"{description} ({placeholder_text})",
            value=display_value,
        )

        if raw_input:
            # Return a list, Pydantic will coerce to set if needed
            return [item.strip() for item in raw_input.split(",") if item.strip()]
        return []

    if isinstance(resolved_type, type) and issubclass(resolved_type, Enum):
        options = [e.value for e in resolved_type]
        idx = options.index(default_value) if default_value in options else 0
        return st.selectbox(label, options=options, index=idx, key=key, help=description)

    if isinstance(resolved_type, type) and issubclass(resolved_type, BaseModel):
        # Use expander for nested models to save space
        with st.expander(label, expanded=True):
            if description:
                st.caption(description)

            data = {}
            # If current_value is a model instance, convert to dict to pass down
            nested_values = (
                current_value.model_dump() if isinstance(current_value, BaseModel) else (current_value or {})
            )

            for name, info in resolved_type.model_fields.items():
                data[name] = _render_field(name, info, parent_key=key, current_value=nested_values.get(name))
            return data

    field_type = resolved_type

    if field_type is SecretStr:
        return st.text_input(label, type="password", value=default_value, key=key, help=description)

    if field_type is Decimal:
        # Decimal handled as string input
        val_str = str(default_value) if default_value is not None else ""
        return st.text_input(
            label,
            value=val_str,
            key=key,
            help=description,
        )

    if field_type in (str, EmailStr, AnyUrl):
        return st.text_input(label, key=key, help=description, value=default_value)

    if field_type is int or field_type is float:
        constraints = field_info.json_schema_extra if field_info.json_schema_extra else {}

        min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
        max_val = constraints.get("maximum") or constraints.get("exclusiveMaximum")

        # Ensure default_value respects constraints if possible
        if min_val is not None and default_value < min_val:
            default_value = min_val
        if max_val is not None and default_value > max_val:
            default_value = max_val

        if min_val is not None and max_val is not None:
            return st.slider(
                label,
                min_value=float(min_val) if field_type is float else int(min_val),
                max_value=float(max_val) if field_type is float else int(max_val),
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
            value=default_value,
        )

    if field_type is date:
        return st.date_input(label, key=key, help=description, value=default_value)

    if field_type is time:
        return st.time_input(label, key=key, help=description, value=default_value)

    if field_type is datetime:
        # Handle datetime splitting
        d_val = default_value.date() if isinstance(default_value, datetime) else None
        t_val = default_value.time() if isinstance(default_value, datetime) else None

        col1, col2 = st.columns(2)
        with col1:
            d = st.date_input(f"{label} (Date)", value=d_val, key=f"{key}_date", help=description)
        with col2:
            t = st.time_input(f"{label} (Time)", value=t_val, key=f"{key}_time")

        if d and t:
            return datetime.combine(d, t)
        return None

    return st.text_input(
        label,
        key=key,
        help=description,
        value=str(default_value) if default_value is not None else "",
    )


def render_pydantic_form[T: BaseModel](
    model: type[T],
    instance: T | None = None,
    form_key: str = "pydantic_form",
) -> T | None:
    """
    Generates a Streamlit form from a Pydantic model class.

    Args:
        model: The Pydantic model class (not an instance).
        instance: An optional existing instance to pre-fill the form (Edit mode).
        form_key: Unique key for the st.form.

    Returns:
        An instance of the model if submitted and valid, otherwise None.
    """

    with st.form(key=form_key):
        st.subheader(f"{model.__name__} Form")

        form_data = {}

        # If instance is provided, convert to dict for easier lookup
        instance_data = instance.model_dump() if instance else {}

        for name, field_info in model.model_fields.items():
            form_data[name] = _render_field(
                name,
                field_info,
                parent_key=form_key,
                current_value=instance_data.get(name),
            )

        submitted = st.form_submit_button("Submit")

        if submitted:
            try:
                # Create new instance from form data
                new_instance = model(**form_data)
                st.success("Validation Successful!")
            except ValidationError as e:
                st.error("Validation Error")

                for error in e.errors():
                    loc = " -> ".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    st.error(f"**{loc}**: {msg}")
                return None
            else:
                return new_instance

    return None
