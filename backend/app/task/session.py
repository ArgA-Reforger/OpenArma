from celery.backends.database.session import SessionManager as CelerySessionManager


class SessionManager(CelerySessionManager):
    """
    Overrides celery SessionManager
    """

    def __init__(self) -> None:
        super().__init__()

        # Disable automatically creating the task result tables defined internally by celery
        self.prepared = True
