import builtins
import json
import types
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

import orjson
import streamlit as st
from pydantic import AnyUrl, BaseModel, EmailStr, SecretStr, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

T = TypeVar("T", bound=BaseModel)


@dataclass
class RenderContext:
    """Context object passed to all renderers containing field state."""

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


# --- Registry for Custom Renderers ---
Renderer = Callable[[RenderContext, Any], Any]
_RENDERER_REGISTRY: dict[Any, Renderer] = {}


def register_renderer(type_: Any, renderer: Renderer) -> None:
    """Register a custom renderer for a specific type."""
    _RENDERER_REGISTRY[type_] = renderer


# --- Type Resolution & Helpers ---


def _resolve_type(annotation: Any) -> tuple[Any, bool]:
    """
    Recursively resolves the base type and checks for optionality.
    Handles Annotated, Union, Optional.
    Returns (base_type, is_optional)
    """
    # Handle TypeAliasType (Python 3.12+)
    if hasattr(annotation, "__value__") and type(annotation).__name__ == "TypeAliasType":
        return _resolve_type(annotation.__value__)

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Handle Annotated (unwrap and recurse)
    if origin is Annotated:
        return _resolve_type(args[0])

    # Handle Union / Optional
    if (origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)) and type(None) in args:
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            # Standard Optional[T] -> T
            base, _ = _resolve_type(non_none_args[0])
            return base, True
        # Union[A, B, None] -> Union[A, B]
        union_type: Any = non_none_args[0]
        for candidate in non_none_args[1:]:
            union_type = union_type | candidate
        return union_type, True

    return annotation, False


def _get_default_value(ctx: RenderContext, field_type: Any) -> Any:
    """Determine the default value for a widget."""
    if ctx.current_value is not None:
        return ctx.current_value

    if ctx.field_info.default is not PydanticUndefined:
        return ctx.field_info.default

    field_type, _ = _resolve_type(field_type)

    # Fallbacks
    match field_type:
        case _ if field_type in (int, float, Decimal):
            constraints = ctx.field_info.json_schema_extra
            if not isinstance(constraints, dict):
                constraints = {}
            min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
            if min_val is not None and isinstance(min_val, (int, float, str)):
                return float(min_val) if field_type is float else int(min_val)
            return 0.0 if field_type is float else 0
        case _ if field_type in (str, EmailStr, AnyUrl, SecretStr):
            return ""
        case builtins.bool:
            return False
        case _ if field_type in (list, set):
            return []
        case _ if field_type is dict or get_origin(field_type) is dict:
            return {}

    return None


# --- Functional Renderers ---


def render_bool(ctx: RenderContext, _: Any) -> bool:
    default = _get_default_value(ctx, bool)
    return st.toggle(
        ctx.label,
        value=bool(default),
        key=ctx.key,
        help=ctx.description or "Toggle value",
    )


