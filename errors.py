#корневая ошибка
class API_ERROR(Exception):
	pass

#корневая ошибка авторизации
class ACCESS_ERROR(API_ERROR):
	pass

#ошибка инициализации
class INIT_ERROR(ACCESS_ERROR):
	pass

#ошибка авторизации
class AUTH_ERROR(ACCESS_ERROR):
	pass

#ошибка неверно переданных/непереданных параметров
class PARAM_ERROR(API_ERROR):
	pass

#ошибка при обработке запроса
class API_BASE_ERROR(API_ERROR):
	def __init__(self,text=None,code=None,descr=None):
		self.text=text
		self.code=code
		self.descr=descr