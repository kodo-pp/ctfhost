from loguru import logger


GUEST = 0
USER = 100
ADMIN = 200


class ApiPermissionError(Exception):
    def __init__(self, *a):
        super().__init__(*a)


class Api:
    def __init__(self):
        self.handlers = {}

    def set_locale(self, lc):
        self.lc = lc
    
    def add(self, name, func, access_level):
        if self.has(name):
            raise KeyError(name)
        self.handlers[name] = (access_level, func)

    def has(self, name):
        return name in self.handlers

    def remove(self, name):
        self.handlers.pop(name)
    
    def handle(self, name, session, args=None):
        if session is None:
            access_level = GUEST
        elif session.is_admin:
            access_level = ADMIN
        else:
            access_level = USER
        required_access_level, func = self.handlers[name]
        if access_level < required_access_level:
            raise ApiPermissionError(self.lc.get('api_call_not_allowed').format(api_func=name))
        func(self, session, args)

api = Api()
