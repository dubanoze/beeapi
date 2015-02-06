from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy.dialects.mysql import MEDIUMINT, DECIMAL, BIGINT, INTEGER, VARCHAR, DATETIME, TINYINT, ENUM, LONGTEXT
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.exc import InvalidRequestError


engine = create_engine('mysql+mysqlconnector://'
                       'a.spicin:7JQMMADmz2t3hdSF'
                       '@192.168.5.77:3306/ekomobile')
Base = declarative_base()
_Base = declarative_base()


class object(Base):
    __tablename__ = 'a_objects'
    object_id = Column(INTEGER(unsigned=True), primary_key=True, nullable=False)
    name = Column(VARCHAR(length=50), nullable=False, unique=True)  # системное имя класса
    ru_name = Column(VARCHAR(length=50), nullable=False)  # человеческое название класса
    description = Column(VARCHAR(length=250))
    table = Column(VARCHAR(length=50))  # таблица, в которой хранятся экземпляры класса
    id_field = Column(VARCHAR(length=50))  # название поля-идентификатора

    properties_t = relationship('properties', backref='a_properties',
                                primaryjoin="object.object_id==properties.object_id")


class properties(Base):
    __tablename__ = 'a_properties'


    def _get_val_select(sel):
        sl = {}
        sel = str(sel).split('|')
        for el in sel:
            pck, v = yield el.split(':')
            sl[int(k)] = v
        return sl

    def _get_val_storage(st):
        st = st
        if st == 0:
            return 'Неисторический'
        elif st == 1:
            return "Исторический"
        elif st == 2:
            return "Кэшированный"


    property_id = Column(MEDIUMINT(unsigned=True), primary_key=True, nullable=False)

    object_id = Column(INTEGER(unsigned=True), ForeignKey('a_objects.object_id'),
                       nullable=False)  # ID класса, которому принадлежит свойство

    name = Column(VARCHAR(length=50), nullable=False)  # системное именование свойства
    ru_name = Column(VARCHAR(length=64), nullable=False)  # Отображаемое название свойства
    storage = Column(TINYINT(unsigned=True), nullable=False)  # 0-Неисторический; 1-Исторический; 2-кешированный

    storage_table = Column(VARCHAR(length=50, unicode=True, charset='utf8'))
    indicator = Column(TINYINT(unsigned=True), nullable=False)
    data_type = Column(ENUM('varchar', 'int', 'date', 'dec', 'text'), nullable=False)  # Тип данных свойства
    ref_object = Column(INTEGER(unsigned=True),
                        ForeignKey('a_objects.object_id'))  # ID класса, на экземпляр которого ссылается свойство
    # ref_object=Column(INTEGER(unsigned=True)) #ID класса, на экземпляр которого ссылается свойство
    ref_object_label = Column(VARCHAR(length=50, unicode=True, charset='utf8'))  #названеи отображаемого свойства
    ref_object_label_property = Column(INTEGER(unsigned=True))  #ID свойства класса, значение которого отображать
    unique = Column(TINYINT(unsigned=True),
                    nullable=False)  #Признак того, что значение свойства должно быть уникальным для каждого экземпляра класса.
    input = Column(ENUM('text', 'number',
                        'date', 'select',
                        'autocomplete',
                        'textarea', 'password'))
    context_search = Column(TINYINT,
                            nullable=False)  #Учавствует в контекстном поиске по ссылке из другого класса. Значение >0 носит признак сортировки.
    sort = Column(TINYINT(unsigned=True), nullable=False)
    ungapped = Column(TINYINT(unsigned=True), nullable=False)
    description = Column(VARCHAR(length=250))
    values_to_select = Column(VARCHAR(
        length=128))  #Список возможных вариантов значений для выбора в интерфейсе на основе <select>. Формат: Число:Имя
    _values_to_select = _get_val_select(values_to_select)
    group_by = Column(VARCHAR(length=16))  #Идентификатор группировки свойств в пределах класса.
    required = Column(TINYINT(unsigned=True), nullable=False)  #Обязательно к указанию значения
    key = Column(TINYINT(unsigned=True),
                 nullable=False)  #Признак того, что свойство является ключевым в классе типа "связь"

    object = relationship('object', uselist=False, backref=backref('a_object'), foreign_keys=ref_object,
                          primaryjoin="object.object_id==properties.ref_object")


class class_getter():
    def get(self, classname=None, class_id=None, attrib_id=None):
        def get_link_attrib(object_id, prop_id):
            rez = class_getter().get(class_id=object_id)

            # получаем аттрибуты класса

        def getattr(attrib):
            types = {
            'varchar': VARCHAR,
            'int': INTEGER,
            'date': DATETIME,
            'dec': DECIMAL,
            'text': LONGTEXT,
            'raw': VARCHAR
            }
            out_attrib = Column(attrib.name, types[attrib.data_type])
            if attrib.required:
                out_attrib.nullable = False
            else:
                out_attrib.nullable = True
            if attrib.ref_object:
                pass
            #get_link_attrib(attrib.ref_object,attrib.ref_object_label_property)
            return out_attrib

        #ищем по имени класса
        if classname:
            try:
                rezult = session.query(object).filter(object.name == classname).one()
            except MultipleResultsFound:
                print('Objects with classname="{}">1'.format(classname))
                return
        #ищем по id класса
        if class_id:
            rezult = session.query(object).filter(object.object_id == class_id).one()
        #для ситуаций, когда нужно получить только одно свойство
        if attrib_id:
            pass
            '''for el in rezult.properties_t:
                if el.propery_id==attrib_id:
                    rezult.properties_t=[el]'''
        attributes = {'__tablename__': rezult.table}
        for attrib in rezult.properties_t:
            attributes[attrib.name] = getattr(attrib)
        attributes[rezult.id_field] = Column(rezult.id_field, INTEGER, nullable=False, primary_key=True)

        try:
            return type(rezult.name, (Base,), attributes)  #возвращаем новый динамически созданный класс
        except InvalidRequestError:
            return type(rezult.name, (_Base,), attributes)  #возвращаем новый динамически созданный класс


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

if _Base:
    _Base.metadata.create_all(engine)