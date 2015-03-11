from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy.dialects.mysql import MEDIUMINT, DECIMAL, INTEGER, VARCHAR, DATETIME, TINYINT, ENUM, LONGTEXT
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import relationship, backref
from const import eko_access
from sqlalchemy.orm.exc import MultipleResultsFound

DB_DRIVER = 'pymysql'
engine = create_engine('mysql+{DB_DRIVER}://'
                       '{user}:{passwd}'
                       '@{host}:{port}/ekomobile'.format(DB_DRIVER, **eko_access))
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
                                primaryjoin="Object.object_id==Properties.object_id") #related properties


class Properties(Base):
    """Describe table with Properties (pole-names of objects)"""
    #TODO add other meta-attributes of object parameters
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
                       nullable=False)  #ID of Object

    name = Column(VARCHAR(length=50), nullable=False)  # system name of property
    ru_name = Column(VARCHAR(length=64), nullable=False)  # humanity name of property
    storage = Column(TINYINT(unsigned=True), nullable=False)  # 0-nonhistoric; 1-historic; 2-cached

    storage_table = Column(VARCHAR(length=50, unicode=True, charset='utf8'))
    indicator = Column(TINYINT(unsigned=True), nullable=False)
    data_type = Column(ENUM('varchar', 'int', 'date', 'dec', 'text'), nullable=False)  #properties data type
    ref_object = Column(INTEGER(unsigned=True),
                        ForeignKey('a_objects.object_id'))  # id of linked property
    ref_object_label = Column(VARCHAR(length=50, unicode=True, charset='utf8'))  #name of showing property
    unique = Column(TINYINT(unsigned=True),
                    nullable=False)  #unique or not
    description = Column(VARCHAR(length=250)) #property description
    required = Column(TINYINT(unsigned=True), nullable=False)  #requered

    object = relationship('Object', uselist=False, backref=backref('a_object'), foreign_keys=ref_object,
                          primaryjoin="Object.object_id==Properties.ref_object")


class ClassGetter():

    @staticmethod
    def get(classname=None, class_id=None, attrib_id=None, ref=False):
        def get_link_attrib(object_id, prop_id):
            rez = ClassGetter.get(class_id=object_id)

            # получаем аттрибуты класса

        def _getattr(attrib):
            types = {
            'varchar': VARCHAR,
            'int': INTEGER,
            'date': DATETIME,
            'dec': DECIMAL,
            'text': LONGTEXT,
            'raw': VARCHAR
            }
            out_attrib = Column(attrib.name, types[attrib.data_type])
            out_attrib.label(attrib.name+'_')
            if attrib.required:
                out_attrib.nullable = False
            else:
                out_attrib.nullable = True
            if attrib.ref_object:
                '''ref = ClassGetter.get(class_id=attrib.ref_object)
                session.query(getattr(ref, attrib.ref_object_level)).filter()'''
                pass
            #TODO: make returning linked object
            if ref:
                pass
            return out_attrib

        if classname:  #searching by class name
            try:
                result = session.query(Object).filter(Object.name == classname).one()

            except MultipleResultsFound:
                print('Objects with class name="{}" > 1'.format(classname))
                return

        if class_id:  #searching by class id
            result = session.query(Object).filter(Object.object_id == class_id).one()

        attributes = {'__tablename__': result.table}
        for attrib in result.properties_t:
            attributes[attrib.name] = _getattr(attrib)
        attributes[result.id_field] = Column(result.id_field, INTEGER, nullable=False, primary_key=True)
        attributes['__table_args__' ] = {'extend_existing': True}

        return type(result.name, (Base,), attributes)  #returns new class with Propeties of Object instance


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
