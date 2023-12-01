# --------------------------------------------------------------------------------
# FastAPI PATCH to add query params to endpoints (until I figure out how to do it properly)
# https://github.com/tiangolo/fastapi/blob/1c46aa2d5242fcdcc8ebba20a53cfd473f4ee7bc/fastapi/dependencies/utils.py#L348

from enum import Enum
import functools
import inspect
from typing import Any, Optional, Type
import pydantic
from pydantic.schema import get_annotation_from_field_info

class ParamTypes(Enum):
    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"

def get_param_field(
    *,
    param: inspect.Parameter,
    param_name: str,
    default_field_info: Type[pydantic.fields.FieldInfo] = pydantic.fields.FieldInfo,
    force_type: Optional[ParamTypes] = None,
    ignore_default: bool = False,
) -> pydantic.fields.ModelField:
    default_value = pydantic.fields.Required
    had_schema = False
    if not param.default == param.empty and ignore_default is False:
        default_value = param.default
    if isinstance(default_value, pydantic.fields.FieldInfo):
        had_schema = True
        field_info = default_value
        default_value = field_info.default
        if (
            isinstance(field_info, pydantic.fields.FieldInfo)
            and getattr(field_info, "in_", None) is None
        ):
            field_info.in_ = default_field_info.in_
        if force_type:
            field_info.in_ = force_type  # type: ignore
    else:
        field_info = default_field_info(default_value)
    required = default_value == pydantic.fields.Required
    annotation: Any = Any
    if not param.annotation == param.empty:
        annotation = param.annotation

    annotation = get_annotation_from_field_info(annotation, field_info, param_name)

    if not field_info.alias and getattr(field_info, "convert_underscores", None):
        alias = param.name.replace("_", "-")
    else:
        alias = field_info.alias or param.name

    response_field = functools.partial(
        pydantic.fields.ModelField,
        name=param.name,
        type_=annotation,
        class_validators=None,
        default=None if required else default_value,
        required=required,
        model_config=pydantic.BaseConfig,
        alias=alias,
    )

    field = response_field(field_info=field_info)

    return field