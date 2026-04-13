class LangflowError(Exception):
    pass


class LangflowAuthenticationError(LangflowError):
    pass


class LangflowUserCreationError(LangflowError):
    pass


class LangflowProjectCreationError(LangflowError):
    pass


class LangflowFlowCreationError(LangflowError):
    pass


class LangflowFlowRunError(LangflowError):
    pass


class LangflowFileUploadError(LangflowError):
    pass
