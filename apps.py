from xwritter import ex_write
from const import desktop as d
from const import conn_eko as conn
from bill_classes import session, class_getter
import time
import re
import sys
import os
import shutil
from grab.error import GrabTimeoutError

from soap_api import bee_api
from client import RestClient
from errors import PARAM_ERROR,API_BASE_ERROR


class BAN():
	def __init__ (self,ban,login,password):
		self.ban=ban
		self.login=login
		self.password=password

#услуги списка номеров
def serv(ctn_list):

	for ctn in ctn_list:
		api=RestClient(ctn=ctn)
		api.get_token()
		serv=api.get_servicers_list()['services']
		print('ctn == '+ str(api.ctn)+"\nServices count == "+str(len(serv)))
		for s in serv:
			for el in ['name','entityName','category','effDate','expDate']:
				print('\t'+el+" == "+str(s[el]))
			print("\t--------------------")
		print("=======================\n=======================")


def down_serv(banlist):
	pth='C:/User/админ/Desktop/serv.xlsx'
	names=['','','','','','','','','']
	serv=[]
	for ban in [176824529	,
132582827	,
147807239	,
184989346	,
385816266	,
414006137	,
176824561
]:
		print('Начинаем с {}'.format(ban))
		api=bee_api(ban=ban)
		api.get_token()
		print('Получаем список услуг')
		serv+=api.getServicesList(level='ban')
		print('закончили с {}'.format(ban))
	print('Сохраняем')
	ex_write(names,serv,pth)
	print('Готово')



def getRequest(*args):
	api=bee_api(ctn=9672666660)
	api.login=args[0][1]
	api.token=args[0][0]
	req=args[0][2]
	return api.getRequestList_one(req=req,token=api.token,login=api.login)

#проверка блок-разблок
def check_sus_res():

	def post_check():
		stat=q.getCTNInfoList()
		print(stat)
		a=1
		while stat['status']==ctn_info['status']:
			stat=q.getCTNInfoList()
			a+=1
			if a==20:
				print(stat)
				print('20 попыток, достаточно...')
				break
		print(stat)
		print('Статус номера изменился после {}й проверки.'.format(a))

	q=bee_api(ctn=9679697678)
	q.get_token()
	ctn_info=q.getCTNInfoList()
	print(ctn_info)

	try:
		r=q.restoreCTN()
		print('Let\'s restore CTN...')
	except Exception:
		r=q.suspendCTN(rsn="WIO")
		print('Let\'s suspend CTN')
	req=q.getRequestList_one(req=r)
	a=1
	while 1:
		if req['requestStatus']=='IN_PROGRESS':
			req=q.getRequestList_one(req=r)
			a+=1
			if a==20:
				print(req)
				print('20 попыток, достаточно...')
				break
		else:
			for el in req.__keylist__:
				print(str(el)+" == "+ str(req.__getattribute__(el)))
			print('Статус запроса стал отличным от IN_PROGRESS при {}й проверке.'.format(a))
			post_check()
			break
	#print(q._getRequestList_one(req=2201125379))


def getCTNInfoList(*args):
	if re.match(r'9\d{9}',args[0][0]):
		api=bee_api(ctn=args[0][0])
		level='ctn'
	else:
		api=bee_api(ban=args[0][0])
		level='ban'
	try:
		login=args[0][1]
		password=args[0][2]
	except:
		login=None
		password=None
	if login!=None and password!=None:
		api.login=login
		api.password=password
		print(api.login,api.password)
	api.get_token()
	print('Получаем список номеров')
	rez=api.getCTNInfoList(level=level)
	els=[]
	if level=='ctn':
		els.append(rez)
	elif level=='ban':
		for el in rez:
			els.append([el['ctn'][1:],el['statusDate'],el['status'],el['activationDate'],el['pricePlan'],el['reasonStatus'],el['subscriberHLR'],el['lastActivity']])
	return els

