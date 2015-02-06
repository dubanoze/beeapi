from bill_classes import session, class_getter
from client import RestClient, SoapClient
from const import conn_eko as conn
from xwritter import ex_write
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_
from mysql.connector.errors import InterfaceError
from datetime import datetime

ctn = class_getter().get('ctn')
agree = class_getter().get('operator_agree')
accounts = class_getter().get('account_info')
btp = class_getter().get('operator_tarif')
services = class_getter().get('service_fx')

rapi = RestClient()
curs = conn.cursor()


def get_mass_serv():
    banlist = session.query(agree.i_id).filter(agree.moboperator == 1, agree.payment_type == 0,
                                               agree.discontinued == 0).all()
    banlist = [el[0] for el in banlist]
    ctnlist = session.query(ctn.msisdn, ctn.operator_tarif).filter(
        ctn.operator_agree.in_(banlist), ctn.status == 1).group_by(ctn.operator_tarif).all()
    result = []

    for el in ctnlist:

        rapi.change_owner(ctn=int(el[0]))
        rez = rapi.get_available_services()['availableServices']
        if len(rez) == 0:
            print(rapi.ctn)
        for r in rez:
            tarif = session.query(btp.name).filter(btp.i_id == int(el[1])).one()[0]
            try:
                serv = session.query(services.i_id).filter(services.bee_sync == r['name']).one()[0]
            except NoResultFound:
                serv = 'Нет в билле!'
            result.append([rapi.ctn, el[1], tarif, serv, r['name'], r['entityName'], r['rcRate']])
        print('{} из {}'.format(ctnlist.index(el) + 1, len(ctnlist)))

    names = ['Номер', 'Тариф', 'Техкод услуги', 'Название услуги', 'АП услуги']

    ex_write(names, result, path='C:/Users/админ/Desktop/services.xlsx')


def check_detail():
    """проверка деталки"""
    sapi = SoapClient()

    def get_det(num):
        sapi.change_owner(num)
        rez = sapi.get_current_detail()
        names = [el for el in rez[0]]
        detal = []
        for rec in rez:
            detal.append([rec[key] for key in rec])
        ex_write(names, detal, 'C:/Users/админ/Desktop/деталка/{}_API.xlsx'.format(num))
        print('Get detail from API')


    curs.execute('select phone from numbers where d_callcharge>3000 limit 2,20')
    phones = curs.fetchall()
    phones = [int(phone[0]) for phone in phones]
    for phone in phones:
        print('Check {}'.format(phone))
        get_det(phone)
        print('{} of {}'.format(
            phones.index(phone) + 1,
            len(phones)
        ))
        if input('Next? y/n ') == 'n':
            break


def check_bills():
    '''проверка наличия услуг в биллинге'''
    ser = class_getter().get('hstr_service_fx')
    service_fx = class_getter().get('service_fx')

    file = open('C:/Users/админ/Desktop/1.txt').readlines()
    rez_f = []
    for el in file:
        phone, off, on = el.split(';')
        rez_f.append({'phone': phone.rstrip(), 'on': on.rstrip(), 'off': off.rstrip()})

    on = [[el['phone'], el['on']] for el in rez_f if el['on'] != '']
    off = [[el['phone'], el['off']] for el in rez_f if el['off'] != '']

    for el in on:
        phone, service = el
        try:
            sid = session.query(service_fx.i_id).filter(service_fx.bee_sync == service.rstrip()).one()[0]
        except NoResultFound:
            print(el, 'неверные параметры, должна быть подключена')
            continue

        hstr = session.query(ser).filter(ser.object_id == phone.rstrip(),
                                         ser.service_id == sid,
                                         ser.activated < datetime.now(),
                                         or_(ser.deactivated == None,
                                             ser.deactivated > datetime.now())).all()
        if len(hstr) == 0:
            print(el, ' не подключена, должна быть подключена')

    for el in off:
        phone, service = el
        try:
            sid = session.query(service_fx.i_id).filter(service_fx.bee_sync == service.rstrip()).one()[0]
        except NoResultFound:
            print(el, 'неверные параметры, должна быть отключена')
            continue
        hstr = session.query(ser).filter(ser.object_id == phone.rstrip(),
                                         ser.service_id == sid,
                                         ser.deactivated < datetime.now(),
                                         or_(ser.deactivated == None,
                                             ser.deactivated > datetime.now())).all()
        if len(hstr) != 0:
            print(el, ' не отклчена, должна быть отключена')