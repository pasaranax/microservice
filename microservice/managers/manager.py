from datetime import timedelta, datetime


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
            self.data.append(item.validate)
        self.valid = True


class DataManager:
    """
    Менеджер данных выполняет работу с данными в формате CRUD+L(list)
    """
    model = None

    def __init__(self, obj=None):
        """        
        Создать менеджер данных
        """
        self.cache = {}
        if obj is not None:
            self.obj = obj
    
    def create(self, *kwargs):
        return None
    
    def read(self, *kwargs):
        return None
    
    def update(self, *kwargs):
        return None
    
    def delete(self, *kwargs):
        return None
    
    def list(self, *kwargs):
        return None

    def save_cache(self, user, name, value, lifetime=timedelta(days=1)):
        key = "{}-{}".format(user["id"], name)
        deathtime = datetime.now() + lifetime
        self.cache[key] = [deathtime, value]

    def load_cache(self, user, name):
        key = "{}-{}".format(user["id"], name)
        if key in self.cache and self.cache[key][0] > datetime.now():
            return self.cache[key][1]
        else:
            del self.cache[key]

    def check_cache(self, user, name):
        key = "{}-{}".format(user["id"], name)
        if key in self.cache and self.cache[key][0] > datetime.now():
            return True
        else:
            return False

    def __del__(self):
        self.cache = {k: v for k, v in self.cache.items() if v[0] > datetime.now()}

    @staticmethod
    def extract_results(results, *args, **kwargs):
        """
        Извлечь список из результатов пиви или эластика
        :param extra_attrs: аттрибуты из результата, которые надо включить в словарь (peewee)
        :param results: ответ эластика или пиви
        :return: list
        """
        if len(results) > 0:
            lst = Collection([x.dict(*args, **kwargs) for x in results], BasicObject)
        else:
            lst = Collection([], BasicObject)
        return lst

    @staticmethod
    def extract_one(results, *args, **kwargs):
        for x in results:
            return BasicObject(x.dict(*args, **kwargs))
        return None
