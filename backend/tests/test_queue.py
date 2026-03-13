import pytest

from app.services.queue import MessageQueue


@pytest.fixture
async def queue():
    q = MessageQueue(redis_url="redis://localhost:6379")
    await q.connect()
    # Clean test streams
    await q._redis.delete("test:inbound", "test:outbound")
    yield q
    await q._redis.delete("test:inbound", "test:outbound")
    await q.close()


async def test_enqueue_and_dequeue_inbound(queue):
    msg = {"from": "447700900000", "text": "Hello", "message_id": "wamid.123"}
    await queue.enqueue_inbound(msg, stream="test:inbound")
    messages = await queue.dequeue(stream="test:inbound", count=1)
    assert len(messages) == 1
    assert messages[0]["from"] == "447700900000"
    assert messages[0]["text"] == "Hello"


async def test_enqueue_outbound(queue):
    msg = {"to": "447700900000", "text": "Hi from Sage!", "type": "text"}
    await queue.enqueue_outbound(msg, stream="test:outbound")
    messages = await queue.dequeue(stream="test:outbound", count=1)
    assert len(messages) == 1
    assert messages[0]["to"] == "447700900000"


async def test_dequeue_empty_stream(queue):
    messages = await queue.dequeue(stream="test:inbound", count=1)
    assert len(messages) == 0


async def test_multiple_messages_fifo(queue):
    await queue.enqueue_inbound({"text": "first"}, stream="test:inbound")
    await queue.enqueue_inbound({"text": "second"}, stream="test:inbound")
    messages = await queue.dequeue(stream="test:inbound", count=10)
    assert len(messages) == 2
    assert messages[0]["text"] == "first"
    assert messages[1]["text"] == "second"
