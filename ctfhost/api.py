from loguru import logger

from .localization import lc


GUEST = 0
USER = 100
ADMIN = 200


class ApiPermissionError(Exception):
    def __init__(self, *a):
        super().__init__(*a)


class ApiUserError(Exception):
    def __init__(self, *a):
        super().__init__(*a)


class ApiKeyError(Exception):
    def __init__(self, *a):
        super().__init__(*a)


class ApiArgumentError(Exception):
    def __init__(self, arg):
        super().__init__(arg)


class Api:
    def __init__(self):
        self.handlers = {}

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
        try:
            required_access_level, func = self.handlers[name]
        except KeyError:
            raise ApiKeyError(name)
        if access_level < required_access_level:
            raise ApiPermissionError(lc.get('api_call_not_allowed').format(api_func=name))
        func(self, session, args)

api = Api()
