from datetime import timedelta, datetime

from microservice.middleware.objects import BasicObject, Collection


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
    
    def create(self, **kwargs):
        return None
    
    def read(self, **kwargs):
        return None
    
    def update(self, **kwargs):
        return None
    
    def delete(self, **kwargs):
        return None
    
    def list(self, **kwargs):
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
