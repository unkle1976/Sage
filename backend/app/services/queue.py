import json

import redis.asyncio as redis


class MessageQueue:
    """Async message queue using Redis Streams for WhatsApp inbound/outbound processing."""

    INBOUND_STREAM = "sage:inbound"
    OUTBOUND_STREAM = "sage:outbound"

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None

    async def connect(self):
        self._redis = redis.from_url(self._redis_url, decode_responses=True)

    async def enqueue_inbound(self, message: dict, stream: str | None = None):
        """Add an inbound WhatsApp message to the queue."""
        await self._redis.xadd(stream or self.INBOUND_STREAM, {"data": json.dumps(message)})

    async def enqueue_outbound(self, message: dict, stream: str | None = None):
        """Add an outbound message to the queue for sending via WhatsApp."""
        await self._redis.xadd(stream or self.OUTBOUND_STREAM, {"data": json.dumps(message)})

    async def dequeue(self, stream: str, count: int = 10, block: int | None = None) -> list[dict]:
        """Read and remove messages from a stream. Returns list of parsed message dicts.

        Args:
            stream: Redis stream key to read from.
            count: Maximum number of messages to return.
            block: Milliseconds to block waiting for messages. None = don't block.
        """
        kwargs = {"count": count}
        if block is not None:
            kwargs["block"] = block
        entries = await self._redis.xread({stream: "0-0"}, **kwargs)
        results = []
        for _stream_name, messages in entries:
            for msg_id, fields in messages:
                data = json.loads(fields["data"])
                data["_stream_id"] = msg_id
                results.append(data)
                await self._redis.xdel(stream, msg_id)
        return results

    async def close(self):
        if self._redis:
            await self._redis.aclose()
