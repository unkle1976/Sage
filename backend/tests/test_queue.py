import uuid

import pytest

from app.services.queue import MessageQueue


@pytest.fixture
async def queue():
    q = MessageQueue(redis_url="redis://localhost:6379")
    await q.connect()
    yield q
    await q.close()


def _stream(name: str) -> str:
    """Generate a unique stream name per test invocation to avoid cross-test leaks."""
    return f"test:{name}:{uuid.uuid4().hex[:8]}"


async def test_enqueue_and_dequeue_inbound(queue):
    stream = _stream("inbound")
    msg = {"from": "447700900000", "text": "Hello", "message_id": "wamid.123"}
    await queue.enqueue_inbound(msg, stream=stream)
    messages = await queue.dequeue(stream=stream, count=1)
    assert len(messages) == 1
    assert messages[0]["from"] == "447700900000"
    assert messages[0]["text"] == "Hello"
    await queue._redis.delete(stream)


async def test_enqueue_outbound(queue):
    stream = _stream("outbound")
    msg = {"to": "447700900000", "text": "Hi from Sage!", "type": "text"}
    await queue.enqueue_outbound(msg, stream=stream)
    messages = await queue.dequeue(stream=stream, count=1)
    assert len(messages) == 1
    assert messages[0]["to"] == "447700900000"
    await queue._redis.delete(stream)


async def test_dequeue_empty_stream(queue):
    stream = _stream("empty")
    messages = await queue.dequeue(stream=stream, count=1)
    assert len(messages) == 0


async def test_multiple_messages_fifo(queue):
    stream = _stream("fifo")
    await queue.enqueue_inbound({"text": "first"}, stream=stream)
    await queue.enqueue_inbound({"text": "second"}, stream=stream)
    messages = await queue.dequeue(stream=stream, count=10)
    assert len(messages) == 2
    assert messages[0]["text"] == "first"
    assert messages[1]["text"] == "second"
    await queue._redis.delete(stream)
