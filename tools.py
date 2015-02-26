from bill_classes import session, ClassGetter
from client import Rest, Soap
from xwritter import ex_write
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_
from datetime import datetime
import sqlite3
import warnings








def get_mass_serv():

    rapi = Rest()
    services = ClassGetter.get('service_fx')
    agree = ClassGetter.get('operator_agree')
    ctn = ClassGetter.get('ctn')
    btp = ClassGetter.get('operator_tarif')
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

    try:
        ex_write(names, result, path='C:/Users/ГостЪ/Desktop/services.xlsx')
    except ValueError:
        return result
    else:
        return


def check_detail():

    """проверка деталки"""
    sapi = Soap()

    def get_det(num):
        sapi.change_owner(num)
        rez = sapi.get_current_detail()
        names = [el for el in rez[0]]
        detal = []
        for rec in rez:
            detal.append([rec[key] for key in rec])
        ex_write(names, detal, 'C:/Users/админ/Desktop/деталка/{}_API.xlsx'.format(num))
        print('Get detail from API')


  #  curs.execute('select phone from numbers where d_callcharge>3000 limit 2,20')
   # phones = curs.fetchall()
    phones = [int(phone[0]) for phone in [1]]
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
    ser = ClassGetter.get('hstr_service_fx')
    service_fx = ClassGetter.get('service_fx')

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

def get_some_db():
    agree = ClassGetter.get('operator_agree')
    ctn = ClassGetter.get('ctn')
    accounts = ClassGetter.get('account_info')

    agrees = session.query(agree.i_id, agree.oan, agree.name, agree.payment_type).filter(agree.region==1).all()
    agrees_id = [el[0] for el in agrees]
    ctns = session.query(ctn.i_id,ctn.msisdn,ctn.operator_agree).filter(ctn.operator_agree.in_(agrees_id)).all()
    accs = session.query(accounts.i_id, accounts.login, accounts.password,accounts.operator_agree).\
        filter(accounts.operator_agree.in_(agrees_id),accounts.access_type==1).group_by(accounts.operator_agree).all()

    conn = sqlite3.connect('eko_mini.db')
    curs = conn.cursor()

    curs.execute('create table agrees (i_id integer primary key,'
                 'oan integer, name text, payment_type integer)')
    #curs.execute('create table agrees ')

def get_off_services():

    services = ClassGetter.get('service_fx')
    hstr_services = ClassGetter.get('hstr_service_fx')
    rezult = []
    sers = session.query(hstr_services.object_id, hstr_services.service_id).\
		filter(or_(hstr_services.deactivated==None,
				   hstr_services.deactivated>datetime.now())).\
		group_by(hstr_services.service_id).all()
    print('Getted services list')

    for rec in sers:


        rapi = Rest(ctn=int(rec[0]))
        ser_name = session.query(services.bee_sync).filter(services.i_id==int(rec[1]),services).one()[0]
        api_sers = rapi.get_services_list()['services']
        for ser in api_sers:
            if ser['name']==ser_name:
                rezult.append([ser_name,ser['removeInd']])
        if rezult[-1][0]!=ser_name:
            warnings.warn('Kosyak, phone={}, service={}'.format(rapi.ctn,ser_name))
        print('Made {} of {}'.format(sers.index(rec)+1,len(sers)))
    try:
        ex_write(['code','y/n'],rezult,"C:/Users/админ/Desktop/remove_services.xlsx")
    except Exception:
        return rezult

def check_subscription(nums):
    rapi = Rest()

    rez = []
    for phone in nums:
        try:
            rapi.change_owner(ctn=str(phone).strip())
        except NoResultFound:
            continue
        if len(rapi.get_subscriptions()['subscriptions'])>0:
            rez.append(rapi.ctn)
        print('Ready {} of {}'.format(nums.index(phone)+1,len(nums)))
    print(rez)

def remove_subscription(nums='C:/Users/админ/Desktop/1.txt'):
    rapi = Rest()

    if not isinstance(nums, list):
        nums = open(nums).readlines()
    for phone in nums:
            rapi.change_owner(ctn=str(phone).strip())
            subscrs = rapi.get_subscriptions()['subscriptions']
            for el in subscrs:
                rapi.remove_subscribtion(sId=el['id'],type=el['type'])
            if len(subscrs)>0:
                print('Made {} request(-s) for {}th of {} numbers'.format(
                    len(subscrs),
                    nums.index(phone)+1,
                    len(nums)
                ))
            else:
                print('Didn\'t found subscriptions on {}.\n{}th of {} numbers'.format(
                    phone,
                    nums.index(phone)+1,
                    len(nums)
                ))

    check_subscription(nums)

def check_sim():

    sapi = Soap()
    nums = [[	9653471202	,	897019914051244936	,	9052555979	,	897019912102959356	],
            [9672092303	,	897019914051244868	,	9052366533	,	897019912031511672	],
            [	9653508738	,	897019914072751440	,	9602543269	,	897019914024242348	],
            [	9653508915	,	897019914072751439	,	9602543267	,	897019914024242341	],
            [	9672095910	,	897019914044848304	,	9602348121	,	897019914101216731	],
            [	9653578212	,	897019914072751372	,	9602542729	,	897019914082848694	]]

    for row in nums:
        sapi.change_owner(ctn=row[0])
        v_sim = sapi.get_sim_list()[0]['serialNumber']
        sapi.change_owner(row[2])
        r_sim = sapi.get_sim_list()[0]['serialNumber']
        print('Old: {}\nNew:\nvirt:{}\nreal:{}'.format(row,v_sim,r_sim))

def update_objects(classname, key, path='C:/Users/админ/Desktop/1.txt'):
    """required classname and key"""

    c_class = ClassGetter.get(classname)
    if input('First line - system names, second and other - values (Y/n)? ') not in ["y,Y",""]:
        return
    with open(path) as file:
        names = file.readline().split('\t')
        names = [el.strip() for el in names]
        values = file.readlines()[1:]
        for val in values:
            #if it possible - making digits, else stripping
            val_u = [int(el) if el.strip().isdigit() else el.strip() for el in val.split('\t')]
            items = dict(zip(names,val_u))
            serv = session.query(c_class).filter(getattr(c_class,key) == items[key]).one()

            for key in items:
                #if value not null...
                if items[key] != "":
                    setattr(serv,key,items[key])
            print('Ready {} of {}'.format(values.index(val)+1,len(values)))

        session.commit()
        print('That\'s all')


