import copy
import types
from contextlib import contextmanager
from typing import Any, Callable
from dataclasses import Field

_ALIAS_MAP = "__alias_map__"
_ALIAS_FACTORY = "__alias_factory__"
_FIELDS = "__dataclass_fields__"
_OVERRIDE = "__override_by_alias__"
_OVERRIDE_FIELDS = (_FIELDS, "__dict__")



def _is_dataclass_instance(obj):
    """Returns True if obj is an instance of a dataclass."""
    return hasattr(type(obj), _FIELDS)

def _is_aliased_dataclass(obj):
    return hasattr(obj, _OVERRIDE)


def _asdict_inner(obj, dict_factory):
    if _is_dataclass_instance(obj):
        result = []
        for key, f in getattr(obj, _FIELDS, {}).items():
            value = _asdict_inner(getattr(obj, f.name), dict_factory)
            result.append((key, value))
        return dict_factory(result)
    elif isinstance(obj, tuple) and hasattr(obj, '_fields'):

        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)((_asdict_inner(k, dict_factory),
                          _asdict_inner(v, dict_factory))
                         for k, v in obj.items())
    else:
        return copy.deepcopy(obj)


def _patch_get_attribute(cls):
    # closure for super() because he need a __class__ variable in scope
    __class__ = cls
    def get_attribute(self, item: str) -> Any:
        override = super().__getattribute__(_OVERRIDE)
        if override and item in _OVERRIDE_FIELDS:
            fields = super().__getattribute__(_FIELDS)
            if item == _FIELDS:
                return {field.metadata["alias"]: field for field in fields.values()}
            dct = super().__getattribute__(item)
            return {field.metadata["alias"]: dct[field.name] for field in fields.values()}
        alias_map = super().__getattribute__(_ALIAS_MAP)
        if item in alias_map:
            return super().__getattribute__(alias_map[item])
        return super().__getattribute__(item)
    cls.__getattribute__ = get_attribute


def _patch_set_attribute(cls):
    __class__ = cls
    def set_attr(self, item: str, value: Any) -> None:
        alias_map = super().__getattribute__(_ALIAS_MAP)
        if item in alias_map:
            item = alias_map[item]
        super().__setattr__(item, value)
    cls.__setattr__ = set_attr



class AliasedDataclasses(type):

    def __new__(metacls, name, bases, namespace, alias_factory: Callable[[str], str] | None = None, override_by_alias: bool | None = None):
        alias_map = {}
        need_to_rename = False
        bases_fields = []
        base_alias_factory: Callable[[str], str] | None = None
        base_override_by_alias = False
        for base in bases:
            [bases_fields.extend(getattr(base_parent, "__annotations__", {})) for base_parent in base.__mro__]
            if base.__dict__.get(_ALIAS_MAP):
                alias_map.update(base.__dict__[_ALIAS_MAP])
            if base.__dict__.get(_ALIAS_FACTORY):
                if alias_factory is None:
                    if base_alias_factory is None:
                        base_alias_factory = base.__dict__.get(_ALIAS_FACTORY)
                    else:
                        need_to_rename = True
                else:
                    need_to_rename = True
            if base.__dict__.get(_OVERRIDE):
                base_override_by_alias = True
        if not alias_factory:
            alias_factory = base_alias_factory
        if need_to_rename:
            alias_map = {}
            for field in bases_fields:
                alias_map[alias_factory(field)] = field
        if override_by_alias is None:
            override_by_alias = base_override_by_alias
        for name, _ in namespace.get("__annotations__", {}).items():
            # if slots=True method __new__ will recall and __dataclass_fields__ will be in namespace
            if _FIELDS in namespace:
                field = namespace[_FIELDS][name]
            elif name in namespace and isinstance(namespace[name], Field):
                field = namespace[name]
            elif alias_factory:
                alias_map[alias_factory(name)] = name
                continue
            else:
                continue
            aliased_name = field.metadata.get("alias")
            if aliased_name:
                alias_map[aliased_name] = name
        namespace[_ALIAS_MAP] = alias_map
        namespace[_ALIAS_FACTORY] = alias_factory
        cls = super().__new__(metacls, name, bases, namespace)
        setattr(cls, _OVERRIDE, override_by_alias)
        _patch_get_attribute(cls)
        _patch_set_attribute(cls)
        return cls

    def __call__(cls, *args, **kwargs):
        if _FIELDS not in cls.__dict__:
            raise ValueError("Will be use only with dataclass")
        alias_map = cls.__dict__.get(_ALIAS_MAP)
        for alias, name in alias_map.items():
            if alias in kwargs:
                kwargs[name] = kwargs.pop(alias)
        instance = super().__call__(*args, **kwargs)
        setattr(instance, _OVERRIDE, cls.__dict__.get(_OVERRIDE, False))
        return instance

    def __setattr__(cls, key, value):
        if key == _FIELDS:
            alias_map = cls.__dict__.get(_ALIAS_MAP)
            visited = set()
            for alias, name in alias_map.items():
                field = value[name]
                new_metadata = {k: v for k, v in field.metadata.items()}
                new_metadata["alias"] = alias
                field.metadata = types.MappingProxyType(new_metadata)
                visited.add(name)
            for name, field in value.items():
                if name in visited:
                    continue
                new_metadata = {k: v for k, v in field.metadata.items()}
                new_metadata["alias"] = name
                field.metadata = types.MappingProxyType(new_metadata)
        super().__setattr__(key, value)


def asdict(obj, *, dict_factory=dict):
    """
    Our implementation of asdict from dataclasses
    """
    if not _is_dataclass_instance(obj):
        raise TypeError("asdict() should be called on dataclass instances")
    return _asdict_inner(obj, dict_factory)


@contextmanager
def alias(obj):
    if not _is_aliased_dataclass(obj):
        raise TypeError("alias should be used on aliased dataclass instances")
    setattr(obj, _OVERRIDE, True)
    yield
    setattr(obj, _OVERRIDE, False)