from google.auth.transport.requests import Request

class Credentials:
    token: str

    @classmethod
    def from_authorized_user_file(
        cls, filename: str, scopes: list[str] | None = None
    ) -> "Credentials": ...
    def refresh(self, request: Request) -> None: ...
