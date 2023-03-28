class ErrorEnv(ValueError):
    """Некорректные переменные среды."""

    pass


class ErrorResponseData(TypeError):
    """Не допустимый формат."""

    pass


class ErrorConnection(Exception):
    """Проблемы с доступом к серверу."""

    pass


class ErrorStatus(Exception):
    """Не допустимый статус задания."""

    pass


class ErrorSend(Exception):
    """Ошибка отправки сообщения."""

    pass
