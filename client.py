from grab import Grab
from json import loads, dumps
from datetime import datetime
from sqlalchemy.orm.exc import MultipleResultsFound
from suds.client import Client
import re

try:
    from bill_classes import session, ClassGetter
except ImportError:
    from .bill_classes import session, ClassGetter

try:
    from errors import INIT_ERROR, PARAM_ERROR, ACCESS_ERROR
except ImportError:
    from .errors import INIT_ERROR, PARAM_ERROR, ACCESS_ERROR

from suds import WebFault
_ctn = ClassGetter.get('ctn')
_agree = ClassGetter.get('operator_agree')
_account = ClassGetter.get('account_info')


def _get_data(num=None, login=None,
              ban_id=None, ban=None,
              ctn_b=_ctn, agree_b=_agree,
              account_b=_account, i_n=0):
    """Method returns login, password, ban and ban_id from eko_DB
    Can getting phone or/and oan
    """
    pay_type = None
    if not num and not ban and not login:
        raise INIT_ERROR('Ни один обязательный параметр (num,ban,login) не был передан')
    if num:
        ban_id = session.query(ctn_b.operator_agree).filter(ctn_b.msisdn == num).one()[0]
        ban, pay_type = session.query(agree_b.oan, agree_b.payment_type).filter(agree_b.i_id == ban_id).one()

    if ban:
        ban_id, pay_type = session.query(agree_b.i_id, agree_b.payment_type).filter(agree_b.oan == ban).one()
    if ban_id is not None:

        query = session.query(account_b.login, account_b.password).filter(account_b.operator_agree == ban_id,
                                                                          account_b.access_type == 1)
        try:

            return query.one(), ban, ban_id, pay_type
        except MultipleResultsFound:

            return query.all()[i_n], ban, ban_id, pay_type
    if login:
        return session.query(account_b.login, account_b.password).filter(account_b.login == login,
                                                                         account_b.access_type == 1).one(), ban


