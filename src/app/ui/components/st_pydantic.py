import json
import types
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from functools import wraps
from typing import (
    Annotated,
    Any,
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

import streamlit as st
from pydantic import AnyUrl, BaseModel, EmailStr, SecretStr, TypeAdapter, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

T = TypeVar("T", bound=BaseModel)


# --- Core Context & Types ---


@dataclass(frozen=True)
class RenderContext:
    """Immutable context object passed to all renderers."""

    key: str
    field_name: str
    field_info: FieldInfo
    current_value: Any
    parent_key: str = ""
    form_key: str = ""

    @property
    def label(self) -> str:
        return self.field_info.title or self.field_name.replace("_", " ").title()

    @property
    def description(self) -> str:
        return self.field_info.description or ""

    def sub_context(
        self,
        name: str,
        info: FieldInfo,
        value: Any,
        key: str | None = None,
    ) -> "RenderContext":
        """Create a child context for nested fields."""
        return RenderContext(
            key=key or f"{self.key}_{name}",
            field_name=name,
            field_info=info,
            current_value=value,
            parent_key=self.key,
            form_key=self.form_key,
        )


Renderer = Callable[[RenderContext, Any], Any]
Predicate = Callable[[Any], bool]


# --- Registry System ---

_RENDERER_REGISTRY: list[tuple[Predicate, Renderer]] = []


def register(predicate: Predicate) -> Callable[[Renderer], Renderer]:
    """Decorator to register a renderer for types matching the predicate."""

    @wraps(predicate)
    def decorator(renderer: Renderer) -> Renderer:
        # Insert at the beginning to allow overriding (LIFO)
        _RENDERER_REGISTRY.insert(0, (predicate, renderer))
        return renderer

    return decorator


def find_renderer(type_: Any) -> Renderer | None:
    """Find the first renderer whose predicate matches the type."""
    for predicate, renderer in _RENDERER_REGISTRY:
        if predicate(type_):
            return renderer
    return None


# --- Pure Logic Helpers ---


def resolve_type(annotation: Any) -> tuple[Any, bool]:
    """
    Recursively resolves the base type and checks for optionality.
    Returns (base_type, is_optional).
    """
    if hasattr(annotation, "__value__") and type(annotation).__name__ == "TypeAliasType":
        return resolve_type(annotation.__value__)

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        return resolve_type(args[0])

    if (origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)) and type(None) in args:
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return resolve_type(non_none_args[0])[0], True

        # Reconstruct Union without None
        union_type = non_none_args[0]
        for candidate in non_none_args[1:]:
            union_type = union_type | candidate
        return union_type, True

    return annotation, False


def get_default_value(ctx: RenderContext, field_type: Any) -> Any:
    """Pure function to determine default value based on type and constraints."""
    if ctx.current_value is not None:
        return ctx.current_value

    if ctx.field_info.default is not PydanticUndefined:
        return ctx.field_info.default

    field_type, _ = resolve_type(field_type)
    origin = get_origin(field_type)

    # Constraints
    constraints = ctx.field_info.json_schema_extra or {}
    if not isinstance(constraints, dict):
        constraints = {}

    min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")

    if field_type in (int, float, Decimal):
        if min_val is not None and isinstance(min_val, (int, float, str, Decimal)):
            return float(min_val) if field_type is float else int(min_val)
        return 0.0 if field_type is float else 0

    if field_type in (str, EmailStr, AnyUrl, SecretStr):
        return ""

    if field_type is bool:
        return False

    if origin in (list, set, tuple):
        return []

    if origin is dict or field_type is dict:
        return {}

    return None


# --- State Management Abstraction ---


def _get_meta_store(form_key: str) -> dict:
    """Access the metadata store for the form."""
    return st.session_state[form_key].setdefault("meta", {})


