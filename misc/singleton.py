class Singleton(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance:
            return cls._instance
        cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance
