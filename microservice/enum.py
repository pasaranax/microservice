class Enum:
    @classmethod
    def all(cls):
        return [cls.__dict__[x] for x in cls.__dict__.keys() if not x.startswith("_")]
