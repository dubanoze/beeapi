'''
Модуль авторизации
'''

from suds.client import Client
from suds import WebFault

from errors import AUTH_ERROR


class Auth():
    def __init__(self, login, password):
        auth_url = 'https://my.beeline.ru/rapi/AuthService?WSDL'
        auth = Client(auth_url)
        access = dict(login=login, password=password)
        print(access)
        self.token = auth.service.auth(**access)
        print('Catch access data')


def _get():
    from get_access import get_data

    data = get_data(9672666660)
    print(data)
    for d in data:
        try:
            token = Auth(*d[:2])
        except WebFault:
            if data[-1] != d:
                continue
            else:
                raise AUTH_ERROR
        print(token.token)


if __name__ == '__main__':
    t = Auth('A4841888', '84855')
    print(t.token)
