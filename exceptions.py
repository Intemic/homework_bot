class ErrorEnv(ValueError):
    pass 

class ErrorResponseData(TypeError):
    def __str__(self):
        return 'Не корректный формат данных'

class ErrorConnection(Exception):
    pass

class ErrorStatus(Exception):
    pass

class ErrorSend(Exception):
    pass