def get_collection_state(form_key: str, field_key: str, current_items: list | dict) -> tuple[list[str], dict]:
    """
    Retrieve or initialize state for a dynamic collection.
    Returns (list_of_ids, values_map).
    """
    meta = _get_meta_store(form_key)

    if field_key not in meta:
        meta[field_key] = {}

    state = meta[field_key]

    # Initialize if needed
    if "ids" not in state or "values" not in state:
        items = list(current_items.items()) if isinstance(current_items, dict) else current_items or []

        initial_ids = [str(uuid.uuid4()) for _ in items]
        state["ids"] = initial_ids

        # For dicts, values are stored as {"key": k, "value": v}
        # For lists, values are stored directly
        if isinstance(current_items, dict):
            state["values"] = {uid: {"key": k, "value": v} for uid, (k, v) in zip(initial_ids, items, strict=False)}
        else:
            state["values"] = dict(zip(initial_ids, items, strict=False))

    return state["ids"], state["values"]


def add_collection_item(form_key: str, field_key: str, default_value: Any) -> None:
    """Add a new item to the collection state."""
    meta = _get_meta_store(form_key)
    state = meta.get(field_key, {})
    if "ids" in state and "values" in state:
        new_id = str(uuid.uuid4())
        state["ids"].append(new_id)
        state["values"][new_id] = default_value


def remove_collection_item(form_key: str, field_key: str, item_id: str) -> None:
    """Remove an item from the collection state."""
    meta = _get_meta_store(form_key)
    state = meta.get(field_key, {})
    if "ids" in state and item_id in state["ids"]:
        state["ids"].remove(item_id)
        if "values" in state and item_id in state["values"]:
            del state["values"][item_id]


# --- Predicates ---


def is_numeric(t: Any) -> bool:
    return t in (int, float, Decimal)


def is_string_like(t: Any) -> bool:
    return t in (str, EmailStr, AnyUrl, SecretStr)


def is_enum(t: Any) -> bool:
    return isinstance(t, type) and issubclass(t, Enum)


def is_literal(t: Any) -> bool:
    return get_origin(t) is Literal


def is_datetime_type(t: Any) -> bool:
    return t in (datetime, date, time)


def is_timedelta(t: Any) -> bool:
    return t is timedelta


def is_bool(t: Any) -> bool:
    return t is bool


def is_list_origin(t: Any) -> bool:
    return get_origin(t) in (list, set, tuple)


def is_dict_origin(t: Any) -> bool:
    return get_origin(t) is dict or t is dict


def is_pydantic_model(t: Any) -> bool:
    return isinstance(t, type) and issubclass(t, BaseModel)


def is_union(t: Any) -> bool:
    origin = get_origin(t)
    return origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)


def is_none_type(t: Any) -> bool:
    return t is None or t is type(None)


# --- Renderers ---


@register(is_bool)
def render_bool(ctx: RenderContext, _: Any) -> bool:
    default = get_default_value(ctx, bool)
    return st.checkbox(
        ctx.label,
        value=bool(default),
        key=ctx.key,
        help=ctx.description or "Toggle value",
    )


@register(is_string_like)
def render_string(ctx: RenderContext, type_: Any) -> str | SecretStr:
    default = get_default_value(ctx, type_)
    if type_ is SecretStr:
        val = st.text_input(
            ctx.label,
            value=str(default) if default else "",
            type="password",
            key=ctx.key,
            help=ctx.description or "Enter secret value",
        )
        return SecretStr(val) if val else SecretStr("")

    return st.text_input(
        ctx.label,
        value=str(default),
        key=ctx.key,
        help=ctx.description or "Enter text",
    )


