from datetime import datetime
import re

from suds.client import Client
from suds import WebFault

from auth import Auth
from get_access import get_data
from errors import * #импортируем ошибки


service_url='https://my.beeline.ru/rapi/SubscriberService?WSDL'


class bee_api():
	def __init__(self,ctn=None,ban=None,login=None,password=None,token=None):
		#пробуем получать логин/пароль из БД биллинга

		try:
			if ctn:
				if type(ctn)==list:
					self.login,self.password,self.ban,self.ctn=get_data(ctn=ctn[0])[0]
					self.ctn=ctn
				else:
					self.login,self.password,self.ban,self.ctn=get_data(ctn=ctn)[0]
			elif ban:
				self.login,self.password,self.ban=get_data(ban=ban)[0]
				self.ctn=None
			else:
				raise INIT_ERROR('Can\'t get access for ctn/BAN: {}/{}'.format(ctn,ban))
		#для ситуаций, когда передаем ctn/ban, которых нет в БД
		except ACCESS_ERROR:
			if ctn:
				self.ctn=ctn
			elif ban:
				self.ban=ban
		'''
		self.ctn=ctn
		self.ban=ban
		self.login=login
		self.password=password
		self.token=token'''
	#для проверки уровня запроса - BAN или CTN
	def _chk_level(self,level):
		if level=='ctn':
			if self.ctn==None:
				raise PARAM_ERROR('Не задан номер')
			else:
				return dict(token=self.token,ctn=self.ctn,ban=self.ban)
		elif level=='ban':
			if self.ban==None:
				raise PARAM_ERROR('Не задан BAN')
			else:
				return dict(token=self.token,ban=self.ban)
		else:
			raise PARAM_ERROR('Уровня {} не существует'.format(level))

	#для проверки формата введенной даты
	def _chk_datetime(self,date):
		if re.compile(r'^\d{4}[.-]\d{2}[.-]\d{2}\s\d{2}[:]\d{2}[:]\d{2}[.]\d{6}$').search(str(date)):
			return date.isoformat()
		elif re.compile(r'^\d{2}[.-]\d{2}[.-]\d{4}$').search(date):
			return date.isoformat()
		else:
			raise PARAM_ERROR('Неверно задан формат даты')

	#декоратор для получения текста ошибок
	def excDescr(function):
		def getException(*args,**kwargs):
			try:
				return function(*args,**kwargs)
			except WebFault as error:
				raise API_BASE_ERROR(error.fault[1],error.fault[2].UssWsApiException.errorCode,
					  error.fault[2].UssWsApiException.errorDescription)
		return getException

	#получаем токен
	@excDescr
	def get_token(self):
		self.token=Auth(self.login,self.password).token

	# инфо о номере - статус, дата активации, тариф, БАН
	@excDescr
	def getCTNInfoList(self,level='ctn'):
		params=self._chk_level(level)
		rez=Client(service_url).service.getCTNInfoList(**params)
		if level=='ctn':
			return rez[0]
		else:
			return rez

	#аналог 'limit' для getCTNInfoList
	@excDescr
	def getCTNInfoListPaged(self,p=1,r=1):
		params=self._chk_level('ban')
		params['page']=p
		params['recordsPerPage']=r
		rez=Client(service_url).service.getCTNInfoListPaged(**params)
		return rez

	#деталка
	@excDescr
	def createBillChargesRequest(self,bD):
		params=dict(token=self.token,ban=self.ban,billDate=bD+"T00:00:00.000")
		return Client(service_url).service.createBillChargesRequest(**params)

	@excDescr
	def getBillCharges(self,req):
		params=dict(token=self.token,requestId=req)
		return Client(service_url).service.getBillCharges(**params)

	#статус созданной заявки
	@excDescr
	def getRequestList_one(self,req):
		params=dict(token=self.token,requestId=str(req),login=self.login,page=1)
		rezult=Client(service_url).service.getRequestList(**params)
		return rezult

	#разблок
	@excDescr
	def restoreCTN(self,date=datetime.now()):
		if self.ctn==None:
			raise PARAM_ERROR('Не задан номер')
		date=self._chk_datetime(date)
		params=dict(token=self.token,ctn=self.ctn,actvDate=date,reasonCode="RSBO")
		requestId=Client(service_url).service.restoreCTN(**params)
		return requestId
		#self.getRequestList_one(requestId)

	#блок
	@excDescr
	def suspendCTN(self,date=datetime.now(),rsn='S1B'):
		if self.ctn==None:
			raise PARAM_ERROR('Не задан номер')
		date=self._chk_datetime(date)
		params=dict(token=self.token,ctn=self.ctn,actvDate=date,reasonCode=rsn)
		requestId=Client(service_url).service.suspendCTN(**params)
		return requestId
		#self.getRequestList_one(requestId)

	#список подключенных услуг
	@excDescr
	def getServicesList(self,level='ctn'):
		params=self._chk_level(level)

		rezult=Client(service_url,timeout=300).service.getServicesList(**params)
		print('Done')
		return rezult

	#платежи
	@excDescr
	def getPaymentList(self,level,bmonth,eday,emonth,bday):
		if level=='ctn':
			print('Напоминаю, только для BAN!')
		params = self._chk_level(level)
		if not eday or not emonth:
			raise PARAM_ERROR('Не задан конец периода')
		print("Платежи с {}.{} числа и до {}.{}!".format(bday,bmonth,eday,emonth))
		params['startDate']=datetime(2014,bmonth,bday).isoformat()
		params['endDate']=datetime(2014,emonth,eday,23,59,59).isoformat()
		rezult=Client(service_url).service.getPaymentList(**params)
		return rezult

	#подключение/отключение услуг
	@excDescr
	def addDelSOC(self,SOC,DIR,effDate=None,expDate=None):
		params=self._chk_level(level='ctn')
		params['soc']=SOC
		params['inclusionType']=DIR
		if effDate:
			params['effDate']=datetime.strptime(effDate,"%Y-%m-%d").isoformat()+'.000'
		if expDate:
			params['expDate']=datetime.strptime(expDate,"%Y-%m-%d").isoformat()+'.000'
		del params['ban']
		rezult=Client(service_url).service.addDelSOC(**params)
		return rezult


	#замена SIM
	@excDescr
	def replaceSIM(self,SIM):
		if self.ctn==None:
			raise PARAM_ERROR('Не задан CTN')
		params=dict(serialNumber=SIM,ctn=self.ctn)
		return Client(service_url).service.replaceSIM(**params)

	#смена ТП
	@excDescr
	def _changePP(self,PP,fD='N'):
		print('Creating request for changing PricePlan')
		params=self._params(level='CTN')
		params['pricePlan']=PP
		params['futureDate']=fD
		del(params['ban'])
		if fD not in ('Y',"N"):
			print('FutureDate parameter incorrect')
			return
		else:
			req=Client(service_url).service.changePP(**params)
	#ТД
	@excDescr
	def getUnbilledCallsList(self):
		params=dict(token=self.token,ctn=self.ctn)
		return Client(service_url).service.getUnbilledCallsList(**params)



	#инфа о SIM
	@excDescr
	def getSIMList(self):
		params=dict(ban=self.ban,ctn=self.ctn,token=self.token)
		return Client(service_url).service.getSIMList(**params)

	@excDescr
	def createBillCallsRequest(self,billDate):
		params=dict(ban=self.ban,token=self.token)
		params['billDate']=billDate+'T00:00:00.0'
		return Client(service_url).service.createBillCallsRequest(**params)

	@excDescr
	def getBillCallsPaged(self,requestID,page=1,recordsPerPage=1):
		params=dict(token=self.token,requestId=requestID,page=page,recordsPerPage=recordsPerPage)
		return Client(service_url).service.getBillCallsPaged(**params)

	@excDescr
	def getBANInfoList(self):
		params=dict(login=self.login,token=self.token)
		return Client(service_url).service.getBANInfoList(**params)

	@excDescr
	def getAdjustmentList(self,sdt,edt):
		params=dict(token=self.token,ban=self.ban,startDate=sdt,endDate=edt)
		return Client(service_url).service.getAdjustmentList(**params)

if __name__=='__main__':

	api=bee_api(ctn=9673481105)
	api.get_token()
	rez=api.createBillCallsRequest(billDate="2014-11-30")