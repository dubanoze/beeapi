from bill_classes import session, ClassGetter
from client import Rest, Soap
from xwritter import ex_write
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_
from datetime import datetime
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


def check_bills():
    """проверка наличия услуг в биллинге"""
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
                                         or_(not ser.deactivated,
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
                                         or_(not ser.deactivated,
                                             ser.deactivated > datetime.now())).all()
        if len(hstr) != 0:
            print(el, ' не отклчена, должна быть отключена')


def get_off_services():

    services = ClassGetter.get('service_fx')
    hstr_services = ClassGetter.get('hstr_service_fx')
    result = []
    sers = session.query(hstr_services.object_id, hstr_services.service_id).\
        filter(or_(not hstr_services.deactivated,
                   hstr_services.deactivated > datetime.now())).\
        group_by(hstr_services.service_id).all()
    print('Get services list')

    for rec in sers:


        rapi = Rest(ctn=int(rec[0]))
        ser_name = session.query(services.bee_sync).filter(services.i_id == int(rec[1]), services).one()[0]
        api_sers = rapi.get_services_list()['services']
        for ser in api_sers:
            if ser['name'] == ser_name:
                result.append([ser_name, ser['removeInd']])
        if result[-1][0] != ser_name:
            warnings.warn('Kosyak, phone={}, service={}'.format(rapi.ctn, ser_name))
        print('Made {} of {}'.format(sers.index(rec)+1, len(sers)))
    try:
        ex_write(['code', 'y/n'], result, "C:/Users/админ/Desktop/remove_services.xlsx")
    except Exception:
        return result


def check_subscription(nums):
    rapi = Rest()

    rez = []
    for phone in nums:
        try:
            rapi.change_owner(ctn=str(phone).strip())
        except NoResultFound:
            continue
        if len(rapi.get_subscriptions()['subscriptions']) > 0:
            rez.append(rapi.ctn)
        print('Check {} of {}'.format(nums.index(phone)+1, len(nums)))
    print('Now count of active subscriptions = {}'.format(len(rez)))

def remove_subscription(nums='C:/Users/админ/Desktop/1.txt', begin=0):
    rapi = Rest()
    count = 0

    if not isinstance(nums, list):
        nums = open(nums).readlines()
    for phone in nums[begin:]:
            rapi.change_owner(ctn=str(phone).strip())
            subscrs = rapi.get_subscriptions()['subscriptions']
            count += len(subscrs)
            for el in subscrs:
                rapi.remove_subscribtion(sId=el['id'], type=el['type'])
            if len(subscrs) > 0:
                print('Made {} request(-s) for {}th of {} numbers'.format(
                    count,
                    nums.index(phone)+1,
                    len(nums)
                ))
            else:
                print("Didn't found subscriptions on {}.\n{}th of {} numbers".format(
                    phone.strip(),
                    nums.index(phone)+1,
                    len(nums)
                ))
    print('Totally made {} requests for remove subscriptions'.format(count))
    if count != 0:
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
        names = [el.strip() for el in file.readline().split('\t')]
        values = file.readlines()[1:]
        for val in values:
            #if it possible - making digits, else stripping
            val_u = [int(el) if el.strip().isdigit() else el.strip() for el in val.split('\t')]
            items = dict(zip(names, val_u))
            serv = session.query(c_class).filter(getattr(c_class, key) == items[key]).one()
            for key in items:
                #if value not null...
                if items[key] != "":
                    setattr(serv, key, items[key])
            print('Ready {} of {}'.format(values.index(val)+1, len(values)))

        session.commit()
        print('That\'s all')


