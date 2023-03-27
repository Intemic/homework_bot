class ErrorEnv(ValueError):
    """Некорректные переменные среды."""

    pass


class ErrorResponseData(TypeError):
    """Не допустимый формат."""

    def __str__(self):
        """Пропишем сообщение по умолчанию."""
        return 'Не корректный формат данных'


class ErrorConnection(Exception):
    """Проблемы с доступом к серверу."""

    pass


class ErrorStatus(Exception):
    """Не допустимый статус задания."""

    pass


class ErrorSend(Exception):
    """Ошибка отправки сообщения."""

    pass
