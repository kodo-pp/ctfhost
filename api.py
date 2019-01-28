from loguru import logger

class Api:
    def __init__(self):
        self.handlers = {}

    def set_locale(self, lc):
        self.lc = lc
    
    def add(self, name, func):
        if self.has(name):
            raise KeyError(name)
        self.handlers[name] = func

    def has(self, name):
        return name in self.handlers

    def remove(self, name):
        self.handlers.pop(name)
    
    def handle(self, name, args=None):
        return self.handlers[name](self, args)


api = Api()
