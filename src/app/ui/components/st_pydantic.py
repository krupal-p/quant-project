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
        # For now, we don't fully support complex Unions, just return the Union type marked optional
        return annotation, True

    return annotation, False


def _get_default_value(ctx: RenderContext, field_type: Any) -> Any:
    """Determine the default value for a widget."""
    if ctx.current_value is not None:
        return ctx.current_value

    if ctx.field_info.default is not PydanticUndefined:
        return ctx.field_info.default

    # Fallbacks
    match field_type:
        case _ if field_type in (int, float, Decimal):
            constraints = ctx.field_info.json_schema_extra or {}
            min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
            if min_val is not None:
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
        help=ctx.description,
    )


def render_string(ctx: RenderContext, type_: Any) -> str | SecretStr:
    default = _get_default_value(ctx, type_)
    if type_ is SecretStr:
        val = st.text_input(
            ctx.label,
            value=str(default),
            type="password",
            key=ctx.key,
            help=ctx.description,
        )
        return SecretStr(val) if val else SecretStr("")

    return st.text_input(
        ctx.label,
        value=str(default),
        key=ctx.key,
        help=ctx.description,
    )


def render_number(ctx: RenderContext, type_: Any) -> int | float | Decimal:
    default = _get_default_value(ctx, type_)
    constraints = ctx.field_info.json_schema_extra or {}

    min_val = constraints.get("minimum") or constraints.get("exclusiveMinimum")
    max_val = constraints.get("maximum") or constraints.get("exclusiveMaximum")

    step = 1 if type_ is int else 0.01

    # Cast constraints
    min_v = float(min_val) if min_val is not None else None
    max_v = float(max_val) if max_val is not None else None

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
            help=ctx.description,
        )
    else:
        result = st.number_input(
            ctx.label,
            value=int(val) if type_ is int else float(val),
            step=step,
            key=ctx.key,
            help=ctx.description,
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
        help=ctx.description,
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
        help=ctx.description,
    )


def render_datetime(ctx: RenderContext, type_: Any) -> datetime | date | time | None:
    default = _get_default_value(ctx, type_)

    if type_ is date:
        return st.date_input(
            ctx.label,
            value=default,
            key=ctx.key,
            help=ctx.description,
        )

    if type_ is time:
        return st.time_input(
            ctx.label,
            value=default,
            key=ctx.key,
            help=ctx.description,
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
                help=ctx.description,
            )
        with c2:
            t = st.time_input(f"{ctx.label} (Time)", value=t_val, key=f"{ctx.key}_time")

        if d and t:
            return datetime.combine(d, t)
        return None
    return None


def render_list(ctx: RenderContext, type_: Any) -> list[Any]:
    args = get_args(type_)
    item_type = args[0] if args else str

    # Check if item_type is a Pydantic Model
    if isinstance(item_type, type) and issubclass(item_type, BaseModel):
        return _render_model_list(ctx, item_type)

    # Simple list (strings, ints, etc) - use text area for now as per original
    default = _get_default_value(ctx, type_)
    display_val = ", ".join(map(str, default)) if isinstance(default, (list, set)) else ""

    val = st.text_area(
        ctx.label,
        value=display_val,
        key=ctx.key,
        help=f"{ctx.description} (Comma-separated values)",
    )
    if val:
        return [item.strip() for item in val.split(",") if item.strip()]
    return []


def _render_model_list(
    ctx: RenderContext,
    item_model: type[BaseModel],
) -> list[BaseModel]:
    st.markdown(f"**{ctx.label}**")
    if ctx.description:
        st.caption(ctx.description)

    items = ctx.current_value if isinstance(ctx.current_value, list) else []

    # State management
    ids_key = f"{ctx.key}_ids"
    vals_key = f"{ctx.key}_values"

    if ids_key not in st.session_state:
        initial_ids = [str(uuid.uuid4()) for _ in items]
        st.session_state[ids_key] = initial_ids
        st.session_state[vals_key] = dict(zip(initial_ids, items, strict=False))

    item_ids = st.session_state[ids_key]
    initial_values = st.session_state[vals_key]

    if st.button(f"Add {item_model.__name__}", key=f"{ctx.key}_add"):
        new_id = str(uuid.uuid4())
        st.session_state[ids_key].append(new_id)
        st.session_state[vals_key][new_id] = None
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
            if mid in st.session_state[ids_key]:
                st.session_state[ids_key].remove(mid)
                if mid in st.session_state[vals_key]:
                    del st.session_state[vals_key][mid]
        st.rerun()

    return results


def render_dict(ctx: RenderContext, _: Any) -> dict:
    default = _get_default_value(ctx, dict)
    display_val = json.dumps(default, indent=2) if isinstance(default, dict) else "{}"

    val = st.text_area(
        ctx.label,
        value=display_val,
        key=ctx.key,
        help=f"{ctx.description} (JSON)",
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


# --- Dispatcher ---


def dispatch_field(ctx: RenderContext) -> Any:
    """Dispatches rendering to the appropriate function based on type."""
    base_type, is_optional = _resolve_type(ctx.field_info.annotation)

    # Handle Optional wrapper
    if is_optional:
        type_name = getattr(base_type, "__name__", str(base_type))
        opt_key = f"{ctx.key}_opt"

        # Use segmented control if available (Streamlit 1.38+)
        options = [type_name, "None"]
        if hasattr(st, "segmented_control"):
            sel = st.segmented_control(
                f"{ctx.label} (Optional)",
                options,
                default=type_name,
                key=opt_key,
            )
        else:
            sel = st.radio(
                f"{ctx.label} (Optional)",
                options,
                horizontal=True,
                key=opt_key,
            )

        if sel == "None":
            return None

        # Render actual field
        cols = st.columns([0.05, 0.95])
        with cols[1]:
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
        case _ if origin in (list, set):
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
                help=f"Unsupported type: {type_}",
            )


# --- Main Entry Point ---


def render_pydantic_form[T: BaseModel](
    model: type[T],
    form_key: str = "pydantic_form",
    instance: T | None = None,
) -> T | None:
    """
    Generates a Streamlit container from a Pydantic model class.

    Args:
        model: The Pydantic model class (not an instance).
        form_key: Unique key for the widgets.
        instance: An optional existing instance to pre-fill the form (Edit mode).

    Returns:
        An instance of the model if submitted and valid, otherwise None.
    """
    with st.container():
        st.subheader(f"{model.__name__} Form")

        form_data = {}
        instance_data = instance.model_dump() if instance else {}

        for name, info in model.model_fields.items():
            ctx = RenderContext(
                key=f"{form_key}_{name}",
                field_name=name,
                field_info=info,
                current_value=instance_data.get(name),
            )
            form_data[name] = dispatch_field(ctx)

        if st.button("Submit", key=f"{form_key}_submit"):
            try:
                new_instance = model(**form_data)
            except ValidationError as e:
                st.error("Validation Error")
                for error in e.errors():
                    loc = " -> ".join(str(loc_part) for loc_part in error["loc"])
                    st.error(f"**{loc}**: {error['msg']}")
                return None
            else:
                st.success("Validation Successful!")
                return new_instance

    return None