@register(is_numeric)
def render_number(ctx: RenderContext, type_: Any) -> int | float | Decimal:
    default = get_default_value(ctx, type_)
    constraints = ctx.field_info.json_schema_extra or {}
    if not isinstance(constraints, dict):
        constraints = {}

    min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
    max_val = constraints.get("maximum") or constraints.get("exclusiveMaximum")

    # Cast constraints
    min_v = float(min_val) if min_val is not None and isinstance(min_val, (int, float, str, Decimal)) else None
    max_v = float(max_val) if max_val is not None and isinstance(max_val, (int, float, str, Decimal)) else None

    step = 1 if type_ is int else 0.01
    val = default

    # Clamp value
    if min_v is not None and val < min_v:
        val = min_v
    if max_v is not None and val > max_v:
        val = max_v

    if min_v is not None and max_v is not None:
        result = st.slider(
            ctx.label,
            min_value=int(min_v) if type_ is int else min_v,
            max_value=int(max_v) if type_ is int else max_v,
            value=int(val) if type_ is int else float(val),
            step=step,
            key=ctx.key,
            help=ctx.description or "Select value",
        )
    else:
        result = st.number_input(
            ctx.label,
            value=int(val) if type_ is int else float(val),
            step=step,
            key=ctx.key,
            help=ctx.description or "Enter number",
        )

    if type_ is Decimal:
        return Decimal(str(result))
    return result


@register(is_enum)
def render_enum(ctx: RenderContext, type_: type[Enum]) -> Any:
    default = get_default_value(ctx, type_)
    options = [e.value for e in type_]
    idx = options.index(default) if default in options else 0
    return st.selectbox(
        ctx.label,
        options=options,
        index=idx,
        key=ctx.key,
        help=ctx.description or "Select an option",
    )


@register(is_literal)
def render_literal(ctx: RenderContext, type_: Any) -> Any:
    default = get_default_value(ctx, type_)
    options = get_args(type_)
    idx = options.index(default) if default in options else 0
    return st.selectbox(
        ctx.label,
        options=options,
        index=idx,
        key=ctx.key,
        help=ctx.description or "Select an option",
    )


@register(is_datetime_type)
def render_datetime(ctx: RenderContext, type_: Any) -> datetime | date | time | None:
    default = get_default_value(ctx, type_)

    if type_ is date:
        return st.date_input(ctx.label, value=default, key=ctx.key, help=ctx.description)

    if type_ is time:
        return st.time_input(ctx.label, value=default, key=ctx.key, help=ctx.description)

    if type_ is datetime:
        d_val = default.date() if isinstance(default, datetime) else None
        t_val = default.time() if isinstance(default, datetime) else None

        c1, c2 = st.columns(2)
        with c1:
            d = st.date_input(f"{ctx.label} (Date)", value=d_val, key=f"{ctx.key}_date")
        with c2:
            t = st.time_input(f"{ctx.label} (Time)", value=t_val, key=f"{ctx.key}_time")

        if d and t:
            return datetime.combine(d, t)
        return None
    return None


@register(is_timedelta)
def render_timedelta(ctx: RenderContext, type_: Any) -> Any:
    default = get_default_value(ctx, type_)
    default_str = str(default) if default is not None else ""

    val = st.text_input(
        ctx.label,
        value=default_str,
        key=ctx.key,
        help=ctx.description or "Enter duration in seconds (e.g., 3600) or ISO 8601 format (e.g., P1DT2H30M)",
    )
    if val:
        try:
            return timedelta(seconds=int(val))
        except ValueError:
            pass
        return val
    return None


@register(is_list_origin)
def render_list(ctx: RenderContext, type_: Any) -> list[Any]:
    args = get_args(type_)
    item_type = args[0] if args else str

    # Handle Enum/Literal multiselect optimization
    resolved_item_type, _ = resolve_type(item_type)
    if is_enum(resolved_item_type) or is_literal(resolved_item_type):
        return _render_multiselect(ctx, resolved_item_type)

    st.markdown(f"**{ctx.label}**")
    if ctx.description:
        st.caption(ctx.description)

    # State Abstraction
    item_ids, values_map = get_collection_state(ctx.form_key, ctx.key, ctx.current_value or [])

    if st.button(f"Add {ctx.label}", key=f"{ctx.key}_add"):
        # Calculate default for new item
        dummy_ctx = RenderContext("", "", FieldInfo(), None, form_key=ctx.form_key)
        new_default = get_default_value(dummy_ctx, item_type)
        add_collection_item(ctx.form_key, ctx.key, new_default)
        st.rerun()

    results = []
    to_remove = []

    for i, item_id in enumerate(item_ids):
        val = values_map.get(item_id)

        c1, c2 = st.columns([0.9, 0.1])
        with c1:
            sub_ctx = ctx.sub_context(
                f"Item {i + 1}",
                FieldInfo(annotation=item_type),
                val,
                key=f"{ctx.key}_{item_id}",
            )
            new_val = dispatch_field(sub_ctx)
            values_map[item_id] = new_val  # Update state with rendered value
            results.append(new_val)

        with c2:
            if st.button(":material/delete:", key=f"{ctx.key}_{item_id}_del"):
                to_remove.append(item_id)

    if to_remove:
        for mid in to_remove:
            remove_collection_item(ctx.form_key, ctx.key, mid)
        st.rerun()

    return results


