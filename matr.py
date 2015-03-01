from bill_classes import ClassGetter, session as eko_ses

from sqlalchemy import Column, Integer, String, create_engine, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from const import eko_access
import gspread
import pickle
import logging
logging.basicConfig(level = logging.DEBUG)

engine = create_engine('mysql+mysqlconnector://'
                       '{user}:{password}'
                       '@{host}:{port}/spicin'.format(**eko_access))
Base = declarative_base()

class s_o_tariff_mobile_data(Base):
    __tablename__ = 'o_tariff_mobile_data'
    __table_args__ = {'extend_existing': True}
    i_id = Column(Integer, primary_key=True)
    tariff_mobile = Column(Integer)
    conn_type_ex = Column(Integer)
    abonent_location = Column(Integer)
    call_direction = Column(Integer)
    price = Column(Float)
    packet = Column(Integer)
    conn_subtype = Column(Integer)
    description = Column(String(255))
    priority = Column(Integer)
    footnote = Column(String(255))

class s_o_tariff_mobile_packet(Base):
    __tablename__ = 'o_tariff_mobile_packet'
    __table_args__ = {'extend_existing': True}
    i_id = Column(Integer, primary_key=True)
    name = Column(String(255))
    value = Column(Float)
    measure = Column(Integer)

class s_o_tariff_mobile(Base):
    __tablename__ = 'o_tariff_mobile'
    __table_args__ = {'extend_existing': True}
    i_id = Column(Integer, primary_key=True)
    name = Column(String(255))
    region = Column(Integer)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

tariff_data = ClassGetter.get('tariff_mobile_data')
abonent_location = ClassGetter.get('abonent_location')
call_direction = ClassGetter.get('call_direction')
tariff_mobile_packet = ClassGetter.get('tariff_mobile_packet')
tariff_mobile = ClassGetter.get('tariff_mobile')
conn_subtype = ClassGetter.get('conn_subtype')

def check_val(val, val_name, obj, subv=None):
    if isinstance(val, str):
        s = val.strip().split('/')
    else:
        s = [val]
    for el in s:
        if el:
            try:
                if not subv:
                    try:
                        rez = eko_ses.query(obj.i_id).filter(getattr(obj, 'name') == el).one()
                    except AttributeError:
                        print(val, val_name, obj, subv)
                        raise
                else:
                    rez = session.query(obj.i_id).filter(getattr(obj, 'name') == el,getattr(obj, 'measure') == subv).one()
            except NoResultFound:
                logging.warning("Unavailable value {} of {}".format(el, val_name))
            else:
                return rez[0]

def update_val(obj, insert=True, **values):
    if insert:
        obj.insert().values(**values)

def check_values(record, num):
    def check(val):
        if isinstance(val, str):
            if val.count('.201') > 0:
                val = val[:val.index('.201')]
            if val.count(',') > 0:
                val = val.replace(',', '.')
        return round(float(val),2)

    to_insert = dict()
    for el in ['tariff_mobile', 'abonent_location', 'call_direction', 'conn_subtype']:
        val = check_val(record[el], el, globals()[el])
        if isinstance(val, int):
            to_insert[el] = val
        elif not val:
            to_insert[el] = None
        else:
            logging.warning('{} of {} record not supported'.format(val, record))
    if record['Шаблон']:
        to_insert['description'] = record['Шаблон']
    if record['payment_type'] == 'минуты':
        p_type = 1
    elif record['payment_type'] == 'смс/ммс':
        p_type = 2
    elif record['payment_type'] == 'рубли':
        p_type = 4
    elif record['payment_type'] == 'Мб':
        p_type = 3
    else:
        p_type = None
    if p_type in [1, 2, 3]:
        try:
            pack_r = check_val(record['tariff_mobile_packet'], 'tariff_mobile_packet', globals()['tariff_mobile_packet'], p_type)
        except NoResultFound:

            new_pack = s_o_tariff_mobile_packet(
                name = '{} {}'.format(int(record['tariff_mobile_packet']), record['payment_type']),
                value = int(record['tariff_mobile_packet']),
                measure = p_type
            )
            session.add(new_pack)
            try:
                session.flush()
            except Exception:
                logging.warning('{}'.format(record['tariff_mobile_packet']))
                raise
            session.refresh(new_pack)
            pack_r = new_pack.i_id
            logging.info("Added new pack i_id={}; {}; id={}; value={}".format(pack_r, record['payment_type'], p_type,record['tariff_mobile_packet']))
        finally:
            to_insert['packet'] = pack_r

    else:
        try:
            to_insert['price'] = check(record['tariff_mobile_packet'])
        except Exception:
            logging.warning("Incorrect value {}, rec_id={}; record:{}".format(record['tariff_mobile_packet'], num, record))
    new_par = s_o_tariff_mobile_data(**to_insert)
    session.add(new_par)

def main(p=1, f=0):
    if p == 1:
        with open('C:/Users/ГостЪ/Desktop/vals.pickle', 'rb') as file:
            vals = pickle.load(file)
            logging.info('Loaded values')
    else:
        gc = gspread.login('a.spicin@ekomobile.ru', '1qazse4rfv')
        logging.info('Connected to GSpread')

        wks = gc.open('МегаМатрица')
        ws = wks.worksheet('тарификационные параметры ')
        logging.info('Downloading records from GSpread')
        vals = ws.get_all_records()
        with open('C:/Users/ГостЪ/Desktop/vals.pickle', 'wb') as file:
            pickle.dump(vals, file)
            logging.info('Loaded values')
        logging.info("Ready")


    for rec in vals[f:]:
        if rec['object_type'] == "тариф корпорации":
            try:
                check_values(rec, vals.index(rec))
            except Exception:
                logging.warning(vals.index(rec))
                raise
            if vals.index(rec) % 150 == 0:
                logging.info('Ready {} of {} records'.format(vals.index(rec), len(vals)))

if __name__ == "__main__":
    main()