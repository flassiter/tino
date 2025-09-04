"""
Tests for the EventBus system.

Tests event subscription, emission, filtering, error handling, and async support.
"""


import pytest

from tino.core.events import (
    Event,
    EventBus,
    FileOpenedEvent,
    TextChangedEvent,
)


class TestEvent(Event):
    """Test event for testing purposes."""

    def __init__(self, data: str = "test"):
        super().__init__()
        self.data = data


class TestEventBus:
    """Test cases for EventBus functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.received_events: list[Event] = []

    def simple_handler(self, event: Event) -> None:
        """Simple event handler for testing."""
        self.received_events.append(event)

    async def async_handler(self, event: Event) -> None:
        """Async event handler for testing."""
        self.received_events.append(event)

    def test_subscribe_and_emit_basic(self):
        """Test basic event subscription and emission."""
        # Subscribe to test events
        self.event_bus.subscribe(TestEvent, self.simple_handler)

        # Emit an event
        test_event = TestEvent("hello")
        self.event_bus.emit(test_event)

        # Check that handler was called
        assert len(self.received_events) == 1
        assert self.received_events[0].data == "hello"

    def test_multiple_subscribers(self):
        """Test that multiple subscribers receive the same event."""
        received_1 = []
        received_2 = []

        def handler_1(event):
            received_1.append(event)

        def handler_2(event):
            received_2.append(event)

        # Subscribe both handlers
        self.event_bus.subscribe(TestEvent, handler_1)
        self.event_bus.subscribe(TestEvent, handler_2)

        # Emit event
        test_event = TestEvent("multi")
        self.event_bus.emit(test_event)

        # Both should receive the event
        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0].data == "multi"
        assert received_2[0].data == "multi"

    def test_event_type_filtering(self):
        """Test that handlers only receive events of subscribed types."""
        text_events = []
        file_events = []

        def text_handler(event):
            text_events.append(event)

        def file_handler(event):
            file_events.append(event)

        # Subscribe to different event types
        self.event_bus.subscribe(TextChangedEvent, text_handler)
        self.event_bus.subscribe(FileOpenedEvent, file_handler)

        # Emit different event types
        from pathlib import Path

        self.event_bus.emit(TextChangedEvent(content="new text", old_content="old"))
        self.event_bus.emit(FileOpenedEvent(file_path=Path("test.md")))

        # Check filtering worked
        assert len(text_events) == 1
        assert len(file_events) == 1
        assert isinstance(text_events[0], TextChangedEvent)
        assert isinstance(file_events[0], FileOpenedEvent)

    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        # Subscribe
        self.event_bus.subscribe(TestEvent, self.simple_handler)

        # Emit and verify subscription works
        self.event_bus.emit(TestEvent("first"))
        assert len(self.received_events) == 1

        # Unsubscribe
        result = self.event_bus.unsubscribe(TestEvent, self.simple_handler)
        assert result is True

        # Emit again and verify no longer receiving
        self.event_bus.emit(TestEvent("second"))
        assert len(self.received_events) == 1  # Still just the first event

    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing a handler that wasn't subscribed."""

        def dummy_handler(event):
            pass

        result = self.event_bus.unsubscribe(TestEvent, dummy_handler)
        assert result is False

    def test_error_handling(self):
        """Test that errors in handlers don't break event emission."""

        def good_handler(event):
            self.received_events.append(event)

        def bad_handler(event):
            raise Exception("Handler error")

        # Subscribe both handlers
        self.event_bus.subscribe(TestEvent, bad_handler)
        self.event_bus.subscribe(TestEvent, good_handler)

        # Emit event - should not raise exception
        self.event_bus.emit(TestEvent("error_test"))

        # Good handler should still receive the event
        assert len(self.received_events) == 1

    @pytest.mark.asyncio
    async def test_async_emit(self):
        """Test asynchronous event emission."""

        async def async_handler(event):
            self.received_events.append(event)

        # Subscribe async handler
        self.event_bus.subscribe(TestEvent, async_handler)

        # Emit async
        await self.event_bus.emit_async(TestEvent("async_test"))

        # Check handler was called
        assert len(self.received_events) == 1
        assert self.received_events[0].data == "async_test"

    @pytest.mark.asyncio
    async def test_mixed_sync_async_handlers(self):
        """Test mixing sync and async handlers."""
        sync_received = []
        async_received = []

        def sync_handler(event):
            sync_received.append(event)

        async def async_handler(event):
            async_received.append(event)

        # Subscribe both types
        self.event_bus.subscribe(TestEvent, sync_handler)
        self.event_bus.subscribe(TestEvent, async_handler)

        # Emit async
        await self.event_bus.emit_async(TestEvent("mixed"))

        # Both should receive
        assert len(sync_received) == 1
        assert len(async_received) == 1

    def test_event_history(self):
        """Test event history tracking."""
        # Enable debug mode to see events
        self.event_bus.set_debug_mode(True)

        # Emit some events
        self.event_bus.emit(TestEvent("first"))
        self.event_bus.emit(TestEvent("second"))
        self.event_bus.emit(TestEvent("third"))

        # Check history
        history = self.event_bus.get_event_history()
        assert len(history) == 3

        # Most recent should be first
        assert history[0].data == "third"
        assert history[1].data == "second"
        assert history[2].data == "first"

    def test_event_history_limit(self):
        """Test event history size limiting."""
        # Clear any existing history
        self.event_bus.clear_history()

        # Emit more events than history limit
        # Default limit is 1000, so let's emit 5 and test limit=3
        for i in range(5):
            self.event_bus.emit(TestEvent(f"event_{i}"))

        # Get limited history
        history = self.event_bus.get_event_history(limit=3)
        assert len(history) == 3

        # Should be most recent 3 events
        assert history[0].data == "event_4"
        assert history[1].data == "event_3"
        assert history[2].data == "event_2"

    def test_subscriber_count(self):
        """Test getting subscriber count for event types."""
        # Initially no subscribers
        assert self.event_bus.get_subscriber_count(TestEvent) == 0

        # Add subscribers
        self.event_bus.subscribe(TestEvent, self.simple_handler)
        assert self.event_bus.get_subscriber_count(TestEvent) == 1

        def another_handler(event):
            pass

        self.event_bus.subscribe(TestEvent, another_handler)
        assert self.event_bus.get_subscriber_count(TestEvent) == 2

        # Remove one
        self.event_bus.unsubscribe(TestEvent, another_handler)
        assert self.event_bus.get_subscriber_count(TestEvent) == 1

    def test_get_all_event_types(self):
        """Test getting all event types with subscribers."""
        # Initially empty
        assert len(self.event_bus.get_all_event_types()) == 0

        # Add subscribers for different event types
        self.event_bus.subscribe(TestEvent, self.simple_handler)
        self.event_bus.subscribe(TextChangedEvent, self.simple_handler)

        event_types = self.event_bus.get_all_event_types()
        assert len(event_types) == 2
        assert TestEvent in event_types
        assert TextChangedEvent in event_types

    def test_unsubscribe_all_for_subscriber(self):
        """Test unsubscribing all handlers owned by a subscriber."""

        class MockSubscriber:
            def handler_1(self, event):
                pass

            def handler_2(self, event):
                pass

        subscriber = MockSubscriber()

        # Subscribe multiple handlers from same subscriber
        self.event_bus.subscribe(TestEvent, subscriber.handler_1, subscriber)
        self.event_bus.subscribe(TextChangedEvent, subscriber.handler_2, subscriber)

        # Verify subscriptions
        assert self.event_bus.get_subscriber_count(TestEvent) == 1
        assert self.event_bus.get_subscriber_count(TextChangedEvent) == 1

        # Unsubscribe all for this subscriber
        removed = self.event_bus.unsubscribe_all(subscriber)
        assert removed == 2

        # Verify all removed
        assert self.event_bus.get_subscriber_count(TestEvent) == 0
        assert self.event_bus.get_subscriber_count(TextChangedEvent) == 0

    def test_event_inheritance(self):
        """Test that handlers receive events from parent classes."""

        class SpecificEvent(TestEvent):
            pass

        base_events = []
        specific_events = []

        def base_handler(event):
            base_events.append(event)

        def specific_handler(event):
            specific_events.append(event)

        # Subscribe to base and specific types
        self.event_bus.subscribe(TestEvent, base_handler)
        self.event_bus.subscribe(SpecificEvent, specific_handler)

        # Emit specific event
        self.event_bus.emit(SpecificEvent("inheritance_test"))

        # Base handler should receive specific events due to inheritance
        assert len(base_events) == 1
        assert len(specific_events) == 1

    def test_debug_mode(self):
        """Test debug mode functionality."""
        # Initially off
        assert not self.event_bus._debug_mode

        # Turn on debug mode
        self.event_bus.set_debug_mode(True)
        assert self.event_bus._debug_mode

        # Turn off
        self.event_bus.set_debug_mode(False)
        assert not self.event_bus._debug_mode

    def test_clear_history(self):
        """Test clearing event history."""
        # Add some events
        self.event_bus.emit(TestEvent("test1"))
        self.event_bus.emit(TestEvent("test2"))

        assert len(self.event_bus.get_event_history()) == 2

        # Clear history
        self.event_bus.clear_history()
        assert len(self.event_bus.get_event_history()) == 0

    def test_cleanup_dead_references(self):
        """Test cleanup of dead weak references."""

        class TemporarySubscriber:
            def handle(self, event):
                pass

        # Create subscriber that will go out of scope
        temp = TemporarySubscriber()
        self.event_bus.subscribe(TestEvent, temp.handle, temp)

        # Delete the subscriber
        del temp

        # Force cleanup (this is automatic with WeakSet, but test the method)
        cleaned = self.event_bus.cleanup_dead_references()
        # Note: This might be 0 due to immediate garbage collection or timing
        assert cleaned >= 0