def _render_multiselect(ctx: RenderContext, item_type: Any) -> list[Any]:
    options = []
    if is_enum(item_type):
        options = [e.value for e in item_type]
    elif is_literal(item_type):
        options = list(get_args(item_type))

    current = ctx.current_value if isinstance(ctx.current_value, list) else []
    default = [x for x in current if x in options]

    return st.multiselect(
        ctx.label,
        options=options,
        default=default,
        key=ctx.key,
        help=ctx.description,
    )


@register(is_dict_origin)
def render_dict(ctx: RenderContext, type_: Any) -> dict:
    args = get_args(type_)
    if not args or len(args) != 2:
        # Fallback for untyped dicts
        return _render_json_dict(ctx)

    key_type, value_type = args

    st.markdown(f"**{ctx.label}**")
    if ctx.description:
        st.caption(ctx.description)

    item_ids, values_map = get_collection_state(ctx.form_key, ctx.key, ctx.current_value or {})

    if st.button(f"Add {ctx.label}", key=f"{ctx.key}_add"):
        dummy_ctx = RenderContext("", "", FieldInfo(), None, form_key=ctx.form_key)
        k_def = get_default_value(dummy_ctx, key_type)
        v_def = get_default_value(dummy_ctx, value_type)
        add_collection_item(ctx.form_key, ctx.key, {"key": k_def, "value": v_def})
        st.rerun()

    to_remove = []

    for _, row_id in enumerate(item_ids):
        row_data = values_map.get(row_id)
        if not row_data:
            continue

        c1, c2, c3 = st.columns([0.4, 0.5, 0.1])

        with c1:
            k_ctx = ctx.sub_context(
                "Key",
                FieldInfo(annotation=key_type),
                row_data["key"],
                key=f"{ctx.key}_{row_id}_key",
            )
            row_data["key"] = dispatch_field(k_ctx)

        with c2:
            v_ctx = ctx.sub_context(
                "Value",
                FieldInfo(annotation=value_type),
                row_data["value"],
                key=f"{ctx.key}_{row_id}_value",
            )
            row_data["value"] = dispatch_field(v_ctx)

        with c3:
            if st.button(":material/delete:", key=f"{ctx.key}_{row_id}_del"):
                to_remove.append(row_id)

    if to_remove:
        for mid in to_remove:
            remove_collection_item(ctx.form_key, ctx.key, mid)
        st.rerun()

    # Reconstruct dict
    final_dict = {}
    for row_id in item_ids:
        row = values_map[row_id]
        try:
            hash(row["key"])
            final_dict[row["key"]] = row["value"]
        except TypeError:
            pass
    return final_dict


def _render_json_dict(ctx: RenderContext) -> dict:
    default = get_default_value(ctx, dict)
    display_val = json.dumps(default, indent=2) if isinstance(default, dict) else "{}"
    val = st.text_area(ctx.label, value=display_val, key=ctx.key, help=ctx.description)
    if val:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            st.error(f"Invalid JSON for {ctx.label}")
    return {}


