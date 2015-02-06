from grab import Grab
from json import loads, dumps
#from xwritter import ex_write
#from const import desktop as d
from datetime import datetime
from bill_classes import session, class_getter
from sqlalchemy.orm.exc import MultipleResultsFound
from suds.client import Client
import os
import re
from errors import INIT_ERROR, PARAM_ERROR, ACCESS_ERROR

_ctn = class_getter().get('ctn')
_agree = class_getter().get('operator_agree')
_account = class_getter().get('account_info')


def _get_data(num=None, ban=None, login=None, ctn=None,
			  agree=None, account=None,
			  ctn_b=_ctn, agree_b=_agree,
			  account_b=_account):
	'''Method returns login, password, ban and ban_id from eko_DB
	Can getting phone or/and oan
	'''
	if not num and not ban and not login:
		raise INIT_ERROR('Ни один обязательный параметр (num,ban,login) не был передан')
	if num:
		ban_id = session.query(ctn_b.operator_agree).filter(ctn_b.msisdn == num).one()[0]
		ban = session.query(agree_b.oan).filter(agree_b.i_id == ban_id).one()[0]

	if ban:
		ban_id = session.query(agree_b.i_id).filter(agree_b.oan == ban).one()[0]
	if ban_id is not None:

		query = session.query(account_b.login, account_b.password).filter(account_b.operator_agree == ban_id,
																		  account_b.access_type == 1)
		try:

			return query.one(), ban, ban_id
		except MultipleResultsFound:

			return query.all()[0], ban, ban_id
	if login:
		return session.query(account_b.login, account_b.password).filter(account_b.login == login,
																		 account_b.access_type == 1).one(), ban


class decors():
	'''class with decorators'''

	def account_cheker(func):
		'''check availability of login and password for checking instance of Client class'''
		def wrapper(self, *args, **kwargs):
			if not self.login or not self.password:
				self.get_account_info()
			return func(self, *args, **kwargs)

		return wrapper

	def total_checker(func):
		'''check some things, at first, availability of  login and password, then token.
		 At last, decorator check errors of returned result'''
		def wrapper(self, *args, **kwargs):
			if not self.login or not self.password:
				self.get_account_info()
			if not self.token:
				self.get_token()
			rez = func(self, *args, **kwargs)
			try:
				if rez['meta']['status'] != 'OK':
					if rez['meta']['message'] == 'TOKEN_NOT_FOUND':
						self.get_token()
						return
					self.error = rez['meta']

					try:
						print('Ошибка при вызове метода {}\n'
						  '{}\n'
						  'Параметры: {}'.format(func.__name__, rez['message'], (args, kwargs)))
						print(self)
					except KeyError:
						return rez
			except (TypeError,AttributeError):
				if self.api_type == 'REST':
					self.error = rez
					print('Ошибка при вызове метода {}\n'
						  '{}\n'
						  'Параметры: {}'.format(func.__name__, rez, (args, kwargs)))
				else:
					pass
			return rez

		return wrapper


class SetupSaver():
	def __init__(self, method=None, headers=None, params=None, cookies=None):
		self.method = method
		self.headers = headers
		self.params = params
		self.cookies = cookies


