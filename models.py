from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy.dialects.mysql import MEDIUMINT, DECIMAL, INTEGER, VARCHAR, DATETIME, TINYINT, ENUM, LONGTEXT, BIGINT
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import relationship, backref
from const import db_access
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
import logging
from errors import DatabaseError
import warnings

Base = declarative_base()


def get_engine(db_name):
    db_driver = 'pymysql'
    return create_engine('mysql+{0}://'
                         '{user}:{passwd}'
                         '@{host}:{port}/{1}?charset=cp1251'.format(db_driver, db_name, **db_access), encoding='cp1251')


def get_session(db_name):
    engine = get_engine(db_name)
    session = sessionmaker(bind=engine)
    return session()


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

    '''def _get_val_storage(st):
        st = st
        if st == 0:
            return 'historic'
        elif st == 1:
            return "nonhistoric"
        elif st == 2:
            return "cached"'''

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
    ref_object_label_property = Column(INTEGER)  # name of showing property
    unique = Column(TINYINT(unsigned=True),
                    nullable=False)  # unique or not
    description = Column(VARCHAR(length=250))  # property description
    required = Column(TINYINT(unsigned=True), nullable=False)  # required
    values_to_select = Column(VARCHAR(length=250))

    object = relationship('Object', uselist=False, backref=backref('a_object'), foreign_keys=ref_object,
                          primaryjoin="Object.object_id==Properties.ref_object")


class BaseBill(object):

    @staticmethod
    def __commit(session):
        """Method for commit. Required session instance"""
        logging.log(msg='Start Commit')
        session.commit()
        logging.log(msg='Finish')

    @classmethod
    def _check_attributes(cls, attributes):
        """Method for check requirement attributes of query"""
        ch = False
        for attr in attributes:
            if str(attr) not in cls.__attr_list__:
                logging.error(msg='{} is not a property of {}'.format(attr, cls.classname))
                ch = True
        if ch:
            raise AttributeError('Has some unresolved attributes')

    @classmethod
    def select(cls, session, where, begin=None, cnt=1, all_references=False):
        """Method for SELECT-query
        Requires session instance, WHERE statement which must be dict.
        Also can get LIMIT statement like arguments `begin` and `end`."""

        if not isinstance(where, dict):
            raise AttributeError('WHERE statement must be dictionary')

        cls._check_attributes(where.keys())
        result_set = session.query(cls).filter_by(**where)
        if cnt == 1:
            result_set = result_set[0]
        else:
            result_set = result_set[begin: begin + cnt]
        if not all_references:
            return result_set
        else:
            #  TODO make `values-to-select`
                return cls.all_references(result_set)

    @classmethod
    def update(cls, session, where, update, commit=True):
        """Method for UPDATE-query.
        Requires session instance, WHERE statement and SET (`update`) statement. All statements must be dictionaries"""

        if not isinstance(where, dict):
            raise AttributeError('WHERE statement must be dictionary')
        if not isinstance(update, dict):
            raise AttributeError('SET statement must be dictionary')

        cls._check_attributes(where.keys() + update.keys())
        query = cls.select(session, where)

        for element in query:  # for every result-element
            for key in update:  # for every key in update values dict
                setattr(element, key, update[key])  # update
            ready = query.index(element)
            if ready % 100 == 0 and ready != 0:
                logging.log(msg='Ready {} of {}'.format(ready+1, len(query)))  # for big update

        if commit:
            cls.__commit(session)

    @classmethod
    def delete(cls, session, where, commit=True):
        """Method for DELETE-query.
        Requires session instance and WHERE statement"""

        if not isinstance(where, dict):
            raise AttributeError('WHERE statement must be dictionary')

        cls._check_attributes(where.keys())
        query = cls.select(session, where)
        for element in query:
            session.delete(element)

        if commit:
            cls.__commit(session)

    @classmethod
    def insert(cls, session, attributes, commit=True):
        """Method for INSERT-query"""
        cls._check_attributes(attributes)
        for attr_name in attributes:
            setattr(cls, attr_name, attributes[attr_name])

        if commit:
            cls.__commit(session)

    @classmethod
    def _all_references(cls, result_instance, session):
        """Method, which returns object with new attributes - referenced objects of instance class."""
        for attribute in result_instance.__referrer_list__:
            bill_class = get_class(class_id=result_instance.__referrer_list__[attribute])
            try:
                reference = bill_class.select(session, {'i_id': getattr(result_instance, attribute)})
            except IndexError:
                pass
                continue
            ref_attr_name = "ref_" + attribute
            setattr(result_instance, ref_attr_name, reference)
            result_instance.__attr_list__ += (ref_attr_name,)
        for attribute in cls.__attr_list__:
            try:
                sel_vals = getattr(cls, attribute).values_to_select
            except AttributeError:
                continue
            if sel_vals:
                setattr(result_instance,
                        'value_' + attribute,
                       sel_vals[
                            str(getattr(result_instance, attribute))
                        ])
        return result_instance