def choice(args):

	try: args[1]
	except IndexError:
		print('ctn_down - выгрузить в excel параметры номера/номеров бана. Параметры - ban,login,password\n'
			  'ctn_show - отобразить параметры номера/номеров бана'
			  '\nserv - отобразить услуги номера')
	else:
		if args[1]=='ctn_down':
			pth="C:/Users/админ/Desktop/{}.xlsx".format(sys.argv[2])
			names=['Номер','Дата изменения статуса','Статус',"Дата активации",'Тариф','Причина изменения статуса',"HLR","Последняя активность"]
			rez=getCTNInfoList(args[2:])
			ex_write(names,rez,pth)
			print('Сохранили результат в Excel')

		elif args[1]=='ctn_show':
			rezult=getCTNInfoList(args[2:])
			print(rezult)


		elif args[1]=='serv':
			serv([args[2]])

		elif args[1]=='make_serv':
			make_services(args[2:])

		elif args[1]=='paym':
			paym(*args[2:])

		elif args[1]=='exit':
			sys.exit()

		elif args[1]=="req":
			getRequest(args[2:])

		elif args[1]=='remove_subscr':
			mass_remove_subscriptions(args[2:])



		else:
			print('ctn_down - выгрузить в excel параметры номера/номеров бана\n'
				  'ctn_show - отобразить параметры номера/номеров бана\n'
				  'serv - список услуг, подключенных на номере\n'
				  'make_serv - подключить/отключить услугу на номере\n'
				  'paym - платежи за указанную дату по заданным заранее БАНам\n'
				  'remove_subscr - отключение услуг на номерах из txt-файла'
				  'exit - выход')


def paym(*args):
	path='C:/Users/админ/Desktop/Служебные/Платежи'
	try:
		if args[0]=='help':
			print('Введите по запросу дату в формате ДД.ММ.\nExcel-файлы появятся на рабочем столе в папке "Платежи"')
			return
	except:
		pass
	names=['Номер','Дата платежа','Статус платежа','Тип платежа','Исходная сумма платежа',
		   'Текущая сумма платежа','ID п.п.','Дата последней активности с платежом']
	if not os.path.exists(path):
		os.mkdir(path)
	else:
		shutil.rmtree(path=path)
		os.mkdir(path)
	path=path+"/платежи_{}_{}.xlsx"
	rez=[]
	date=input('Введите дату, за которую нужны платежи в формате дд.мм ')
	if not re.match(r'^\d{2}[.]\d{2}$',date):
		raise PARAM_ERROR('Неверно введена дата')
	else:
		date=date.split('.')
	for el in [147807239,
132582827,
385816266,
414006137,
444722621,
176824529,
184989346,393589930]:
		b = BAN(ban=el, login='super_is', password='vbhe-Vbh22')
		api = bee_api(ban=b.ban)
		api.login = b.login
		api.password = b.password
		api.get_token()
		print('Начинаем {}, {}'.format(api.ban,date[0]+'.'+date[1]))
		rez = api.getPaymentList(level='ban', bday=int(date[0]), bmonth=int(date[1]), eday=int(date[0]), emonth=int(date[1]))
		ex_write(names=names, values=rez, path=path.format(b.ban, date[0]+'.'+date[1]))
		print('{} {} готов'.format(b.ban,date[0]+'.'+date[1]))


def make_services(*args):

	if args[0][0]=='help':
		print('Добавьте к запросу обязательные параметры через пробел:\nНОМЕР\nТЕХ.КОД УСЛУГИ\nA/D - подключить/отключить\nДД.ММ.ГГГГ - дату подключения/отключения')
		return
	ctn, soc, drct, date = args[0]
	api = bee_api(ctn)
	drct=drct.upper()
	api.get_token()
	if drct == 'A':
		print('подключаем')
		req = api.addDelSOC(DIR=drct, SOC=soc, effDate=date)
	elif drct == 'D':
		print('отключаем')
		req = api.addDelSOC(DIR=drct, SOC=soc, expDate=date)
		print('готово')
	else:
		print('ошибка')
		raise PARAM_ERROR('Подключить/отключить только A/D!')

	print('Готово, запрос {},логин {}, token {}'.format(req, api.login, api.token))
	return req,api.login,api.token

def check_ban():
	out=[]
	curs=conn.cursor()
	curs.execute('select ban,login,password from spicin.manual_access group by ban,login,password')
	access=curs.fetchall()
	a=0
	for el in access:
		ban,login,password=el
		api=bee_api(ban=ban)
		api.login=login
		api.password=password
		try:
			api.get_token()
		except Exception:
			out.append([ban,login,password,'нет доступа'])
			print('сделали {}'.format(a))
			a+=1
			continue
		try:
			rez=api.getCTNInfoListPaged()
		except Exception:
			out.append([ban,login,password,'не удалось получить данные по номерам'])
			print('сделали {}'.format(a))
			a+=1
			continue
		try:
			out.append([ban,login,password,rez[0][0].__getattribute__('ctn')])
		except TypeError:
			out.append([ban,login,password,'скорее всего, нет номеров'])
			print('сделали {}'.format(a))
			a+=1
			continue
		print('сделали {}'.format(a))
		a+=1
	ex_write(['ban','login','pass','итог'],out,path=d+'/гарант.xlsx')
	conn.close()