def render_string(ctx: RenderContext, type_: Any) -> str | SecretStr:
    default = _get_default_value(ctx, type_)
    if type_ is SecretStr:
        val = st.text_input(
            ctx.label,
            value=str(default),
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


def render_number(ctx: RenderContext, type_: Any) -> int | float | Decimal:
    default = _get_default_value(ctx, type_)
    constraints = ctx.field_info.json_schema_extra
    if not isinstance(constraints, dict):
        constraints = {}

    min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
    max_val = constraints.get("maximum") or constraints.get("exclusiveMaximum")

    step = 1 if type_ is int else 0.01

    # Cast constraints
    min_v = float(min_val) if min_val is not None and isinstance(min_val, (int, float, str)) else None
    max_v = float(max_val) if max_val is not None and isinstance(max_val, (int, float, str)) else None

    # Adjust default if out of bounds
    val = default
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


def render_enum(ctx: RenderContext, type_: type[Enum]) -> Any:
    default = _get_default_value(ctx, type_)
    options = [e.value for e in type_]
    idx = options.index(default) if default in options else 0
    return st.selectbox(
        ctx.label,
        options=options,
        index=idx,
        key=ctx.key,
        help=ctx.description or "Select an option",
    )


def render_literal(ctx: RenderContext, type_: Any) -> Any:
    default = _get_default_value(ctx, type_)
    options = get_args(type_)
    idx = options.index(default) if default in options else 0
    return st.selectbox(
        ctx.label,
        options=options,
        index=idx,
        key=ctx.key,
        help=ctx.description or "Select an option",
    )


def render_datetime(ctx: RenderContext, type_: Any) -> datetime | date | time | None:
    default = _get_default_value(ctx, type_)

    if type_ is date:
        return st.date_input(
            ctx.label,
            value=default,
            key=ctx.key,
            help=ctx.description or "Select date",
        )

    if type_ is time:
        return st.time_input(
            ctx.label,
            value=default,
            key=ctx.key,
            help=ctx.description or "Select time",
        )

    if type_ is datetime:
        d_val = default.date() if isinstance(default, datetime) else None
        t_val = default.time() if isinstance(default, datetime) else None

        c1, c2 = st.columns(2)
        with c1:
            d = st.date_input(
                f"{ctx.label} (Date)",
                value=d_val,
                key=f"{ctx.key}_date",
                help=ctx.description or "Select date",
            )
        with c2:
            t = st.time_input(f"{ctx.label} (Time)", value=t_val, key=f"{ctx.key}_time", help="Select time")

        if d and t:
            return datetime.combine(d, t)
        return None
    return None


def _render_multiselect(ctx: RenderContext, item_type: Any) -> list[Any]:
    options = []
    if isinstance(item_type, type) and issubclass(item_type, Enum):
        options = [e.value for e in item_type]
    elif get_origin(item_type) is Literal:
        options = list(get_args(item_type))

    current = ctx.current_value if isinstance(ctx.current_value, list) else []
    # Filter default values to ensure they are in options
    default = [x for x in current if x in options]

    return st.multiselect(
        ctx.label,
        options=options,
        default=default,
        key=ctx.key,
        help=ctx.description or "Select options",
    )


def render_list(ctx: RenderContext, type_: Any) -> list[Any]:
    args = get_args(type_)
    item_type = args[0] if args else str

    resolved_item_type, _ = _resolve_type(item_type)

    # Check if item_type is a Pydantic Model
    if isinstance(resolved_item_type, type) and issubclass(resolved_item_type, BaseModel):
        return _render_model_list(ctx, resolved_item_type)

    # Check for Enum or Literal -> Multiselect
    is_enum = isinstance(resolved_item_type, type) and issubclass(resolved_item_type, Enum)
    is_literal = get_origin(resolved_item_type) is Literal

    if is_enum or is_literal:
        return _render_multiselect(ctx, resolved_item_type)

    return _render_primitive_list(ctx, item_type)


def _render_primitive_list(ctx: RenderContext, item_type: Any) -> list[Any]:
    st.markdown(f"**{ctx.label}**")
    if ctx.description:
        st.caption(ctx.description)

    items = ctx.current_value if isinstance(ctx.current_value, list) else []

    # State management
    meta = st.session_state[ctx.form_key].setdefault("meta", {})

    if ctx.key not in meta:
        meta[ctx.key] = {}

    list_state = meta[ctx.key]

    if "ids" not in list_state:
        initial_ids = [str(uuid.uuid4()) for _ in items]
        list_state["ids"] = initial_ids
        list_state["values"] = dict(zip(initial_ids, items, strict=False))

    item_ids = list_state["ids"]
    initial_values = list_state["values"]

    if st.button("Add Item", key=f"{ctx.key}_add"):
        new_id = str(uuid.uuid4())
        list_state["ids"].append(new_id)

        # Get default for primitive
        dummy_ctx = RenderContext("", "", FieldInfo(), None, form_key=ctx.form_key)
        list_state["values"][new_id] = _get_default_value(dummy_ctx, item_type)
        st.rerun()

    results = []
    to_remove = []

    for i, item_id in enumerate(item_ids):
        val = initial_values.get(item_id)

        c1, c2 = st.columns([0.9, 0.1])
        with c2:
            if st.button(":material/delete:", key=f"{ctx.key}_{item_id}_del", help="Remove item"):
                to_remove.append(item_id)

        with c1:
            # Create sub-context for the primitive item
            sub_ctx = ctx.sub_context(
                f"Item {i + 1}",
                FieldInfo(annotation=item_type),
                val,
                key=f"{ctx.key}_{item_id}",
            )
            # Render
            new_val = dispatch_field(sub_ctx)
            results.append(new_val)
            list_state["values"][item_id] = new_val

    if to_remove:
        for mid in to_remove:
            if mid in list_state["ids"]:
                list_state["ids"].remove(mid)
                if mid in list_state["values"]:
                    del list_state["values"][mid]
        st.rerun()

    return results


def _render_model_list(
    ctx: RenderContext,
    item_model: type[BaseModel],
) -> list[BaseModel]:
    st.markdown(f"**{ctx.label}**")
    if ctx.description:
        st.caption(ctx.description)

    items = ctx.current_value if isinstance(ctx.current_value, list) else []

    # State management
    meta = st.session_state[ctx.form_key].setdefault("meta", {})

    if ctx.key not in meta:
        meta[ctx.key] = {}

    list_state = meta[ctx.key]

    if "ids" not in list_state:
        initial_ids = [str(uuid.uuid4()) for _ in items]
        list_state["ids"] = initial_ids
        list_state["values"] = dict(zip(initial_ids, items, strict=False))

    item_ids = list_state["ids"]
    initial_values = list_state["values"]

    if st.button(f"Add {item_model.__name__}", key=f"{ctx.key}_add"):
        new_id = str(uuid.uuid4())
        list_state["ids"].append(new_id)
        list_state["values"][new_id] = None
        st.rerun()

    results = []
    to_remove = []

    for i, item_id in enumerate(item_ids):
        val = initial_values.get(item_id)

        c1, c2 = st.columns([0.9, 0.1])
        with c2:
            if st.button(":material/delete:", key=f"{ctx.key}_{item_id}_del"):
                to_remove.append(item_id)

        with c1, st.expander(f"{item_model.__name__} #{i + 1}", expanded=True):
            # Recursive call
            model_data = {}
            model_val = val.model_dump() if isinstance(val, BaseModel) else (val or {})

            for name, info in item_model.model_fields.items():
                sub_ctx = ctx.sub_context(
                    name,
                    info,
                    model_val.get(name),
                    key=f"{ctx.key}_{item_id}_{name}",
                )
                model_data[name] = dispatch_field(sub_ctx)

            results.append(model_data)

    if to_remove:
        for mid in to_remove:
            if mid in list_state["ids"]:
                list_state["ids"].remove(mid)
                if mid in list_state["values"]:
                    del list_state["values"][mid]
        st.rerun()

    return results


def render_dict(ctx: RenderContext, _: Any) -> dict:
    default = _get_default_value(ctx, dict)
    display_val = json.dumps(default, indent=2) if isinstance(default, dict) else "{}"

    val = st.text_area(
        ctx.label,
        value=display_val,
        key=ctx.key,
        help=f"{ctx.description} (JSON)" if ctx.description else "Enter JSON object",
    )

    if val:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            st.error(f"Invalid JSON for {ctx.label}")
    return {}


def render_nested_model(ctx: RenderContext, model_type: type[BaseModel]) -> dict:
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


def render_union(ctx: RenderContext, type_: Any) -> Any:
    args = get_args(type_)
    # Filter out NoneType
    options = [arg for arg in args if arg is not type(None)]

    if not options:
        return None

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
    selector_key = f"{ctx.key}_type_selector"

    # Determine current type index
    current_type_idx = 0

    # Priority: Widget State > Data Inference
    if selector_key in st.session_state and st.session_state[selector_key] in type_labels:
        current_type_idx = type_labels.index(st.session_state[selector_key])
    elif ctx.current_value is not None:
        for i, (_, t) in enumerate(type_map.items()):
            # Check for Pydantic models
            if isinstance(t, type) and issubclass(t, BaseModel):
                if isinstance(ctx.current_value, (dict, t)):
                    current_type_idx = i
                    break
            # Check for primitives
            elif isinstance(t, type) and isinstance(ctx.current_value, t):
                current_type_idx = i
                break

    selected_label = st.segmented_control(
        f"Type for {ctx.label}",
        options=type_labels,
        default=type_labels[current_type_idx],
        key=selector_key,
        help=f"Select type for {ctx.label}",
    )

    if selected_label is None:
        selected_label = type_labels[current_type_idx]

    selected_type = type_map[selected_label]

    # Check compatibility of current value
    compatible_value = ctx.current_value
    is_compatible = False
    if compatible_value is not None:
        if isinstance(selected_type, type) and issubclass(selected_type, BaseModel):
            if isinstance(compatible_value, (dict, selected_type)):
                is_compatible = True
        elif isinstance(selected_type, type) and isinstance(compatible_value, selected_type):
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


def dispatch_field(ctx: RenderContext) -> Any:
    """Dispatches rendering to the appropriate function based on type."""
    base_type, is_optional = _resolve_type(ctx.field_info.annotation)

    # Handle Optional wrapper
    if is_optional:
        # Use a checkbox to toggle presence
        is_checked = ctx.current_value is not None

        enable = st.checkbox(
            f"Include {ctx.label}",
            value=is_checked,
            key=f"{ctx.key}_opt_check",
            help=f"Enable {ctx.label}",
        )

        if not enable:
            return None

        return _dispatch_base(ctx, base_type)

    return _dispatch_base(ctx, base_type)


def _dispatch_base(ctx: RenderContext, type_: Any) -> Any:
    # Check registry first
    if type_ in _RENDERER_REGISTRY:
        return _RENDERER_REGISTRY[type_](ctx, type_)

    origin = get_origin(type_)

    # Match statement for dispatch
    match type_:
        case _ if origin is Literal:
            return render_literal(ctx, type_)
        case _ if origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):
            return render_union(ctx, type_)
        case _ if origin in (list, set, tuple):
            return render_list(ctx, type_)
        case _ if origin is dict or type_ is dict:
            return render_dict(ctx, type_)
        case _ if isinstance(type_, type) and issubclass(type_, Enum):
            return render_enum(ctx, type_)
        case _ if isinstance(type_, type) and issubclass(type_, BaseModel):
            return render_nested_model(ctx, type_)
        case builtins.bool:
            return render_bool(ctx, type_)
        case builtins.int | builtins.float:
            return render_number(ctx, type_)
        case _ if type_ is Decimal:
            return render_number(ctx, type_)
        case builtins.str:
            return render_string(ctx, type_)
        case _ if type_ in (EmailStr, AnyUrl, SecretStr):
            return render_string(ctx, type_)
        case _ if type_ is date:
            return render_datetime(ctx, date)
        case _ if type_ is time:
            return render_datetime(ctx, time)
        case _ if type_ is datetime:
            return render_datetime(ctx, datetime)
        case _ if type_ is timedelta:
            # Fallback to string for timedelta
            return render_string(ctx, str)
        case _:
            # Fallback
            return st.text_input(
                ctx.label,
                key=ctx.key,
                help=ctx.description or "Enter value",
            )


