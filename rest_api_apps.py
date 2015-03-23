import os, time

from client import Rest
from soap_api import bee_api as SoapApi
from xwritter import ex_write
from bill_classes import class_getter, session


def get_access(num):
    ctn = class_getter().get('ctn')
    acc = class_getter().get('account_info')
    n = session.query(ctn.operator_agree).filter(ctn.msisdn == num).one()
    log, passw = session.query(acc.login, acc.password).filter(acc.operator_agree == n.operator_agree).filter(
        acc.access_type == 1).one()
    return log, passw


def available_one(num):
    ctn = class_getter().get('ctn')
    acc = class_getter().get('account_info')
    n = session.query(ctn.operator_agree).filter(ctn.msisdn == num).one()
    log, passw = session.query(acc.login, acc.password).filter(acc.operator_agree == n.operator_agree).filter(
        acc.access_type == 1).one()
    ap = Rest(ctn=num, login=log, password=passw)
    ap.get_available_services('save')
    print('done')


def available_all():
    ctn = class_getter().get('ctn')
    acc = class_getter().get('account_info')
    oan = class_getter().get('operator_agree')
    btp = class_getter().get('operator_tarif')

    filelist = os.listdir('C:/Users/админ/Desktop/REST_API/Проверка услуг')
    readylist = []
    for el in filelist:
        readylist.append(el[:el.find('_9')])

    op_tp_list = session.query(btp.i_id).filter(btp.moboperator == 1, ~btp.name.in_(readylist)).all()
    op_tp_list = [el[0] for el in op_tp_list]
    print('Получили список нужных тарифов')
    oan_list = session.query(oan.i_id).filter(oan.moboperator == 1, oan.payment_type == None).all()
    oan_list = [el[0] for el in oan_list]

    print('получили список договоров')

    ctn_list = session.query(ctn.msisdn, ctn.operator_agree).filter(ctn.operator_agree.in_(oan_list),
                                                                    ctn.status == 1).group_by(ctn.operator_tarif).all()
    print('получили список номеров')
    for el in ctn_list:
        l_a = None
        query = session.query(acc.login, acc.password).filter(acc.operator_agree == el.operator_agree).filter(
            acc.access_type == 1)
        try:
            log, passw = query.one()
        except:
            try:
                l_a = query.all()
            except:
                print(el.msisdn, el.operator_agree)
                raise Exception

        if l_a:
            for acc_a in l_a:
                log, passw = acc_a
                ap = Rest(ctn=el.msisdn, login=log, password=passw)
                ap.get_token()
                break
        else:
            ap = Rest(ctn=el.msisdn, login=log, password=passw)
        ap.get_available_services('save')
        print('Сделали {} из {}, номер {}'.format(ctn_list.index(el), len(ctn_list), el.msisdn))
    print('done')


def availables():
    ctn = class_getter().get('ctn')
    acc = class_getter().get('account_info')
    oan = class_getter().get('operator_agree')
    btp = class_getter().get('operator_tarif')
    file = open("C:/Users/админ/Desktop/1.txt").readlines()
    rez = []
    for number in file:
        pre_rez = []
        ctn_n = session.query(ctn.msisdn, ctn.operator_agree, ctn.operator_tarif, ctn.status).filter(
            ctn.msisdn == number.rstrip()).one()
        ctn_tp = session.query(btp.name).filter(btp.i_id == ctn_n.operator_tarif).one()
        query = session.query(acc.login, acc.password).filter(acc.operator_agree == ctn_n.operator_agree).filter(
            acc.access_type == 1)
        log, passw = query.one()
        RApi = Rest(ctn=ctn_n.msisdn, login=log, password=passw)
        RApi.get_token()
        SApi = SoapApi()
        SApi.ctn = number
        SApi.token = RApi.token
        if RApi.get_status()['status'] == "S":
            print('Разблокируем {}'.format(ctn_n.msisdn))
            SApi.restoreCTN()
            while 1:
                if RApi.get_status()['status'] == "S":
                    time.sleep(1)
                else:
                    print('Готово')
                    break
        print('Получаем список доступных услуг')

        RApi.grabber.setup(cookies={'token': RApi.token})
        r = RApi.get_available_services()['availableServices']
        pre_rez = [[el, ctn_tp, number] for el in r]
        rez.append(pre_rez)

        print('Сохранили полученный список в общий')
        if RApi.get_status()['status'] == "A":
            SApi.suspendCTN()
            print('Блокируем обратно')
        print('Сделали {} из {}'.format(file.index(number), len(file)))
    return rez
    ex_write(names=['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''], values=rez,
             path='C:/Users/админ/Desktop/рез.xlsx')


def get_tarifs():
    ctn = class_getter().get('ctn')
    agr = class_getter().get('operator_agree')
    accs = class_getter().get('account_info')
    agrs = session.query(agr.i_id).filter(agr.moboperator == 1).all()
    agrs = [el[0] for el in agrs]
    ctns = session.query(ctn.msisdn, ctn.operator_tarif, ctn.operator_agree).filter(
        ctn.operator_agree.in_(agrs)).group_by(ctn.operator_tarif).all()
    out = []
    errors = []
    for phone in ctns:
        rez_acc = session.query(accs.login, accs.password).filter(accs.operator_agree == phone[2],
                                                                  accs.access_type == 1).all()
        if not rez_acc:
            errors.append([[phone, rezultFee]])
            continue
        for access in rez_acc:
            log, passw = access
            api = Rest(ctn=phone[0], login=log, password=passw)

            try:
                api.get_token()
            except:
                continue
            else:
                break

        try:
            rezultFee = api.get_PP()['pricePlanInfo']['rcRate']
        except:
            errors.append([phone, api])
        out.append([phone, rezultFee])
        print('{} {}'.format(ctns.index(phone) + 1, len(ctns)))
    ex_write(names=['', '', '', '', '', '', '', '', '', '', ''], values=out, path='C:/Users/админ/Desktop/tp_fee.xlsx')
    print(errors)


if __name__ == '__main__':
    get_tarifs()
