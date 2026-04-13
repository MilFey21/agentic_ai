from typing import Any

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class CreateUserRequest(BaseModel):
    username: str
    password: str


class CreateUserResponse(BaseModel):
    id: str
    username: str
    profile_image: str | None = None
    store_api_key: str | None = None
    is_active: bool
    is_superuser: bool
    create_at: str
    updated_at: str
    last_login_at: str | None = None
    optins: dict


class CreateApiKeyRequest(BaseModel):
    name: str


class CreateApiKeyResponse(BaseModel):
    id: str
    api_key: str
    name: str
    created_at: str | None = None
    last_used_at: str | None = None


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    components_list: list[str] | None = None
    flows_list: list[str] | None = None


class CreateProjectResponse(BaseModel):
    name: str
    description: str | None = None
    id: str
    parent_id: str | None = None


# Flow schemas
class CreateFlowRequest(BaseModel):
    name: str
    description: str | None = None
    data: dict[str, Any] | None = None
    folder_id: str | None = None


class CreateFlowResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    folder_id: str | None = None


# Run flow schemas
class RunFlowRequest(BaseModel):
    input_value: str
    output_type: str = 'chat'
    input_type: str = 'chat'
    session_id: str | None = None
    tweaks: dict[str, Any] = {}


class FlowOutputMessage(BaseModel):
    message: str | None = None
    text: str | None = None

    @property
    def content(self) -> str:
        return self.message or self.text or ''


class FlowOutput(BaseModel):
    outputs: list[dict[str, Any]] = []

    def get_message(self) -> str:
        """Extract the message text from the nested output structure."""
        for output in self.outputs:
            results = output.get('results', {})
            message_data = results.get('message', {})
            if isinstance(message_data, dict):
                text = message_data.get('text') or message_data.get('message')
                if text:
                    return text
            # Try to get from outputs array directly
            inner_outputs = output.get('outputs', [])
            for inner in inner_outputs:
                if isinstance(inner, dict):
                    results = inner.get('results', {})
                    message = results.get('message', {})
                    if isinstance(message, dict):
                        text = message.get('text') or message.get('message')
                        if text:
                            return text
        return ''


class RunFlowResponse(BaseModel):
    outputs: list[FlowOutput] = []
    session_id: str | None = None

    def get_message(self) -> str:
        """Get the response message from the flow outputs."""
        for output in self.outputs:
            msg = output.get_message()
            if msg:
                return msg
        return ''


# Chat history schemas
class ChatMessage(BaseModel):
    """A single chat message from LangFlow monitor."""

    id: str | None = None
    flow_id: str | None = None
    session_id: str | None = None
    timestamp: str | None = None
    sender: str | None = None  # "User" or "Machine"
    sender_name: str | None = None
    text: str | None = None

    @property
    def role(self) -> str:
        """Map sender to role (user/assistant)."""
        if self.sender == 'User':
            return 'user'
        return 'assistant'

    @property
    def content(self) -> str:
        """Get message content."""
        return self.text or ''


class UploadFileResponse(BaseModel):
    """Response from LangFlow file upload."""

    flowId: str
    file_path: str


class CreateFlowWithFileResponse(BaseModel):
    """Response from creating a flow with an optional file upload."""

    id: str
    name: str
    description: str | None = None
    folder_id: str | None = None
    uploaded_file_path: str | None = None
    file_component_id: str | None = None
