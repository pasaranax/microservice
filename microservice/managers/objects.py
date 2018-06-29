from collections import UserDict, UserList


class BasicObject(UserDict):
    def __init__(self, item_dict):
        super(BasicObject, self).__init__(item_dict)
        self.data.update(item_dict)
        self.validate()
        for key in self.data:
            setattr(self, key, self.data[key])

    def __setitem__(self, key, value):
        self.data[key] = value
        setattr(self, key, value)

    def validate(self):
        """implement it"""
        pass

    def set_model(self):
        """if object have id, it may be saved to db (o rly?)"""
        pass


class Collection(UserList):
    def __init__(self, items_list, object_class=None):
        super(Collection, self).__init__(items_list)
        self.object_class = object_class
        self.items = items_list
        if object_class:
            self.set_class(object_class)
        else:
            self.data = []
            self.valid = False

    def set_class(self, object_class):
        self.object_class = object_class
        for item in self.items:
            self.data.append(object_class(item))
        self.valid = True
