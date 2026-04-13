from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, resource: str = 'Resource') -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'{resource} not found',
        )


class NotFoundException(HTTPException):
    def __init__(self, detail: str = 'Resource not found') -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class BadRequestError(HTTPException):
    def __init__(self, detail: str = 'Bad request') -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class ConflictException(HTTPException):
    def __init__(self, detail: str = 'Resource already exists') -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