def mass_services():

	from openpyxl import load_workbook
	from datetime import datetime

	curs=conn.cursor()

	pth=input('Введите путь (корень - рабочий стол) ')
	filename=d+'/'+pth
	xl=load_workbook(filename).get_active_sheet()
	rezult_excel=[]
	def element(*row):

		def go(*args):
			try:
				print('{} услугу {} на номер {}'.format(act,service,ctn))
				req=make_services([ctn,service,act,str(datetime.now().date())])[0]
				print('Готово')
			except API_BASE_ERROR:
				return 'действие с услугой недоступно'
			else:
				api=bee_api(ctn=ctn)
				api.get_token()
				rezult=api.getRequestList_one(req=req)

				while rezult[0][0]['requestStatus']=='IN_PROGRESS':
					rezult=api.getRequestList_one(req=req)
				else:
					if rezult[0][0]['requestStatus']=='COMPLETE':
						print('Готово')
						return 'COMPLETE'
					else:
						print('Готово')
						return rezult[0][0]['requestStatus']

		ctn,service,descr,status,tarif,action=row[0]
		if action=='подключить':
			act='A'
		elif action=="отключить":
			act='D'
		else:
			return 'невозможное действие'
		curs.execute('select status from o_ctn where msisdn={}'.format(ctn))
		db_status=str(curs.fetchall()[0][0])
		if db_status=='1':
			rez=go(ctn,service,act)
		elif db_status=='0':
			api=bee_api(ctn=ctn)
			api.get_token()
			print('Разблокируем номер {}'.format(ctn))
			try:
				req=api.restoreCTN()
			except API_BASE_ERROR:
				print(db_status)
				try:
					rez=go(ctn,service,act)
					print('Блокируем {} обратно'.format(ctn))
					try:
						req=api.suspendCTN()
					except API_BASE_ERROR:
						print(db_status)
						return 'ошибка изменения статуса'
					pre_rez=api.getRequestList_one(req=req)
					while pre_rez[0][0]['requestStatus']=='IN_PROGRESS':
						pre_rez=api.getRequestList_one(req=req)
					print('Готово')
					return rez
				except:
					return 'ошибка'
			pre_rez=api.getRequestList_one(req=req)
			print(pre_rez)
			while pre_rez[0][0]['requestStatus']=='IN_PROGRESS':
				pre_rez=api.getRequestList_one(req=req)
			print('Готово')
			rez=go(ctn,service,act)
			print('Блокируем {} обратно'.format(ctn))
			try:
				req=api.suspendCTN()
			except API_BASE_ERROR:
				print(db_status)
				return 'ошибка изменения статуса'
			pre_rez=api.getRequestList_one(req=req)
			while pre_rez[0][0]['requestStatus']=='IN_PROGRESS':
				pre_rez=api.getRequestList_one(req=req)
			print('Готово')
			return rez
		else:
			return 'не наш номер'


	l=len(xl.rows)
	q=1
	for row in xl.rows:
		row_v=[]
		for cell in row:
			row_v.append(cell.value)

		row_v.append(element(row_v))
		rezult_excel+=[row_v]
		print('Сделали {} из {}'.format(q,l))
		q+=1
	print(rezult_excel)
	ex_write(['ctn','service','descr','status','tarif','action'],values=rezult_excel,path=d+'\services_out.xlsx')
	conn.close()

def get_mass_services():
	banlist=session.query(a)
	ctnlist=session.query(ctn.msisdn).filter
	rez=[]
	for line in file.readlines():
		print(line.rstrip())
		api=bee_api(ctn=line.rstrip())
		api.get_token()
		serv=api.getServicesList()
		rec=[]
		for s in serv:
			for el in s.__keylist__:
				rec.append(s.__getattribute__(el))
			rez.append(rec)
	ex_write(names=['','','','','','',''],values=rez,path='out.xlsx')
	print('Готово')