class decors():
    """class with decorators"""

    @staticmethod
    def account_cheker(func):
        """check availability of login and password for checking instance of Client class"""

        def wrapper(self, *args, **kwargs):
            if not self.login or not self.password:
                self._get_account_info()
            return func(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def total_checker(func):
        """check some things, at first, availability of  login and password, then token.
         At last, decorator check errors of returned result.

         Optionally required available pay_type of method"""
        def wrapper(self, *args, **kwargs):
            # TODO: check payment type of agree for some methods
            '''if pay_type and self.pay_type != pay_type:
            raise PARAM_ERROR('Method can call only {} payment type.'.format(self.__pay_types[pay_type]))'''
            if 's_ctn' in kwargs:
                self.ctn = kwargs.pop('s_ctn')
            if not self.login or not self.password:
                self._get_account_info()
            if not self.token:
                self.get_token()
            return func(self, *args, **kwargs)
        return wrapper

    @staticmethod
    def unavailable(func):
        def wrapper(self):
            raise ACCESS_ERROR('Method unavailable yet')
        return wrapper


class BaseClient():
    """Base API-Client class"""
    def __init__(self, ctn=None, ban=None, ban_id=None,
                 login=None, password=None, pay_type=None,
                 token=None, api_type=None,
                 base_url=None, client=None, api_instance=None):
        self.ctn = ctn
        self.ban = ban
        self.login = login
        self.password = password
        self.token = token
        self.api_type = api_type
        self.ban_id = ban_id
        self.base_url = base_url
        self.client = client
        self.pay_type = pay_type
        self.__pay_types = {
            0: "postpaid",
            1: "prepaid",
            None: "global"
        }
        if api_instance:
            self.exchange_attrs(api_instance)

    def __repr__(self):
        ret = '<{}>,'.format(self.__class__.__name__)
        for el in self.__dict__:
            ret += '{}={}, '.format(el, self.__getattribute__(el))
        return ret[:-2]

    def _get_link(self, method_name=None, params=None, method_type="GET", is_json=True):
        """Method returns responsibility link for requested method.
        While choice PUT method, it automatically changing header 'Content-type' into "application/json".

        Can't be use with SOAP client"""
        if self.api_type == "REST":
            self.client.setup(method=method_type)

            def _ret(_params):
                if not params:
                    return ''
                return_params = '?'
                for key in _params:
                    return_params += '{}={}&'.format(key, _params[key])
                return return_params[:-1]

            if method_type == "GET":
                link = self.base_url + method_name + _ret(params)
            elif method_type == "PUT":
                self.client.setup(post=dumps(params).encode())
                if is_json:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:12.0) Gecko/20100101 Firefox/12.0',
                               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                               'Accept-Language': 'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3',
                               'Accept-Encoding': 'gzip, deflate',
                               'Connection': 'keep-alive',
                               "Content-Type": "application/json"}
                    self.client.setup(headers=headers)
                link = self.base_url + method_name
            else:
                raise PARAM_ERROR("Невозможный тип запроса")
            return link
        elif self.api_type == "SOAP":
            raise ACCESS_ERROR

    def _get_results(self, url, par=None,timeout=30):
        """Returns results of requested method.
        'par' using by SOAP Client"""

        if self.api_type == "REST":
            self.client.setup(timeout=timeout)
            self.client.go(url)
            try:
                return loads(self.client.response.body)
            except TypeError:
                return loads(self.client.response.body.decode())

        #TODO: dictionary for results of SOAP-requests
        elif self.api_type == "SOAP":
            rez = self.client.service.__getattr__(url)(**par)
            return rez

    def _get_account_info(self):
        """Returns login, password, ban, ban_id from BD for requested Client parameters"""
        (self.login, self.password),\
        self.ban, self.ban_id, self.pay_type = _get_data(num=self.ctn, ban=self.ban, login=self.login)

    def change_owner(self, ctn=None, ban=None, acc=1, token=1):
        """Changing owner (ctn, ban) of your Client instance.
        Also, gets account_info and token, if gets same parameters"""
        for el in ['ctn', 'ban', 'login', 'password']:
            self.__setattr__(el, None)
        self.ctn = ctn
        self.ban = ban
        if acc == 1:
            self._get_account_info()
        if token == 1:
            self.get_token()

    def exchange_attrs(self, client):
        """getting attrs of another Client instance.
        Must get SOAP Client, REST Client or BASE Client instance."""
        self.token = client.token
        self.ban = client.ban
        self.ctn = client.ctn
        self.login = client.login
        self.password = client.password
        self.ban_id = client.ban_id
        self.pay_type = client.pay_type

    def _chk_datetime(self, dt):
        """Checking format of datetime attr. Returns datetime in ISO"""
        if not re.search(pattern=r'\d{4}-\d{2}-\d{2}', string=dt):
            if not re.search(pattern=r'\d{2}.\d{2}.\d{4}', string=dt):
                raise PARAM_ERROR('Неверный формат даты')
            else:
                return datetime.strptime(dt, "%d.%m.%Y").isoformat()
        else:
            return datetime.strptime(dt, "%Y-%m-%d").isoformat()