# --- Main Entry Point ---


def render_pydantic_input[T: BaseModel](
    model: type[T],
    form_key: str = "pydantic_form",
    instance: T | None = None,
) -> dict:
    """
    Generates a Streamlit container from a Pydantic model class.

    Args:
        model: The Pydantic model class (not an instance).
        form_key: Unique key for the widgets.
        instance: An optional existing instance to pre-fill the form (Edit mode).

    Returns:
        An instance of the model if submitted and valid, otherwise None.
    """
    if form_key not in st.session_state:
        st.session_state[form_key] = {
            "data": instance.model_dump() if instance else {},
            "meta": {},
        }

    # Ensure structure
    if not isinstance(st.session_state[form_key], dict) or "data" not in st.session_state[form_key]:
        # Fallback if state was initialized differently (e.g. old version)
        # We wrap it.
        old_data = st.session_state[form_key]
        st.session_state[form_key] = {
            "data": old_data if isinstance(old_data, dict) else {},
            "meta": {},
        }

    with st.container():
        st.subheader(f"{model.__name__} Form")

        # form_data = {}

        for name, info in model.model_fields.items():
            ctx = RenderContext(
                key=f"{form_key}_{name}",
                field_name=name,
                field_info=info,
                current_value=st.session_state[form_key]["data"].get(name),
                form_key=form_key,
            )
            st.session_state[form_key]["data"][name] = dispatch_field(ctx)

    return st.session_state[form_key]["data"]


def render_pydantic_form[T: BaseModel](
    model: type[T],
    form_key: str = "pydantic_form",
    instance: T | None = None,
    *,
    button_kwargs: dict[str, Any] | None = None,
) -> T | None:
    if button_kwargs is None:
        button_kwargs = {"label": "Submit", "type": "primary", "key": f"{form_key}_submit"}

    result = render_pydantic_input(model, form_key=form_key, instance=instance)

    if st.button(**button_kwargs):
        try:
            new_instance = model.model_validate(result)
        except ValidationError as e:
            st.error("Please correct the errors below:")
            for error in e.errors():
                fmt_str = orjson.dumps(error, option=orjson.OPT_INDENT_2).decode()
                st.error(f"```json\n{fmt_str}\n```", icon="🚨")
            return None
        else:
            st.success("Validation Successful!")
            return new_instance

    return None
