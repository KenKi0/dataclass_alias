# dataclass_alias

Simple aliasing for dataclass working with orjson and ormsgpack 

## Usages

1. Default

```python
from dataclass_alias import AliasedDataclasses, asdict
from dataclasses import field, dataclass


@dataclass
class Data(metaclass=AliasedDataclasses, override_by_alias=True):
    my_field: str = field(metadata={"alias": "myField"})


instance = Data(my_field="field")
instance2 = Data(myField="field")  # or Data(**{"myField": "field"})
as_dict = asdict(instance2)
print(as_dict)
# Output: {"myField": "field"}
```

2. override_by_alias with False

```python
from dataclass_alias import AliasedDataclasses, asdict, alias
from dataclasses import field, dataclass


@dataclass
class Data(metaclass=AliasedDataclasses):
    my_field: str = field(metadata={"alias": "myField"})


instance2 = Data(myField="field")  # or Data(**{"myField": "field"})
as_dict = asdict(instance2)
print(as_dict)
# Output: {"my_field": "field"}
with alias(instance2):
    as_dict = asdict(instance2)
    print(as_dict)
    # Output: {"myField": "field"}
as_dict = asdict(instance2)
print(as_dict)
# Output: {"my_field": "field"}
```

3. With override_factory

Remember that if you use `alias` in metadate this alias will override alias from `alias_factory`

```python
from dataclass_alias import AliasedDataclasses, asdict
from dataclasses import field, dataclass


def to_lower_camel(string: str) -> str:
    if len(string) >= 1:
        pascal_string = ''.join(word.capitalize() for word in string.split('_'))
        return pascal_string[0].lower() + pascal_string[1:]
    return string.lower()


@dataclass
class Data(metaclass=AliasedDataclasses, alias_factory=to_lower_camel, override_by_alias=True):
    my_field: str = field(metadata={"alias": "MyField"})
    my_other_field: str

    
instance2 = Data(my_field="field", my_other_field="other_field")  # or Data(**{"MyField": "field"})
as_dict = asdict(instance2)
print(as_dict)
# Output: {"MyField": "field", "myOtherField": "other_field"}
```

4. Working with other serialize libraries

This implementation will work with libraries as orjson, ormsgpack

```python
import orjson
from dataclass_alias import AliasedDataclasses, asdict
from dataclasses import field, dataclass


@dataclass
class Data(metaclass=AliasedDataclasses, override_by_alias=True):
    my_field: str = field(metadata={"alias": "myField"})


instance = Data(my_field="field")
instance2 = Data(myField="field")  # or Data(**{"myField": "field"})
dump = orjson.dumps(instance2)
print(dump)
# Output: b'{"myField":"field"}'
```

5. Inheritance

```python
from dataclass_alias import AliasedDataclasses, asdict
from dataclasses import field, dataclass


@dataclass
class BaseAlias(metaclass=AliasedDataclasses, override_by_alias=True):
    ...


@dataclass
class Data(BaseAlias):
    my_field: str = field(metadata={"alias": "myField"})

    
@dataclass
class DataChild(Data):
    my_other_field: str = field(metadata={"alias": "myOtherField"})

    
instance = DataChild(my_field="field", my_other_field="other_field")
as_dict = asdict(instance)
print(as_dict)
# Output: {"myField": "field", "myOtherField": "other_field"}
```
