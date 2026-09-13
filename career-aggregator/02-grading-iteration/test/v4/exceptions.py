class AppError(Exception):
    pass

class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} {resource_id} not found")

class ValidationError(AppError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class GradingError(AppError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class LLMProviderError(AppError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class AuthError(AppError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
