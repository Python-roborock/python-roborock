from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.testing import FakeChannel


async def test_fake_channel_direct():
    """Verify raw subscription, notification, and publish capturing on FakeChannel."""
    channel = FakeChannel()
    messages = []

    def sub(msg):
        messages.append(msg)

    # Trigger message before subscription
    channel.notify_subscribers(RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=b"pre-sub"))
    assert len(messages) == 0

    # Subscribe and notify
    unsub = await channel.subscribe(sub)
    channel.notify_subscribers(RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=b"subbed"))
    assert len(messages) == 1
    assert messages[0].payload == b"subbed"

    # Unsubscribe and notify
    unsub()
    channel.notify_subscribers(RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=b"post-sub"))
    assert len(messages) == 1

    # Test publish logs
    test_msg = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=b"sent")
    await channel.publish(test_msg)
    assert len(channel.published_messages) == 1
    assert channel.published_messages[0] == test_msg