class BaseClient():
	'''Base API-Client class'''
	def __init__(self, ctn=None, ban=None, ban_id=None,
				 login=None, password=None,
				 token=None, error=None,
				 api_type=None, base_url=None, client=None):
		self.ctn = ctn
		self.ban = ban
		self.login = login
		self.password = password
		self.token = token
		self.api_type = api_type
		self.ban_id = ban_id
		self.base_url = base_url
		self.saver = SetupSaver()
		self.client = client

		self.error = error

	def __repr__(self):
		ret = '<{}>,'.format(self.__class__.__name__)
		for el in self.__dict__:
			ret += '{}={}, '.format(el, self.__getattribute__(el))
		return ret[:-2]

	def get_link(self, method_name=None, params=None, method_type="GET", is_json=True, setup=None):
		'''Method returns responsibility link for requested method.
		While choice PUT method, it automatically changing header 'Content-type' into "application/json".

		Can't be use with SOAP client'''
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
			elif method_type == "POST":
				pass
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

	def get_rezults(self, url, par=None):
		'''Returns rezults of requested method.
		'par' using by SOAP Client'''

		if self.api_type == "REST":
			self.client.go(url)
			try:
				return loads(self.client.response.body.decode())
			except Exception:
				print(self.client.response.body.decode())
		elif self.api_type == "SOAP":
			rez = self.client.service.__getattr__(url)(**par)
			try:
				return [dict(el) for el in rez]
			except:
				return rez

	def get_account_info(self):
		'''Returns login, password, ban, ban_id from BD for requested Client parameters'''
		(self.login, self.password), self.ban, self.ban_id = _get_data(num=self.ctn, ban=self.ban, login=self.login)

	def change_owner(self, ctn=None, ban=None, acc=1, token=1):
		'''Changing owner (ctn, ban) of your Client instance.
		Also, gets account_info and token, if gets same parameters'''
		for el in [self.ctn, self.ban, self.login, self.password]:
			el = None
		self.ctn = ctn
		self.ban = ban
		if acc == 1:
			self.get_account_info()
		if token == 1:
			self.get_token()

	def exchange_attrs(self, api):
		'''getting attrs of another Client instance.
		Must get SOAP Client, REST Client or BASE Client instance.'''
		self.token = api.token
		self.ban = api.ban
		self.ctn = api.ctn
		self.login = api.login
		self.password = api.password
		self.ban_id = api.ban_id

	def _chk_datetime(self, dt):
		'''Checking format of datetime attr. Returns datetime in ISO'''
		if not re.search(pattern=r'\d{4}-\d{2}-\d{2}', string=dt):
			if not re.search(pattern=r'\d{2}.\d{2}.\d{4}', string=dt):
				raise PARAM_ERROR('Неверный формат даты')
			else:
				return datetime.strptime(dt, "%d.%m.%Y").isoformat()
		else:
			return datetime.strptime(dt, "%Y-%m-%d").isoformat()


