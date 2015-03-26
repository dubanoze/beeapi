from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy.dialects.mysql import MEDIUMINT, DECIMAL, INTEGER, VARCHAR, DATETIME, TINYINT, ENUM, LONGTEXT
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import relationship, backref
from const import db_access
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

DB_DRIVER = 'pymysql'
eko_engine = create_engine('mysql+{0}://'
                       '{user}:{passwd}'
                       '@{host}:{port}/ekomobile?charset=cp1251'.format(DB_DRIVER, **db_access), encoding='cp1251')


spicin_engine = create_engine('mysql+{0}://'
                       '{user}:{passwd}'
                       '@{host}:{port}/spicin?charset=cp1251'.format(DB_DRIVER, **db_access), encoding='cp1251')

Base = declarative_base()


class Object(Base):
    """Describe table with objects (other tables)"""
    __tablename__ = 'a_objects'
    object_id = Column(INTEGER(unsigned=True), primary_key=True, nullable=False)
    name = Column(VARCHAR(length=50), nullable=False, unique=True)  # system class name
    ru_name = Column(VARCHAR(length=50), nullable=False)  # human class name
    description = Column(VARCHAR(length=250))
    table = Column(VARCHAR(length=50))  # table name of class instances
    id_field = Column(VARCHAR(length=50))  # name of class's id field

    properties_t = relationship('Properties', backref='a_properties',
                                primaryjoin="Object.object_id==Properties.object_id")  # related properties


class Properties(Base):
    """Describe table with Properties (pole-names of objects)"""
    # TODO add other meta-attributes of object parameters
    __tablename__ = 'a_properties'

    def _get_val_storage(st):
        st = st
        if st == 0:
            return 'historic'
        elif st == 1:
            return "nonhistoric"
        elif st == 2:
            return "cached"


    property_id = Column(MEDIUMINT(unsigned=True), primary_key=True, nullable=False)

    object_id = Column(INTEGER(unsigned=True), ForeignKey('a_objects.object_id'),
                       nullable=False)  # ID of Object

    name = Column(VARCHAR(length=50), nullable=False)  # system name of property
    ru_name = Column(VARCHAR(length=64), nullable=False)  # humanity name of property
    storage = Column(TINYINT(unsigned=True), nullable=False)  # 0-nonhistoric; 1-historic; 2-cached

    storage_table = Column(VARCHAR(length=50, unicode=True, charset='utf8'))
    indicator = Column(TINYINT(unsigned=True), nullable=False)
    data_type = Column(ENUM('varchar', 'int', 'date', 'dec', 'text'), nullable=False)  # properties data type
    ref_object = Column(INTEGER(unsigned=True),
                        ForeignKey('a_objects.object_id'))  # id of linked property
    ref_object_label = Column(VARCHAR(length=50, unicode=True, charset='utf8'))  # name of showing property
    unique = Column(TINYINT(unsigned=True),
                    nullable=False)  # unique or not
    description = Column(VARCHAR(length=250))  # property description
    required = Column(TINYINT(unsigned=True), nullable=False)  # required

    object = relationship('Object', uselist=False, backref=backref('a_object'), foreign_keys=ref_object,
                          primaryjoin="Object.object_id==Properties.ref_object")


class ClassGetter():
    def __repr__(self):
        return 'ClassGetter'

    @staticmethod
    def get(class_name=None, class_id=None, ref=False):
        def get_link_attrib(object_id, prop_id):
            rez = ClassGetter.get(class_id=object_id)

            # получаем аттрибуты класса

        def _getattr(attribute):
            types = {
                'varchar': VARCHAR(length=255),
                'int': INTEGER,
                'date': DATETIME,
                'dec': DECIMAL,
                'text': LONGTEXT,
                'raw': VARCHAR(length=255)
            }
            out_attrib = Column(attribute.name, types[attribute.data_type])
            out_attrib.label(attribute.name+'_')
            if attribute.required:
                out_attrib.nullable = False
            else:
                out_attrib.nullable = True
            if attribute.ref_object:
                pass
            #  TODO: make returning linked object
            if ref:
                pass
            return out_attrib

        if class_name:  # searching by class name
            try:
                result = session_eko.query(Object).filter(Object.name == class_name).one()

            except MultipleResultsFound:
                print('Objects with class name="{}" > 1'.format(class_name))
                return
            except NoResultFound:
                print('No objects with class name="{}" > 1'.format(class_name))
                return

        elif class_id:  # searching by class id
            result = session_eko.query(Object).filter(Object.object_id == class_id).one()
        else:
            raise AttributeError('Must have className or classId')

        attributes = {'__tablename__': result.table}
        attributes['__attr_list__'] = []
        for attrib in result.properties_t:
            attributes[attrib.name] = _getattr(attrib)
            attributes['__attr_list__'].append(attrib.name)
        attributes[result.id_field] = Column(result.id_field, INTEGER, nullable=False, primary_key=True)
        attributes['__table_args__'] = {'extend_existing': True,  # allows create same objects in one runtime
                                        'prefixes': ["TEMPORARY"]}  # always creating temporary table
        attributes['user_id'] = Column('user_id', INTEGER, nullable=False)
        attributes['date_in'] = Column('date_in', DATETIME, nullable=False)
        attributes['date_ch'] = Column('date_ch', DATETIME, nullable=False)
        attributes['__attr_list__'].append('user_id')
        attributes['__attr_list__'].append('date_in')
        attributes['__attr_list__'].append('date_ch')
        attributes['__attr_list__'].append('i_id')
        attributes['prefixes'] = ["TEMPORARY"]



        return type(result.name, (Base,), attributes)  # returns new class with Properties of Object instance


#Base.metadata.create_all(engine)
Session_eko = sessionmaker(bind=eko_engine)
session_eko = Session_eko()

Session_spicin = sessionmaker(bind=spicin_engine)
session_spicin = Session_spicin()

def create_temp_table(obj):
    obj.__table__.create(spicin_engine)
    return session_spicin