class QueueProviderException(Exception):
    """
    Generic exception for QueueProvider errors.
    """

    pass


class QueueProviderUnableToConnectException(QueueProviderException):
    """
    Raised when a connection to RabbitMQ cannot be established.
    """

    pass


class QueueProviderNotConnectedException(QueueProviderException):
    """
    Raised when no connection is established.
    """

    pass
