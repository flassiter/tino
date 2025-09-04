"""
Event bus implementation for component communication.

The EventBus provides a centralized way for components to communicate without
direct dependencies. It supports both synchronous and asynchronous event handling.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, Union
from weakref import WeakSet

from .types import Event

logger = logging.getLogger(__name__)

# Type aliases for clarity
SyncHandler = Callable[[Event], None]
AsyncHandler = Callable[[Event], Awaitable[None]]
EventHandler = Union[SyncHandler, AsyncHandler]


class EventBus:
    """
    Centralized event bus for component communication.
    
    Supports both synchronous and asynchronous event handlers with automatic
    cleanup of dead references and error isolation.
    """
    
    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: Dict[Type[Event], List[EventHandler]] = defaultdict(list)
        self._active_subscribers: WeakSet[object] = WeakSet()
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._debug_mode = False
    
    def subscribe(
        self, 
        event_type: Type[Event], 
        handler: EventHandler,
        subscriber: Optional[object] = None
    ) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The handler function (sync or async)
            subscriber: Optional object that owns this subscription (for cleanup)
        """
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler)}")
        
        self._handlers[event_type].append(handler)
        
        if subscriber is not None:
            self._active_subscribers.add(subscriber)
        
        if self._debug_mode:
            logger.debug(
                f"Subscribed {handler} to {event_type.__name__} "
                f"(total handlers: {len(self._handlers[event_type])})"
            )
    
    def unsubscribe(
        self, 
        event_type: Type[Event], 
        handler: EventHandler
    ) -> bool:
        """
        Unsubscribe from events of a specific type.
        
        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler function to remove
            
        Returns:
            True if handler was found and removed, False otherwise
        """
        try:
            self._handlers[event_type].remove(handler)
            if self._debug_mode:
                logger.debug(f"Unsubscribed {handler} from {event_type.__name__}")
            return True
        except ValueError:
            if self._debug_mode:
                logger.warning(f"Handler {handler} not found for {event_type.__name__}")
            return False
    
    def unsubscribe_all(self, subscriber: object) -> int:
        """
        Unsubscribe all handlers owned by a subscriber.
        
        Args:
            subscriber: The object that owns subscriptions to remove
            
        Returns:
            Number of handlers removed
        """
        removed_count = 0
        
        # This is a simple implementation - in practice, you'd need to track
        # which handlers belong to which subscribers more explicitly
        for event_type, handlers in list(self._handlers.items()):
            original_count = len(handlers)
            # Remove handlers that are methods of the subscriber
            self._handlers[event_type] = [
                h for h in handlers 
                if not (hasattr(h, '__self__') and h.__self__ is subscriber)
            ]
            removed_count += original_count - len(self._handlers[event_type])
        
        return removed_count
    
    def emit(self, event: Event) -> None:
        """
        Emit an event to all subscribers synchronously.
        
        Args:
            event: The event to emit
        """
        if self._debug_mode:
            logger.debug(f"Emitting {type(event).__name__}: {event}")
        
        # Add to history
        self._add_to_history(event)
        
        # Get handlers for this event type and its parent classes
        handlers = self._get_handlers_for_event(event)
        
        # Execute all handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # For async handlers, we need to run them in the event loop
                    # If we're not in an event loop, create a task for later
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._safe_async_handler(handler, event))
                    except RuntimeError:
                        # No event loop running, skip async handlers in sync context
                        if self._debug_mode:
                            logger.warning(
                                f"Skipping async handler {handler} - no event loop"
                            )
                else:
                    # Synchronous handler
                    self._safe_sync_handler(handler, event)  # type: ignore[arg-type]
            except Exception as e:
                logger.error(
                    f"Error handling event {type(event).__name__} "
                    f"with handler {handler}: {e}",
                    exc_info=True
                )
    
    async def emit_async(self, event: Event) -> None:
        """
        Emit an event to all subscribers asynchronously.
        
        Args:
            event: The event to emit
        """
        if self._debug_mode:
            logger.debug(f"Emitting async {type(event).__name__}: {event}")
        
        # Add to history
        self._add_to_history(event)
        
        # Get handlers for this event type
        handlers = self._get_handlers_for_event(event)
        
        # Execute all handlers concurrently
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(self._safe_async_handler(handler, event))
            else:
                # Create async wrapper for sync handler
                async def sync_wrapper() -> None:
                    self._safe_sync_handler(handler, event)  # type: ignore[arg-type]
                tasks.append(sync_wrapper())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def _get_handlers_for_event(self, event: Event) -> List[EventHandler]:
        """Get all handlers that should receive this event."""
        handlers = []
        
        # Get handlers for exact type match
        event_type = type(event)
        handlers.extend(self._handlers.get(event_type, []))
        
        # Get handlers for parent classes (inheritance support)
        for base_class in event_type.__mro__[1:]:
            if issubclass(base_class, Event):
                handlers.extend(self._handlers.get(base_class, []))
        
        return handlers
    
    def _safe_sync_handler(self, handler: SyncHandler, event: Event) -> None:
        """Safely execute a synchronous event handler."""
        try:
            handler(event)
        except Exception as e:
            logger.error(
                f"Error in sync handler {handler} for event {type(event).__name__}: {e}",
                exc_info=True
            )
    
    async def _safe_async_handler(self, handler: AsyncHandler, event: Event) -> None:
        """Safely execute an asynchronous event handler."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in async handler {handler} for event {type(event).__name__}: {e}",
                exc_info=True
            )
    
    def _add_to_history(self, event: Event) -> None:
        """Add event to history, maintaining size limit."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_event_history(self, limit: Optional[int] = None) -> List[Event]:
        """
        Get recent event history.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events, most recent first
        """
        history = list(reversed(self._event_history))
        if limit:
            return history[:limit]
        return history
    
    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
    
    def get_subscriber_count(self, event_type: Type[Event]) -> int:
        """Get the number of subscribers for an event type."""
        return len(self._handlers.get(event_type, []))
    
    def get_all_event_types(self) -> List[Type[Event]]:
        """Get all event types that have subscribers."""
        return list(self._handlers.keys())
    
    def set_debug_mode(self, enabled: bool) -> None:
        """Enable or disable debug logging."""
        self._debug_mode = enabled
    
    def cleanup_dead_references(self) -> int:
        """
        Remove any dead weak references.
        
        Returns:
            Number of dead references removed
        """
        # This is automatically handled by WeakSet, but we can force cleanup
        initial_count = len(self._active_subscribers)
        # Force garbage collection of weak references
        self._active_subscribers = WeakSet(list(self._active_subscribers))
        return initial_count - len(self._active_subscribers)