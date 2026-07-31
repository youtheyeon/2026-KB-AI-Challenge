# 서비스 계층의 오류를 일관된 HTTP 상태와 공개 메시지로 전달하는 예외


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
