import logging
from collections import UserDict, UserList

from microservice.exceptions import ApiError


class BasicObject(UserDict):
    def __init__(self, item_dict: dict):
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

    def set_model(self):
        """if object have id, it may be saved to db (o rly?)"""
        pass

    def dict(self):
        """return raw dict"""
        raw_dict = {}
        for k, v in self.data.items():
            if isinstance(v, BasicObject):
                raw_dict[k] = v.dict()
            else:
                raw_dict[k] = v
        return raw_dict

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


class Collection(UserList):
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
        cls.object_class = object_class or BasicObject
        return cls

    def group_enum(self, enum_name, variants):
        """
        Group several boolean flags into one enum field
        :param enum_name: name of new field
        :param variants: flags
        """
        for item in self.data:
            item.group_enum(enum_name, variants)