class Rest(BaseClient):
    """Class initialize client for REST API"""

    def __init__(self, ctn=None, ban=None, ban_id=None,
                 login=None, password=None, token=None,
                 pay_type=None, api_instance=None):
        super().__init__(ctn=ctn, ban=ban, ban_id=ban_id, pay_type=pay_type,
                         login=login, password=password, token=token,
                         api_type='REST', client=Grab(timeout=60),
                         base_url='https://my.beeline.ru/api/1.0',
                         api_instance=api_instance)

    @decors.account_cheker
    def get_token(self, opt=1):
        """Returns token, which must requires on all of API methods"""
        url = self._get_link('/auth', {'login': self.login, 'password': self.password})
        rez = self._get_results(url)
        if opt:
            self.token = rez['token']
            self.client.setup(cookies={'token': self.token})
        else:
            return rez

    @decors.total_checker
    def get_ctn_list(self):
        """Returns all of phones, which associated with your account (login)"""
        url = self._get_link('/sso/subscribers', {'login': self.login})
        return self._get_results(url)

    @decors.total_checker
    def get_pp(self):
        """Returns price plan of the phone"""
        url = self._get_link('/info/pricePlan', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_status(self):
        """Returns status of the phone"""
        url = self._get_link('/info/status', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_available_services(self):
        """Returns available services for the phone"""
        url = self._get_link('/info/serviceAvailableList', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_sso(self):
        url = self._get_link('/sso/list', {'login': self.login})
        return self._get_results(url)

    @decors.unavailable
    @decors.total_checker
    def get_payments_history(self):
        """Returns payment history of phone from `bdt` for the phone"""
        url = self._get_link('/info/payments/history',
                             {
                                 'ctn': self.ctn,
                                 'dateStart': datetime.now().isoformat() + '+0400'
                             })
        return self._get_results(url)

    @decors.total_checker
    def get_blacklist_numbers(self):
        """Returns phones which in black list"""
        url = self._get_link('/info/blackList/numbers', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_notifications(self):
        url = self._get_link('/setting/notifications', {})
        return self._get_results(url)

    @decors.total_checker
    def change_notifications(self, actiontype, email, clear=True):
        if clear:
            pass
        else:
            url = self._get_link(method_name='/setting/notifications', method_type="PUT",
                                 params={
                                     "notifPoints": [{"type": "EMAIL",
                                                      "value": email,
                                                      "enabled": "true"}],
                                     "actionNotifications": [{"actionType": actiontype,
                                                              "enabled": "true"}]
                                 })
            return self._get_results(url)

    @decors.total_checker
    def get_services_list(self):
        """Returns active services of the phone. Also, returns future-activate services"""
        url = self._get_link('/info/serviceList', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_request_status(self, requests):
        """Checking status of requests"""
        inner_requests = []
        if isinstance(requests, []):
            for el in requests:
                inner_requests.append({'requestId': el})
        else:
            inner_requests.append({'requestId': requests})
        url = self._get_link('/request/list', method_type="PUT", params={'requestList': inner_requests})
        return self._get_results(url)

    @decors.total_checker
    def create_detail_request(self, period):
        """Creates detail request. Returns requestId"""
        if not re.search(pattern=r'\d{4}-\d{2}-\d{2}', string=period):
            if not re.search(pattern=r'\d{2}.\d{2}.\d{4}', string=period):
                raise PARAM_ERROR('Неверный формат даты, нужен гггг-мм-дд или дд.мм.гггг')
            else:
                bill_date = datetime.strptime(period, "%d.%m.%Y").isoformat()
        else:
            bill_date = datetime.strptime(period, "%Y-%m-%d").isoformat()
        url = self._get_link('/request/postpaidDetail', {'ctn': self.ctn, 'billDate': bill_date})
        return self._get_results(url)

    @decors.total_checker
    def get_service_params(self, service):
        """Returns params of the `service`"""
        url = self._get_link('/info/serviceParams', {'serviceName': service})
        return self._get_results(url)

    @decors.total_checker
    def activate_service(self, service):
        """Activating services. Can insert date of auto-off"""
        if service == "BL_CPA_22":
            url = self._get_link('/request/serviceActivate',
                                 {'ctn': self.ctn, 'serviceName': service,
                                  'featureParameters': [{'feature': "KKWQPS",
                                                         'paramName': "WACLID",
                                                         'paramValue': None}]},
                                 method_type="PUT")
        else:
            url = self._get_link('/request/serviceActivate',
                                 {'ctn': self.ctn, 'serviceName': service}, method_type="PUT")
        self._get_results(url)

    @decors.total_checker
    def get_packs(self):
        """Returns current instanse of packs for the phone"""
        url = self._get_link('/info/rests', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def create_call_forward_request(self):
        url = self._get_link('/request/callForward', {'ctn': self.ctn})
        return self._get_results(url)['requestId']

    @decors.total_checker
    def get_call_forward(self, request):
        url = self._get_link('/info/callForward', {'requestId': request})
        return self._get_results(url)

    @decors.total_checker
    def get_subscriptions(self):
        url = self._get_link('/info/subscriptions', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def remove_subscribtion(self, sId=None, type=None):
        params = {'ctn': self.ctn}
        if sId:
            params['subscriptionId'] = sId
        if type:
            params['type'] = type
        url = self._get_link('/request/subscription/remove', params)
        return self._get_results(url)

    @decors.total_checker
    def get_balance(self):
        url = self._get_link('/info/prepaidBalance', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_available_pp(self):
        url = self._get_link('/info/pricePlanAvailableList', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_packs_prepaid(self):
        url = self._get_link('/info/prepaidAddBalance', {'ctn': self.ctn})
        return self._get_results(url)

    @decors.total_checker
    def get_unbilled_balance(self, level='ctn'):
        if level == 'ctn':
            params = {'ctn': self.ctn}
        elif level == 'ban':
            params = {'ban': self.ban}
        url = self._get_link('/info/postpaidBalance', params)
        return self._get_results(url)

    @decors.total_checker
    def change_price_plan(self, pp):
        url = self._get_link('/request/changePricePlan', {'ctn': self.ctn, 'pricePlan': pp})
        return self._get_results(url)

    @decors.total_checker
    def get_prepaid_detail(self, startDate, endDate):
        url = self._get_link('/request/prepaidDetail', {'ctn': self.ctn,
                                                           'startDate': startDate,
                                                           'endDate': endDate,
                                                           'reportType': 'xls'})


class Soap(BaseClient):
    def __init__(self, ctn=None, ban=None, ban_id=None,
                 login=None, password=None, token=None,
                 pay_type=None, api_instance=None):
        super().__init__(
            ctn=ctn, ban=ban, ban_id=ban_id, login=login, password=password, token=token, pay_type=pay_type,
            api_type='SOAP', base_url='https://my.beeline.ru/api/SubscriberService?WSDL', client=Client,
            api_instance=api_instance)
        try:
            self.client = self.client(self.base_url, timeout=600)
        except Exception:
            self.client(self.base_url)

    @decors.account_cheker
    def get_token(self):
        self.token = Client('https://my.beeline.ru/api/AuthService?WSDL').service.auth(**{
        'login': self.login,
        'password': self.password
        })

    @decors.total_checker
    def get_ctn_info(self, level='ctn'):
        params = {'token': self.token, 'ban': self.ban}
        if level == 'ctn':
            params['ctn'] = self.ctn
        return self._get_results('getCTNInfoList', params)

    @decors.total_checker
    def get_services_list(self, level='ctn'):
        params = {'token': self.token, 'ban': self.ban}
        if level == 'ctn':
            params['ctn'] = self.ctn
        return self._get_results('getServicesList', params)

    @decors.total_checker
    def get_payments_list(self, bdate=None, edate=None, level='ctn'):
        if not bdate:
            print('За текущий день')
            bdate = datetime.now().isoformat()
        else:
            bdate = self._chk_datetime(bdate)
        if not edate:
            edate = bdate
        else:
            edate = self._chk_datetime(edate)
        if level == 'ctn':
            if input('Для postpaid только по BAN. Продолжить (y/n)? ') == 'n':
                return
        params = {
            'token': self.token,
            'ctn': self.ctn,
            'ban': self.ban,
            'startDate': bdate,
            'endDate': edate
        }
        return self._get_results('getPaymentList', params)

    @decors.total_checker
    def replace_sim(self, sim):
        if not self.ctn:
            raise PARAM_ERROR('CTN обязателен')
        params = {'ctn': self.ctn, 'serialNumber': sim}
        return self._get_results('replaceSIM', params)

    @decors.total_checker
    def get_unbilled_calls(self):
        params = dict(token=self.token, ctn=self.ctn)
        return self._get_results('getUnbilledCallsList', params)

    @decors.total_checker
    def get_services_list_paged(self, page, level='ctn'):
        params = dict(token=self.token, ban=self.ban,
                      page=page, ctnAmountPerPage=50)
        if level == 'ctn' and self.ctn:
            params['ctn'] = self.ctn
        return self._get_results('getServicesListPaged', params)


    @decors.total_checker
    def add_del_soc(self, soc, dir, act=None, deact=None):
        params = dict(token=self.token, ctn=self.ctn, soc=soc, inclusionType=dir, effDate=act, expDate=deact)
        return self._get_results('addDelSOC', params)

    @decors.total_checker
    def get_requests(self, req=None, bdt=None, edt=None, page=1, rec=50):
        params = dict(token=self.token, requestId=str(req), login=self.login, page=page, hash=12321321321, recordsPerPage=rec)
        if req:
            params['requestId']=str(req)
        elif bdt and edt:
            params['startDate'] = bdt
            params['endDate'] = edt
        elif bdt:
            params['startDate'] = bdt
            params['endDate'] = datetime.now().isoformat()
        return self._get_results('getRequestList', params)

    @decors.total_checker
    def get_current_detail(self):
        params = dict(token=self.token, ctn=self.ctn)
        return self._get_results('getUnbilledCallsList', params)

    @decors.total_checker
    def get_sim_list(self, level='ctn'):
        params = dict(token=self.token, ban=self.ban)
        if level == 'ctn' and self.ctn:
            params['ctn'] = self.ctn
        return self._get_results('getSIMList', params)

    @decors.total_checker
    def create_bill_detail(self, billDate):
        params = dict(token=self.token, billDate=self._chk_datetime(billDate) + '.000', ban=self.ban)
        return self._get_results('createBillChargesRequest', params)

    @decors.total_checker
    def get_bill_detail(self, requestId):
        params = dict(token=self.token, requestId=requestId)
        return self._get_results('getBillCharges', params)

    @decors.total_checker
    def create_detail_request(self, billDate):
        params = dict(token=self.token, billDate=self._chk_datetime(billDate) + '.000', CTNList=self.ctn)
        return self._get_results('createBillCallsRequest', params)

    @decors.total_checker
    def get_detail_request(self, request):
        params = dict(token=self.token, requestId=request)
        return self._get_results('getBillCalls', params)


# для обработки нескольких номеров/банов
class ClientStack(BaseClient):

    @decors.unavailable
    def __init__(self, ctnlist=None, banlist=None, api_type=None):
        self.ctnlist = ctnlist
        self.banlist = banlist
        self.api_type = api_type
        self.sorted_list = []
        self.ban_id = None
        self.ban = None
        self.login = None
        self.password = None
        self.token = None

    def sort_by_ban(self):
        def _in(ctn, ban_id, ban, login, password, i):
            self.sorted_list.insert(i,
                                    {'ctn': ctn, 'ban_id': ban_id, 'ban': ban,
                                     'login': login, 'password': password
                                    })

        if self.ctnlist:
            for ctn in self.ctnlist:
                self.ctn = ctn
                self._get_account_info()
                if len(self.sorted_list) == 0:
                    _in(self.ctn, self.ban_id, self.ban,
                        self.login, self.password, 0)
                    continue
                for el in self.sorted_list:
                    if self.ban_id >= int(el['ban_id']):
                        _in(self.ctn, self.ban_id, self.ban,
                            self.login, self.password, self.sorted_list.index(el) - 1)
                        continue
                    else:
                        _in(self.ctn, self.ban_id, self.ban,
                            self.login, self.password, self.sorted_list.index(el))
                        break