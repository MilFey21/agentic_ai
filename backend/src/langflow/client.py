import json
import logging
from pathlib import Path
from typing import Any

import httpx

from src.langflow.config import langflow_settings
from src.langflow.exceptions import (
    LangflowAuthenticationError,
    LangflowFileUploadError,
    LangflowFlowCreationError,
    LangflowFlowRunError,
    LangflowProjectCreationError,
    LangflowUserCreationError,
)
from src.langflow.schemas import (
    ChatMessage,
    CreateApiKeyResponse,
    CreateFlowRequest,
    CreateFlowResponse,
    CreateFlowWithFileResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    CreateUserRequest,
    CreateUserResponse,
    LoginResponse,
    RunFlowRequest,
    RunFlowResponse,
    UploadFileResponse,
)


logger = logging.getLogger(__name__)


class LangflowClient:
    def __init__(self) -> None:
        self.base_url = langflow_settings.LANGFLOW_API_URL
        self.superuser_username = langflow_settings.LANGFLOW_SUPERUSER
        self.superuser_password = langflow_settings.LANGFLOW_SUPERUSER_PASSWORD
        self._superuser_access_token: str | None = None

    async def _login(self, username: str, password: str) -> str:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}api/v1/login',
                    data={
                        'username': username,
                        'password': password,
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=10.0,
                )
                response.raise_for_status()

                login_data = LoginResponse.model_validate(response.json())
                return login_data.access_token
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow authentication failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowAuthenticationError(
                    f'Failed to authenticate with Langflow: {e.response.status_code}'
                ) from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error')
                raise LangflowAuthenticationError(f'Failed to connect to Langflow: {e}') from e

    async def _get_superuser_access_token(self) -> str:
        if self._superuser_access_token:
            return self._superuser_access_token

        self._superuser_access_token = await self._login(
            self.superuser_username,
            self.superuser_password,
        )
        return self._superuser_access_token

    async def create_user(self, username: str, password: str) -> CreateUserResponse:
        access_token = await self._get_superuser_access_token()

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}api/v1/users/',
                    json=CreateUserRequest(username=username, password=password).model_dump(),
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {access_token}',
                    },
                    timeout=10.0,
                )
                response.raise_for_status()

                return CreateUserResponse.model_validate(response.json())
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow user creation failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowUserCreationError(f'Failed to create user in Langflow: {e.response.status_code}') from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error during user creation')
                raise LangflowUserCreationError(f'Failed to connect to Langflow: {e}') from e

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        *,
        user_access_token: str,
    ) -> CreateProjectResponse:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}api/v1/projects/',
                    json=CreateProjectRequest(name=name, description=description).model_dump(exclude_none=True),
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {user_access_token}',
                    },
                    timeout=10.0,
                )
                response.raise_for_status()

                return CreateProjectResponse.model_validate(response.json())
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow project creation failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowProjectCreationError(
                    f'Failed to create project in Langflow: {e.response.status_code}'
                ) from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error during project creation')
                raise LangflowProjectCreationError(f'Failed to connect to Langflow: {e}') from e

    async def login_user(self, username: str, password: str) -> str:
        return await self._login(username, password)

    async def get_current_user_id(self, access_token: str) -> str:
        """Get the current user's ID from LangFlow."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f'{self.base_url}api/v1/users/whoami',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data['id']
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow whoami failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowAuthenticationError(
                    f'Failed to get current user from Langflow: {e.response.status_code}'
                ) from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error during whoami')
                raise LangflowAuthenticationError(f'Failed to connect to Langflow: {e}') from e

    async def create_api_key(
        self,
        name: str,
        *,
        user_access_token: str,
    ) -> CreateApiKeyResponse:
        """Create an API key for a user."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}api/v1/api_key/',
                    json={'name': name},
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {user_access_token}',
                    },
                    timeout=10.0,
                )
                response.raise_for_status()

                return CreateApiKeyResponse.model_validate(response.json())
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow API key creation failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowAuthenticationError(
                    f'Failed to create API key in Langflow: {e.response.status_code}'
                ) from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error during API key creation')
                raise LangflowAuthenticationError(f'Failed to connect to Langflow: {e}') from e

    async def upload_file(
        self,
        flow_id: str,
        file_path: str | Path,
        *,
        api_key: str,
    ) -> UploadFileResponse:
        """Upload a file to a LangFlow flow.

        Args:
            flow_id: The ID of the flow to upload the file to
            file_path: Path to the file to upload
            api_key: User's API key for authentication

        Returns:
            UploadFileResponse with the uploaded file path
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise LangflowFileUploadError(f'File not found: {file_path}')

        async with httpx.AsyncClient() as client:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.name, f, 'text/csv')}
                    response = await client.post(
                        f'{self.base_url}api/v1/files/upload/{flow_id}',
                        files=files,
                        headers={
                            'x-api-key': api_key,
                        },
                        timeout=60.0,
                    )
                    response.raise_for_status()

                    return UploadFileResponse.model_validate(response.json())
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow file upload failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowFileUploadError(f'Failed to upload file to Langflow: {e.response.status_code}') from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error during file upload')
                raise LangflowFileUploadError(f'Failed to connect to Langflow: {e}') from e

    async def create_flow_from_template(
        self,
        template_path: str | Path,
        flow_name: str,
        folder_id: str,
        *,
        user_api_key: str,
        file_component_id: str | None = None,
        file_to_upload: str | Path | None = None,
    ) -> CreateFlowWithFileResponse:
        """Create a new flow in LangFlow from a JSON template file.

        Uses user's API key for authentication (flow will be owned by the user).

        Args:
            template_path: Path to the JSON template file
            flow_name: Name for the new flow
            folder_id: User's folder ID in LangFlow
            user_api_key: User's API key for authentication
            file_component_id: Optional ID of the File component to configure
            file_to_upload: Optional path to a file to upload and attach to the flow

        Returns:
            CreateFlowWithFileResponse with the created flow's ID and optional file info
        """
        template_path = Path(template_path)

        if not template_path.exists():
            raise LangflowFlowCreationError(f'Template file not found: {template_path}')

        with open(template_path, encoding='utf-8') as f:
            template_data = json.load(f)

        # Override the flow name
        template_data['name'] = flow_name

        uploaded_file_path: str | None = None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}api/v1/flows/',
                    json=CreateFlowRequest(
                        name=flow_name,
                        description=template_data.get('description', ''),
                        data=template_data.get('data', {}),
                        folder_id=folder_id,
                    ).model_dump(exclude_none=True),
                    headers={
                        'Content-Type': 'application/json',
                        'x-api-key': user_api_key,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                flow_data = response.json()

                # Upload file if provided
                if file_to_upload and file_component_id:
                    upload_response = await self.upload_file(
                        flow_id=flow_data['id'],
                        file_path=file_to_upload,
                        api_key=user_api_key,
                    )
                    uploaded_file_path = upload_response.file_path
                    logger.info(
                        'Uploaded file to flow %s: %s',
                        flow_data['id'],
                        uploaded_file_path,
                    )

                return CreateFlowWithFileResponse(
                    id=flow_data['id'],
                    name=flow_data.get('name', flow_name),
                    description=flow_data.get('description'),
                    folder_id=flow_data.get('folder_id'),
                    uploaded_file_path=uploaded_file_path,
                    file_component_id=file_component_id,
                )
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow flow creation failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowFlowCreationError(f'Failed to create flow in Langflow: {e.response.status_code}') from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error during flow creation')
                raise LangflowFlowCreationError(f'Failed to connect to Langflow: {e}') from e

    async def run_flow(
        self,
        flow_id: str,
        input_value: str,
        session_id: str | None = None,
        *,
        api_key: str,
        tweaks: dict[str, Any] | None = None,
    ) -> RunFlowResponse:
        """Run a flow and get the response using API key authentication."""
        async with httpx.AsyncClient() as client:
            try:
                request_data = RunFlowRequest(
                    input_value=input_value,
                    output_type='chat',
                    input_type='chat',
                    session_id=session_id,
                    tweaks=tweaks or {},
                )

                response = await client.post(
                    f'{self.base_url}api/v1/run/{flow_id}',
                    json=request_data.model_dump(exclude_none=True),
                    headers={
                        'Content-Type': 'application/json',
                        'x-api-key': api_key,
                    },
                    timeout=120.0,  # LLM calls can be slow
                )
                response.raise_for_status()

                return RunFlowResponse.model_validate(response.json())
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow flow run failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                raise LangflowFlowRunError(f'Failed to run flow in Langflow: {e.response.status_code}') from e
            except httpx.RequestError as e:
                logger.exception('Langflow connection error during flow run')
                raise LangflowFlowRunError(f'Failed to connect to Langflow: {e}') from e

    async def delete_flow(
        self,
        flow_id: str,
        *,
        user_access_token: str,
    ) -> None:
        """Delete a flow from LangFlow."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f'{self.base_url}api/v1/flows/{flow_id}',
                    headers={
                        'Authorization': f'Bearer {user_access_token}',
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.exception(
                    'Langflow flow deletion failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                # Don't raise error on deletion failure - it's not critical
            except httpx.RequestError:
                logger.exception('Langflow connection error during flow deletion')

    async def get_chat_history(
        self,
        session_id: str,
        *,
        api_key: str,
        flow_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessage]:
        """Get chat history for a session from LangFlow monitor API.

        Args:
            session_id: The LangFlow session ID
            api_key: API key for authentication
            flow_id: Optional flow ID to filter by
            limit: Maximum number of messages to retrieve

        Returns:
            List of ChatMessage objects sorted by timestamp (newest first)
        """
        async with httpx.AsyncClient() as client:
            try:
                params: dict[str, str] = {
                    'session_id': session_id,
                    'order_by': 'timestamp',
                }
                if flow_id:
                    params['flow_id'] = flow_id

                response = await client.get(
                    f'{self.base_url}api/v1/monitor/messages',
                    params=params,
                    headers={
                        'accept': 'application/json',
                        'x-api-key': api_key,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                data = response.json()
                messages = []

                # Parse messages from response
                if isinstance(data, list):
                    for msg_data in data[-limit:]:  # Get last N messages
                        messages.append(ChatMessage.model_validate(msg_data))
                elif isinstance(data, dict) and 'messages' in data:
                    for msg_data in data['messages'][-limit:]:
                        messages.append(ChatMessage.model_validate(msg_data))

                # Sort by timestamp descending (newest first)
                messages.sort(key=lambda m: m.timestamp or '', reverse=True)

                return messages

            except httpx.HTTPStatusError as e:
                logger.warning(
                    'Langflow get chat history failed: %s - %s',
                    e.response.status_code,
                    e.response.text,
                )
                return []
            except httpx.RequestError as e:
                logger.warning('Langflow connection error during get chat history: %s', e)
                return []

    def format_chat_history_as_dialog(
        self,
        messages: list[ChatMessage],
        max_length: int = 1000,
    ) -> str:
        """Format chat messages as a concatenated dialog string.

        Args:
            messages: List of ChatMessage objects (should be sorted newest first)
            max_length: Maximum length of the resulting string

        Returns:
            Formatted dialog string, truncated to max_length
        """
        if not messages:
            return ''

        # Reverse to get chronological order (oldest first)
        messages_chronological = list(reversed(messages))

        dialog_parts = []
        for msg in messages_chronological:
            role_label = 'Студент' if msg.role == 'user' else 'Бот'
            content = msg.content.strip()
            if content:
                dialog_parts.append(f'{role_label}: {content}')

        dialog = '\n'.join(dialog_parts)

        # Truncate to max_length, keeping the end (most recent messages)
        if len(dialog) > max_length:
            dialog = '...' + dialog[-(max_length - 3) :]

        return dialog
