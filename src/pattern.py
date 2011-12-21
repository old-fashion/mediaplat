# -*- coding: utf-8 -*-

def singleton(cls):
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.
    """
    instance_container = []

    def getinstance():
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """

        if not len(instance_container):
            instance_container.append(cls())
        return instance_container[0]

    return getinstance

class Singleton(type):
    """
    A Singleton with metaclass aproach, usage is like belows

    class MyClass(BaseClass):
        __metaclass__ = Singleton
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