@register(is_pydantic_model)
def render_model(ctx: RenderContext, model_type: type[BaseModel]) -> dict:
    # Use expander for nested models
    with st.expander(ctx.label, expanded=True):
        if ctx.description:
            st.caption(ctx.description)

        data = {}
        nested_val = (
            ctx.current_value.model_dump() if isinstance(ctx.current_value, BaseModel) else (ctx.current_value or {})
        )

        for name, info in model_type.model_fields.items():
            sub_ctx = ctx.sub_context(name, info, nested_val.get(name))
            data[name] = dispatch_field(sub_ctx)
        return data


@register(is_union)
def render_union(ctx: RenderContext, type_: Any) -> Any:
    args = get_args(type_)
    options = list(args)

    if not options:
        return None

    # Type selection state
    meta = _get_meta_store(ctx.form_key)
    type_key = f"{ctx.key}_type_idx"

    # Heuristic to guess initial type index based on value
    if type_key not in meta:
        inferred_idx = 0
        if ctx.current_value is not None:
            for i, t in enumerate(options):
                # Check compatibility
                if (is_pydantic_model(t) and isinstance(ctx.current_value, (dict, t))) or (
                    isinstance(t, type) and isinstance(ctx.current_value, t)
                ):
                    inferred_idx = i
                    break
        meta[type_key] = inferred_idx

    # Map types to labels
    type_map = {}
    for arg in options:
        origin = get_origin(arg)
        if origin is list:
            inner_args = get_args(arg)
            if inner_args:
                inner_type = inner_args[0]
                inner_name = inner_type.__name__ if isinstance(inner_type, type) else str(inner_type)
                label = f"list[{inner_name}]"
            else:
                label = "list"
        elif isinstance(arg, type):
            label = arg.__name__
        else:
            label = str(arg)
        type_map[label] = arg

    type_labels = list(type_map.keys())
    selected_idx = meta[type_key]

    selected_label = st.radio(
        f"Type for {ctx.label}",
        options=type_labels,
        index=selected_idx,
        key=f"{ctx.key}_selector",
        help=ctx.description or "Select the type to use",
        horizontal=True,
    )

    # Update state if changed
    new_idx = type_labels.index(selected_label)
    if new_idx != selected_idx:
        meta[type_key] = new_idx
        st.rerun()
    selected_type = options[new_idx]

    # Ensure value compatibility when switching types
    compatible_value = ctx.current_value
    is_compatible = False
    if compatible_value is not None and (
        (is_pydantic_model(selected_type) and isinstance(compatible_value, (dict, selected_type)))
        or (isinstance(selected_type, type) and isinstance(compatible_value, selected_type))
    ):
        is_compatible = True

    if not is_compatible:
        compatible_value = None

    sub_ctx = ctx.sub_context(
        ctx.field_name,
        FieldInfo(annotation=selected_type),
        compatible_value,
        key=f"{ctx.key}_{selected_label}",
    )
    return dispatch_field(sub_ctx)


@register(is_none_type)
def render_none(ctx: RenderContext, _: Any) -> None:
    st.write(f"**{ctx.label}**: `None`")
    return


# --- Main Dispatcher ---


def dispatch_field(ctx: RenderContext) -> Any:
    """
    Main entry point for rendering a field.
    Handles Optional wrapping and delegates to the registry.
    """
    base_type, is_optional = resolve_type(ctx.field_info.annotation)

    if is_optional:
        # Construct options including None
        options = []
        if is_union(base_type):
            options.extend(get_args(base_type))
        else:
            options.append(base_type)
        options.append(type(None))

        # Type selection state
        meta = _get_meta_store(ctx.form_key)
        type_key = f"{ctx.key}_opt_type_idx"

        # Heuristic to guess initial type index based on value
        if type_key not in meta:
            inferred_idx = 0
            if ctx.current_value is not None:
                for i, t in enumerate(options):
                    if is_none_type(t):
                        continue
                    # Check compatibility
                    if (is_pydantic_model(t) and isinstance(ctx.current_value, (dict, t))) or (
                        isinstance(t, type) and isinstance(ctx.current_value, t)
                    ):
                        inferred_idx = i
                        break
            meta[type_key] = inferred_idx

        # Map types to labels
        type_map = {}
        for arg in options:
            if is_none_type(arg):
                label = "None"
            else:
                origin = get_origin(arg)
                if origin is list:
                    inner_args = get_args(arg)
                    if inner_args:
                        inner_type = inner_args[0]
                        inner_name = inner_type.__name__ if isinstance(inner_type, type) else str(inner_type)
                        label = f"list[{inner_name}]"
                    else:
                        label = "list"
                elif isinstance(arg, type):
                    label = arg.__name__
                else:
                    label = str(arg)
            type_map[label] = arg

        type_labels = list(type_map.keys())
        selected_idx = meta[type_key]

        # Ensure index is valid
        if selected_idx >= len(type_labels):
            selected_idx = 0

        selected_label = st.radio(
            f"{ctx.label}",
            options=type_labels,
            index=selected_idx,
            key=f"{ctx.key}_opt_selector",
            help=ctx.description or "Select the type to use",
            horizontal=True,
        )

        # Update state if changed
        new_idx = type_labels.index(selected_label)
        if new_idx != selected_idx:
            meta[type_key] = new_idx
            st.rerun()

        selected_type = options[new_idx]

        if is_none_type(selected_type):
            return None

        # Ensure value compatibility when switching types
        compatible_value = ctx.current_value
        is_compatible = False
        if compatible_value is not None and (
            (is_pydantic_model(selected_type) and isinstance(compatible_value, (dict, selected_type)))
            or (isinstance(selected_type, type) and isinstance(compatible_value, selected_type))
        ):
            is_compatible = True

        if not is_compatible:
            compatible_value = None

        sub_ctx = ctx.sub_context(
            ctx.field_name,
            FieldInfo(annotation=selected_type),
            compatible_value,
            key=f"{ctx.key}_{selected_label}",
        )
        return dispatch_field(sub_ctx)

    # Find renderer in registry
    renderer = find_renderer(base_type)
    if renderer:
        return renderer(ctx, base_type)

    # Fallback
    return st.text_input(ctx.label, key=ctx.key, help=ctx.description)


# --- Public API ---


def render_pydantic_input[T: BaseModel](
    model: type[T],
    form_key: str = "pydantic_form",
    instance: T | None = None,
    *,
    container_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generates a Streamlit container from a Pydantic model class.
    """
    # Initialize State Container
    if form_key not in st.session_state:
        st.session_state[form_key] = {
            "data": instance.model_dump() if instance else {},
            "meta": {},
        }

    with st.container(**(container_kwargs or {})):
        st.subheader(f"{model.__name__} Form")

        current_data: dict[str, Any] = st.session_state[form_key]["data"]

        for name, info in model.model_fields.items():
            ctx = RenderContext(
                key=f"{form_key}_{name}",
                field_name=name,
                field_info=info,
                current_value=current_data.get(name),
                form_key=form_key,
            )
            # Update data in place with result from renderer
            current_data[name] = dispatch_field(ctx)

    return current_data


def render_pydantic_form[T: BaseModel](
    model: type[T],
    form_key: str = "pydantic_form",
    instance: T | None = None,
    *,
    container_kwargs: dict[str, Any] | None = None,
    button_kwargs: dict[str, Any] | None = None,
) -> T | None:
    if button_kwargs is None:
        button_kwargs = {"label": "Submit", "type": "primary", "key": f"{form_key}_submit"}

    result_data = render_pydantic_input(
        model,
        form_key=form_key,
        instance=instance,
        container_kwargs=container_kwargs,
    )

    # Debug view
    st.json(TypeAdapter(dict[str, Any]).dump_json(result_data).decode())

    if st.button(**button_kwargs):
        try:
            new_instance = model.model_validate(result_data)
        except ValidationError as e:
            st.error("Please correct the errors below:")
            for error in e.errors():
                st.error(error, icon="🚨")
            return None
        else:
            st.success("Validation Successful!")
            return new_instance

    return None
