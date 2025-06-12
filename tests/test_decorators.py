import types
from unittest.mock import AsyncMock

import pytest
from telegram.constants import ChatAction

from bot.utils.decorators import typing_action


@pytest.mark.asyncio
async def test_typing_action_triggers_send_action():
    mock_chat = types.SimpleNamespace(send_action=AsyncMock())
    update = types.SimpleNamespace(effective_chat=mock_chat)
    context = object()

    called = False

    @typing_action
    async def sample(update, context):
        nonlocal called
        called = True
        return "result"

    result = await sample(update, context)

    assert called is True
    mock_chat.send_action.assert_awaited_once_with(ChatAction.TYPING)
    assert result == "result"