def get_class(class_name=None, class_id=None):

    session = get_session('ekomobile')

    def _getattr(attribute):
        types = {
            'varchar': VARCHAR(length=255),
            'int': BIGINT,
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
            out_attrib.referrer = attribute.ref_object
            out_attrib.referrer_name = attribute.ref_object_label
        else:
            out_attrib.referrer = None
            out_attrib.referrer_name = None
        if attribute.values_to_select:
            out_attrib.values_to_select = dict([
                el.split(':') for el in attribute.values_to_select.split('|')
            ])
        else:
            out_attrib.values_to_select = None
        return out_attrib

    if class_name:  # search by class name
        try:
            result = session.query(Object).filter(Object.name == class_name).one()
        except MultipleResultsFound:
            raise DatabaseError('Objects with class name="{}" > 1'.format(class_name))
        except NoResultFound:
            raise DatabaseError('No objects with class name="{}"'.format(class_name))

    elif class_id:  # search by class id
        result = session.query(Object).filter(Object.object_id == class_id).one()
    else:
        raise AttributeError('Must have className or classId')

    attributes = {
        '__tablename__': result.table,
        '__attr_list__': ['user_id',
                          'date_in',
                          'date_ch',
                          'i_id'],
        "__referrer_list__": dict(),
        'i_id': Column(result.id_field, INTEGER, nullable=False, primary_key=True),
        'date_in': Column('date_in', DATETIME, nullable=False),
        'date_ch': Column('date_ch', DATETIME, nullable=False),
        '__table_args__': {
            'extend_existing': True
        },
        'user_id': Column('user_id', INTEGER, nullable=False),
        'classname': result.name,
        'object_id': result.object_id
    }

    for attr in attributes['__attr_list__']:
        attributes[attr].values_to_select = None
        attributes[attr].referrer = None

    for attrib in result.properties_t:
        attributes[attrib.name] = _getattr(attrib)
        attributes['__attr_list__'] += (attrib.name,)
        if attributes[attrib.name].referrer:
            attributes['__referrer_list__'][attrib.name] = attributes[attrib.name].referrer


    return type(result.name, (Base, BaseBill), attributes)  # returns new class with Properties of Object instance


def show_all_values(obj, select, session, where=None):
    warnings.warn('deprecated', DeprecationWarning)
    # TODO Refactoring, optimization
    # TODO Realize it like method of `bill_classes` class
    if not isinstance(where, dict):
        raise DatabaseError('WHERE statement must be dict, expected {}'.format(type(where)))
    if not isinstance(select, tuple) and not isinstance(select, list):
        raise DatabaseError('SELECT statement must be list or tuple, expected {}'.format(type(select)))

    select_objects = dict()
    for column in select:
        select_objects[column] = get_class(class_id=getattr(obj, column).referrer)

    result_list = session.query(obj).filter_by(**where).all()

    for result in result_list:
        for column in select_objects:
            if getattr(result, column):
                ref = session.query(select_objects[column]).filter_by(i_id=getattr(result, column)).one()
                setattr(result,
                        column + '_refer',
                        ref
                        )
                setattr(result,
                        column + '_ref_label',
                        getattr(
                            ref,
                            getattr(obj, column).referrer_name
                               )
                        )
    return result_list