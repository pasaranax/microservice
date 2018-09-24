import datetime
import json
import logging
from collections import UserDict, UserList
from datetime import datetime

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
            elif isinstance(v, datetime):
                raw_dict[k] = v.isoformat("T")
            else:
                raw_dict[k] = v
        return raw_dict

    def json(self):
        if isinstance(self, BasicObject):
            return json.dumps(self.dict())
        elif isinstance(self, Collection):
            return json.dumps(self.list())

    @staticmethod
    def from_json(s):
        o = json.loads(s)
        if isinstance(o, list):
            return Collection(o)
        elif isinstance(o, dict):
            return BasicObject(o)
        else:
            return o

    def __repr__(self):
        return self.json()

    def __str__(self):
        return self.json()


class BasicObject(UserDict, SerializableMixin):
    def __init__(self, item_dict: dict, obj=None):
        super(BasicObject, self).__init__()  # empty until validated
        for key in item_dict:  # protect system fields
            if key in ["data"]:
                item_dict[key + "_"] = item_dict[key]
                del item_dict[key]

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

    def __delitem__(self, key):
        del self.data[key]
        delattr(self, key)

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
        if name in self.input:
            value = self.input.get(name, default)
        else:
            return
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

    def drop_nones(self, required=None):
        clear = {}
        for k, v in self.items():
            if v is not None or (required and k in required):
                clear[k] = v
            else:
                delattr(self, k)
        self.data = BasicObject(clear)


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
            self.set_class(BasicObject)
        self._ix = {}

    def set_class(self, object_class):
        self.object_class = object_class
        if all([isinstance(x, dict) for x in self.data]):
            self.data = [object_class(item) for item in self.data]

    @property
    def ix(self):
        """
        Need id of items
        """
        if not self._ix and len(self) > 0 and self[0].get("id"):
            self._ix = {v["id"]: v for v in self}
        return self._ix

    def join(self, children, foreign_key, group_name, how="many"):
        assert how in ("many", "one")
        for i in self.data:
            i[group_name] = [] if how == "many" else None
        for child in children:
            try:
                if how == "many":
                    self.ix[child[foreign_key]][group_name].append(child)
                elif how == "one":
                    self.ix[child[foreign_key]][group_name] = child
            except KeyError:
                pass
                # logging.debug("Lost object index: {} id {}".format(foreign_key, child[foreign_key]))

    @classmethod
    def with_class(cls, object_class_=None):
        """Return new class"""
        class TypedCollection(Collection):
            object_class = object_class_ or BasicObject
        logging.debug("Redefined class in collection: {} (Collection id {}), original: {} (Collection id {})".format(TypedCollection.object_class, id(TypedCollection), cls.object_class, id(cls)))
        return TypedCollection

    def group_enum(self, enum_name, variants):
        """
        Group several boolean flags into one enum field
        :param enum_name: str name of new field
        :param variants: list flags
        """
        for item in self.data:
            item.group_enum(enum_name, variants)

    def search(self, case_insensitive=True, method="and", **kwargs):
        """
        Search and return filtered collection with linked objects
        :param case_insensitive: only if value is str
        :param method: and/or
        :param kwargs: filters
        :return: Collection
        """
        results = Collection([])
        for item in self:
            match = 0
            for key, value in kwargs.items():
                if item[key] == value or (case_insensitive and isinstance(item[key], str) and str(item[key]).lower() == str(value).lower()):
                    match += 1
            if method == "and" and match == len(kwargs):
                results.append(item)
            elif method == "or" and match > 0:
                results.append(item)
        return results


if __name__ == '__main__':
    a = Collection([])
    a.append({"a": "a", "b": "b"})
    a.append({"a": 1, "b": "2"})
    a.append({"a": "a", "b": "b"})
    print(a.search(a=1, b="2", method="and"))
