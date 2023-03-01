"""
Exception hierarchy for Citehound

:author: Athanasios Anastasiou
:date: Mar 2023
"""


class InsightException(Exception):
    """
    Base class for all exceptions that are specific to the Insight System.
    """
    def __init__(self,msg):
        super().__init__(self,msg)


class DataImportError(InsightException):
    """
    Raised in the event of exceptions specific to the data importing process.
    """
    pass


class ManagerError(InsightException):
    """
    Raised in the event of an exception at the point of interaction of the InsightManager with any external entities.
    """
    pass
