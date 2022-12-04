class OAuth2WebServerFlow:
    def __init__(
        self,
        client_id: str,
        client_secret: str | None = None,
        scope: str | None = None,
        redirect_uri: str | None = None,
    ): ...

class OAuth2Credentials:
    access_token: str | None