class RestClient(BaseClient):
	"""Класс позволяет использовать REST API Билайн без лишних хлопот :)"""


	def __init__(self, ctn=None, ban=None, ban_id=None,
				 login=None, password=None,
				 token=None, error=None):
		super().__init__(ctn=ctn, ban=ban, ban_id=ban_id, login=login, password=password, token=token, error=error,
						 api_type='REST', client=Grab(),
						 base_url='https://my.beeline.ru/api/1.0')


	@decors.account_cheker
	def get_token(self, opt=1):
		"""Returns token, which must requires on all of API methods"""
		url = self.get_link('/auth', {'login': self.login, 'password': self.password})
		rez = self.get_rezults(url)
		if opt:
			try:
				self.token = rez['token']
				self.client.setup(cookies={'token': self.token}, timeout=30)
				self.error = None
			except KeyError:
				self.error = rez['meta']
		else:
			return rez

	@decors.total_checker
	def get_ctn_list(self):
		"""Returns all of phones, which associated with your account (login)"""

		def show_params():
			pass

		url = self.get_link('/sso/subscribers', {'login': self.login})
		return self.get_rezults(url)

	@decors.total_checker
	def get_PP(self, opt=None):
		'''Returns price plan of the phone'''
		url = self.get_link('/info/pricePlan', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def get_status(self):
		'''Returns status of the phone'''
		url = self.get_link('/info/status', {'ctn': self.ctn})
		return self.get_rezults(url)


	@decors.total_checker
	def get_available_services(self, opt=None):
		'''Returns available services for the phone'''
		url = self.get_link('/info/serviceAvailableList', {'ctn': self.ctn})
		rez = self.get_rezults(url)
		if opt == 'save':
			ser_list = []
			try:
				for ser in rez['availableServices']:
					el_list = []
					el_list += [ser['name'], ser['entityName'], ser['entityDesc'], ser['rcRate'], ser['chargeAmount'],
								ser['category']]
					ser_list.append(el_list)
				pp = self.get_PP()['pricePlanInfo']['name']
				#path = d + '/REST_API/Проверка услуг/{}_{}_{}.xlsx'.format(pp, self.ctn,
																	#	   datetime.now().strftime('%Y%m%d%H%M%S'))
				names = ['Код услуги', 'Коммерческое название', "Коммерческое описание", "Абонентская плата",
						 "Стоимость подключения", "Категория услуги"]
				#ex_write(names, ser_list, path)
			except KeyError:
				print(rez)
				print(self)
				raise Exception
		else:
			return rez

	@decors.total_checker
	def get_sso(self):
		url = self.get_link('/sso/list', {'login': self.login})
		return self.get_rezults(url)

	@decors.total_checker
	def get_payments_history(self, bdt):
		'''Returns payment history of phone from `bdt` for the phone'''
		url = self.get_link('/info/payments/history',
							{'ctn': self.ctn, 'dateStart': datetime.now().isoformat() + '+0400'})
		return self.get_rezults(url)

	@decors.total_checker
	def get_blackList_numbers(self):
		'''Returns phones which in black list'''
		url = self.get_link('/info/blackList/numbers', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def get_notifications(self):
		url = self.get_link('/setting/notifications', {})
		return self.get_rezults(url)

	@decors.total_checker
	def change_notifications(self, actiontype, email, clear=True):
		if clear:
			pass
		else:
			url = self.get_link(method_name='/setting/notifications', method_type="PUT",
								params={"notifPoints": [{"type": "EMAIL",
														 "value": email,
														 "enabled": "true"}],
										"actionNotifications": [{"actionType": actiontype,
																 "enabled": "true"}]})
		return self.get_rezults(url)

	@decors.total_checker
	def get_servicers_list(self):
		'''Returns active services of the phone. Also, returns future-activate services'''
		url = self.get_link('/info/serviceList', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def get_request_status(self, requests=None):
		'''Checking status of requests'''
		if not requests:
			if not self.last_request:
				raise PARAM_ERROR('Нужен номер запроса')
			else:
				requests = self.last_request
		In = []
		if type(requests) == type([]):
			for el in requests:
				In.append({'requestId': el})
		else:
			In.append({'requestId': requests})

		url = self.get_link('/request/list', method_type="PUT", params={'requestList': In})
		return self.get_rezults(url)

	@decors.total_checker
	def create_detail_request(self, period):
		'''Creates detail request. Returns requestId'''
		if not re.search(pattern=r'\d{4}-\d{2}-\d{2}', string=period):
			if not re.search(pattern=r'\d{2}.\d{2}.\d{4}', string=period):
				raise PARAM_ERROR('Неверный формат даты, нужен гггг-мм-дд или дд.мм.гггг')
			else:
				billDate = datetime.strptime(period, "%d.%m.%Y").isoformat()
		else:
			billDate = datetime.strptime(period, "%Y-%m-%d").isoformat()
		url = self.get_link('/request/postpaidDetail', {'ctn': self.ctn, 'billDate': billDate})
		return self.get_rezults(url)

	@decors.total_checker
	def get_service_params(self, service):
		'''Returns params of the `service`'''
		url = self.get_link('/info/serviceParams', {'serviceName': service})
		return self.get_rezults(url)

	@decors.total_checker
	def activate_service(self, service, effDate=None, expDate=None):
		'''Activating services. Can insert date of auro-off'''
		if service == "BL_CPA_22":
			url = self.get_link('/request/serviceActivate',
								{'ctn': self.ctn, 'serviceName': service, 'featureParameters': [{
																									'feature': "KKWQPS",
																									'paramName': "WACLID",
																									'paramValue': None}]},
								method_type="PUT")
		else:
			url = self.get_link('/request/serviceActivate', {'ctn': self.ctn, 'serviceName': service},
								method_type="PUT")
		self.get_rezults(url)

	@decors.total_checker
	def get_packs(self):
		'''Returns current instanse of packs for the phone'''
		url = self.get_link('/info/rests', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def create_callForwardRequest(self):
		url = self.get_link('/request/callForward', {'ctn': self.ctn})
		return self.get_rezults(url)['requestId']

	@decors.total_checker
	def get_callForward(self, request):
		url = self.get_link('/info/callForward', {'requestId': request})
		return self.get_rezults(url)

	@decors.total_checker
	def get_subscriptions(self):
		url = self.get_link('/info/subscriptions', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def remove_subscribtion(self, sId=None, type=None):
		params = {'ctn': self.ctn}
		if sId:
			params['subscriptionId'] = sId
		if type:
			params['type'] = type
		url = self.get_link('/request/subscription/remove', params)
		return self.get_rezults(url)

	@decors.total_checker
	def get_balance(self):
		url = self.get_link('/info/prepaidBalance', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def get_available_pp(self):
		url = self.get_link('/info/pricePlanAvailableList', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def get_packs_prepaid(self):
		url = self.get_link('/info/prepaidAddBalance', {'ctn': self.ctn})
		return self.get_rezults(url)

	@decors.total_checker
	def get_unbilled_balance(self, level='ctn'):
		if level == 'ctn':
			params = {'ctn': self.ctn}
		elif level == 'ban':
			params = {'ban': self.ban}
		url = self.get_link('/info/postpaidBalance', params)
		return self.get_rezults(url)

	@decors.total_checker
	def changePricePlan(self, pp):
		url = self.get_link('/request/changePricePlan', {'ctn': self.ctn, 'pricePlan': pp})
		return self.get_rezults(url)

	@decors.total_checker
	def get_prepaid_detail(self, startDate, endDate):
		url = self.get_link('/request/prepaidDetail', {'ctn': self.ctn,
													   'startDate': startDate,
													   'endDate': endDate,
													   'reportType': 'xls'})


class SoapClient(BaseClient):
	def __init__(self, ctn=None, ban=None, ban_id=None,
				 login=None, password=None,
				 token=None, error=None):
		super().__init__(
			ctn=ctn, ban=ban, ban_id=ban_id, login=login, password=password, token=token, error=error,
			api_type='SOAP', base_url='https://my.beeline.ru/api/SubscriberService?WSDL', client=Client
		)
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
		return self.get_rezults('getCTNInfoList', params)

	@decors.total_checker
	def get_services_list(self, level='ctn'):
		params = {'token': self.token, 'ban': self.ban}
		if level == 'ctn':
			params['ctn'] = self.ctn
		return self.get_rezults('getServicesList', params)

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
		return self.get_rezults('getPaymentList', params)

	@decors.total_checker
	def replace_SIM(self, SIM):
		if not self.ctn:
			raise PARAM_ERROR('CTN обязателен')
		params = {'ctn': self.ctn,'serialNumber': SIM}
		return self.get_rezults('replaceSIM', params)

	@decors.total_checker
	def get_unbilled_calls(self):
		params = dict(token=self.token,ctn=self.ctn)
		return self.get_rezults('getUnbilledCallsList',params)

	@decors.total_checker
	def get_services_list_paged(self,page, level='ctn'):
		params = dict(token=self.token, ban=self.ban,
					  page=page, ctnAmountPerPage=50)
		if level=='ctn' and self.ctn:
			params['ctn'] = self.ctn
		return self.get_rezults('getServicesListPaged', params)


	@decors.total_checker
	def add_del_soc(self,soc,dir,act=None,deact=None):
		params = dict(token=self.token, ctn=self.ctn, soc=soc, inclusionType=dir, effDate=act, expDate=deact)
		return self.get_rezults('addDelSOC',params)

	@decors.total_checker
	def get_requests(self, req=None, page=1):
		if req:
			params = dict(token=self.token, requestId=str(req), login=self.login, page=page)
			return self.get_rezults('getRequestList', params)

	@decors.total_checker
	def get_current_detail(self):
		params = dict(token=self.token,ctn=self.ctn)
		return self.get_rezults('getUnbilledCallsList',params)

	@decors.total_checker
	def get_sim_list(self,level='ctn'):
		params = dict(token=self.token, ban=self.ban)
		if level == 'ctn' and self.ctn:
			params['ctn'] = self.ctn
		return self.get_rezults('getSIMList',params)

	@decors.total_checker
	def create_bill_detail(self,billDate):
		params = dict(token=self.token, billDate=self._chk_datetime(billDate)+'.000')
		return self.get_rezults('createBillChargesRequest', params)

	@decors.total_checker
	def get_bill_detail(self,requestId):
		params = dict(token=self.token, requestId=requestId)
		return self.get_rezults('getBillCharges', params)

#для обработки нескольких номеров/банов
class ClientStack(BaseClient):
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
		def _in(ctn,ban_id,ban,login,password,i):
			self.sorted_list.insert(i,
									{'ctn': ctn, 'ban_id': ban_id, 'ban': ban,
									 'login': login, 'password': password
									})
		if self.ctnlist:
			for ctn in self.ctnlist:
				self.ctn = ctn
				self.get_account_info()
				if len(self.sorted_list) == 0:
					_in(self.ctn, self.ban_id, self.ban,
					self.login, self.password,0)
					continue
				for el in self.sorted_list:
					if self.ban_id >= int(el['ban_id']):
						_in(self.ctn, self.ban_id, self.ban,
							self.login, self.password,self.sorted_list.index(el)-1)
						continue
					else:
						_in(self.ctn, self.ban_id, self.ban,
							self.login, self.password,self.sorted_list.index(el))
						break