def get():
	for ban in [370174062,429313574,434332598,434573783,434573954,434574188,434574645]:
		print('Начинаю с {}'.format(ban))
		api=bee_api(ban=ban)
		api.get_token()
		for per in ["2014-05-31","2014-06-30","2014-07-31","2014-08-31"]:
			print('Период {}'.format(per))
			req=api.createBillChargesRequest(bD=per)
			while 1:
				try:
					rez=api.getBillCharges(req=req)
				except API_BASE_ERROR:
					print('Не готово, подождем...')
					time.sleep(20)
					continue
			print('Получил, сохраняю')
			ex_write(names=rez[0].__keylist__,values=rez,path='C:/Users/админ/Desktop/табло/{}_{}.xlsx'.format(ban,per))

def mass_remove_subscriptions(*args):

	file=open(args[0][0]).readlines()
	rezults=[]
	for el in file:
		api = RestClient(ctn=el.rstrip())
		try:
			api.get_token()
		except GrabTimeoutError:
			while 1:
				api.get_token()
				break
		except Exception:
			print(el)
			continue
		try:
			subscrs = api.get_subscriptions()['subscriptions']
		except GrabTimeoutError:
			while 1:
				subscrs = api.get_subscriptions()['subscriptions']
				break
		if subscrs is None:
			rezults.append([api.ctn,'','Подписок не было'])
			print('{}, не было подписок'.format(el))
		else:
			for sub in subscrs:
				try:
					one=api.remove_subscribtion(sub['id'],sub['type'])['requestId']
					rezults.append([api.ctn,one])
				except GrabTimeoutError:
					while 1:
						rezults.append([api.ctn,api.remove_subscribtion(sub['id'],sub['type'])['requestId']])
						break
				except Exception as e:
					rezults.append([api.ctn,'','Ошибка {}'.format(e)])
		print('Проверили подписки на {1} из {0} номеров, заявок на отключение создали {2}'.
				  format(len(file),
						 file.index(el)+1,
			  len(rezults)))

	if len(rezults) == 1:
		print(api.get_request_status(rezults[0][1]))
	else:
		for rez in rezults:
			api=RestClient(ctn=rez[0])
			try:
				api.get_token()
			except GrabTimeoutError:
				while 1:
					api.get_token()
					break

			try:
				req=api.get_request_status(rez[1])["requestList"][0]['requestStatus']
				rez.append(req)
			except GrabTimeoutError:
				while 1:
					req=api.get_request_status(rez[1])["requestList"][0]['requestStatus']
					rezults[rezults.index(rez)]=rez.append(req)
					break
			print('Проверили отключение {} из {}'.format(len(rezults),
														 rezults.index(rez)))

	print('Сохраняем результат')
	try:

		ex_write(names=['Номер', 'Заявка', 'Результат'],values=rezults,path='C:/Users/админ/Desktop/subscr_rez.xlsx')
	except:
		for el in rezults:
			if el[2] != 'OK':
				print(el)
#достпные на пле москва тарифы
def checkPP():
	agree=class_getter().get('operator_agree')
	account=class_getter().get('account_info')
	ctn=class_getter().get('ctn')
	bans = session.query(agree.i_id).filter(agree.payment_type==1,agree.region==1,agree.moboperator==1).all()
	bans = [el[0] for el in bans]

	ctns = session.query(ctn.msisdn).filter(ctn.operator_agree.in_(bans)).group_by(ctn.operator_tarif).all()
	ctns = [el[0] for el in ctns]
	rezult=[]
	for phone in ctns:
		api=RestClient(ctn=phone)
		try:
			api.get_account_info()
			api.get_token()
			rez=api.get_available_pp()['availablePricePlans']

			c_pp=api.get_PP()['pricePlanInfo']
		except Exception as e:
			print(phone)
			print(e)
			continue
		for pp in rez:
			rezult.append([c_pp['name'],c_pp['entityName'],pp['name'],pp['entityName'],pp['rcRate'],pp['chargeAmount']])
		print('{} из {}'.format(ctns.index(phone)+1,len(ctns)))
	names=['Техкод','Название','АП','Стоимость перехода']
	try:
		ex_write(names,rezult,path='C:/Users/админ/Desktop/pp.xlsx')
	except Exception:
		print(rezult)







if __name__ == '__main__':
	if len(sys.argv)>1:
		choice(sys.argv)