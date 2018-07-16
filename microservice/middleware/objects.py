import json
import logging
from collections import UserDict, UserList
from copy import copy

from microservice.exceptions import ApiError, CriticalError


class SerializableMixin:
    def list(self, l=None):
        """return raw list"""
        raw_list = []
        for v in l if l is not None else self:
            if isinstance(v, BasicObject):
                raw_list.append(v.dict(v))
            elif isinstance(v, Collection):
                raw_list.append(v.list(v))
            elif isinstance(v, dict):
                raw_list.append(self.dict(v))
            elif isinstance(v, list):
                raw_list.append(self.list(v))
            else:
                raw_list.append(v)
        return raw_list

    def dict(self, d=None):
        """return raw dict"""
        raw_dict = {}
        for k, v in d.items() if d is not None else self.items():
            if isinstance(v, BasicObject):
                raw_dict[k] = v.dict(v)
            elif isinstance(v, Collection):
                raw_dict[k] = v.list(v)
            elif isinstance(v, dict):
                raw_dict[k] = self.dict(v)
            elif isinstance(v, list):
                raw_dict[k] = self.list(v)
            else:
                raw_dict[k] = v
        return raw_dict

    def json(self):
        if isinstance(self, BasicObject):
            return json.dumps(self.dict())
        elif isinstance(self, Collection):
            return json.dumps(self.list())

    @classmethod
    def from_json(cls, s):
        return cls(json.loads(s))

    def __repr__(self):
        return self.json()

    def __str__(self):
        return self.json()


class BasicObject(UserDict, SerializableMixin):
    def __init__(self, item_dict: dict, obj=None):
        super(BasicObject, self).__init__()  # empty until validated
        self.input = item_dict
        self.validate()
        # after this moment self.data is validated and may be converted to object fields
        for key in self.data:
            if isinstance(self.data[key], dict):
                self.data[key] = BasicObject(self.data[key])
                # logging.warning("Nested object without class {}: {}".format(self.__class__.__name__, key))
            elif isinstance(self.data[key], list):
                self.data[key] = Collection(self.data[key])
                # logging.warning("Nested list without class {}: {}".format(self.__class__.__name__, key))
            setattr(self, key, self.data[key])
        self.model = None
        self.obj = obj

    def __setitem__(self, key, value):
        self.data[key] = value
        setattr(self, key, value)

    def validate(self):
        """implement it otherwise self.data will be filled from self.input directly"""
        self.data = self.input

    def valid(self, name, default=None, coerce=None, check=None, error="", required=False, allow_none=False):
        """
        Validate field and coerce it if needed. Each call fill self.data with new field.
        :param name: field name
        :param default: default value if name not presents in data
        :param coerce: coerce to type of function
        :param check: check function must return True if passed
        :param error: error text if any of checks not passed
        :param required: set True if field is required
        :param allow_none: set True if param may be None, else None values will be removed
        """
        value = self.input.get(name, default)
        if required and value in (None, ""):
            raise ApiError("#missing #field '{}' {}".format(name, error))
        if value is None:
            value = default
        if coerce and value is not None:
            try:
                value = coerce(value)
            except ValueError:
                raise ApiError("#wrong_type {}, expected {}. {}".format(name, coerce, error))
        if check and value is not None:
            if isinstance(check, (list, tuple)) and value not in check:
                raise ApiError("#wrong_format {} not in {}. {}".format(name, check, error))
            if callable(check) and not check(value):
                raise ApiError("#wrong_format {}. {}".format(name, error))
        # final
        if value is not None or allow_none:
            self.data[name] = value

    def set_model(self, model, obj=None):
        """if object have id, it may be saved to db (o rly?)"""
        self.model = model
        self.obj = obj or self.obj

    async def save(self):
        if not self.model or not self.obj:
            raise CriticalError("Model or objects manager is not set")
        if not self.get("id"):
            raise CriticalError("Object id is not set")
        model = self.model.from_dict(self.dict())
        await self.obj.update(model)

    def group_enum(self, enum_name, variants):
        """
        Group several boolean flags into one enum field
        :param enum_name: name of new field
        :param variants: flags
        """
        for var in variants:
            if getattr(self, var):
                self[enum_name] = var
                break

    def __sub__(self, other):
        """return dict with fields which is differs in self and other"""
        res = BasicObject({})
        for key in self:
            if self[key] != other.get(key):
                res[key] = self[key]
        return res


class Collection(UserList, SerializableMixin):
    object_class = None

    def __init__(self, items_list, object_class=None):
        self.object_class = object_class or self.object_class
        super(Collection, self).__init__(items_list)
        if self.object_class:
            self.set_class(self.object_class)
            self.valid = True
        else:
            self.valid = False
            # logging.warning("Collection object class is not set: {}".format(__name__))
        self._ix = None

    def set_class(self, object_class):
        self.object_class = object_class
        if all([isinstance(x, dict) for x in self.data]):
            self.data = [object_class(item) for item in self.data]

    @property
    def ix(self):
        if not self._ix and len(self) > 0 and self[0].get("id"):
            self._ix = {v["id"]: v for v in self}
        return self._ix

    def join(self, children, foreign_key, group_name):
        for i in self.data:
            i[group_name] = []
        for child in children:
            self.ix[child[foreign_key]][group_name].append(child)

    @classmethod
    def with_class(cls, object_class=None):
        new_cls = copy(cls)
        new_cls.object_class = object_class or BasicObject
        return new_cls

    def group_enum(self, enum_name, variants):
        """
        Group several boolean flags into one enum field
        :param enum_name: name of new field
        :param variants: flags
        """
        for item in self.data:
            item.group_enum(enum_name, variants)
