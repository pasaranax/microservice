from datetime import timedelta, datetime


class DataManager:
    """
    Менеджер данных выполняет работу с данными в формате CRUD+L(list)
    """

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
