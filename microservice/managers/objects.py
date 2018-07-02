from collections import UserDict, UserList

from microservice.exceptions import ApiError


class BasicObject(UserDict):
    def __init__(self, item_dict):
        super(BasicObject, self).__init__(item_dict)  # self.data creates here
        # self.data.update(item_dict)
        self.validate()
        for key in self.data:
            if isinstance(self.data[key], dict):
                self.data[key] = BasicObject(self.data[key])
            setattr(self, key, self.data[key])

    def __setitem__(self, key, value):
        self.data[key] = value
        setattr(self, key, value)

    def validate(self):
        """implement it"""
        pass

    def valid(self, name, value, default=None, coerce=None, check=None, error=""):
        """
        Проверить значение на валидность
        :param error: текст в случае ошибки
        :param value: значение
        :param default: если значение None, то взять default
        :param coerce: привести к типу или применить функцию
        :param check: проверить функцией (должна вернуть True)
        :return: возвращает значение
        """
        if value is None:
            value = default
        if coerce and value is not None:
            try:
                value = coerce(value)
            except ValueError:
                raise ApiError("#wrong_type {}, expected {}. {}".format(name, coerce, error))
        if check and value is not None and not check(value):
            raise ApiError("#wrong_format {}. {}".format(name, error))
        return value

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


class Collection(UserList):
    def __init__(self, items_list, object_class=None):
        super(Collection, self).__init__()  # fill list later
        self.object_class = object_class
        self.items = items_list
        if object_class:
            self.set_class(object_class)
        else:
            self.data = []
            self.valid = False

    def set_class(self, object_class):
        self.object_class = object_class
        self.data = [object_class(item) for item in self.items]
        self.valid = True
