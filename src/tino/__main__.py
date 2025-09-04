"""
Main entry point for the tino editor.

This module provides the main() function that serves as the entry point
when tino is run as a module or installed package.
"""

import sys
import logging
from typing import Optional

from .core.logging import configure_logging, get_logger
from .core.events import EventBus
from .core.registry import ComponentRegistry


def setup_basic_logging() -> None:
    """Set up basic logging for the application."""
    configure_logging(
        level="INFO",
        console_output=True,
        file_output=True,
        debug_mode="--debug" in sys.argv
    )


def create_core_infrastructure() -> tuple[EventBus, ComponentRegistry]:
    """Create the core infrastructure components."""
    logger = get_logger(__name__)
    logger.info("Initializing tino editor core infrastructure")
    
    # Create event bus
    event_bus = EventBus()
    event_bus.set_debug_mode("--debug" in sys.argv)
    
    # Create component registry
    registry = ComponentRegistry(event_bus)
    
    logger.info("Core infrastructure initialized successfully")
    return event_bus, registry


def demonstrate_core_functionality(event_bus: EventBus, registry: ComponentRegistry) -> None:
    """Demonstrate that the core infrastructure is working."""
    logger = get_logger(__name__)
    
    # Test event bus
    from .core.events import TextChangedEvent
    
    received_events = []
    
    def test_handler(event):
        received_events.append(event)
        logger.info(f"Received event: {type(event).__name__}")
    
    event_bus.subscribe(TextChangedEvent, test_handler)
    
    # Emit a test event
    test_event = TextChangedEvent(
        content="Hello from tino core infrastructure!",
        old_content="",
        change_type="insert"
    )
    event_bus.emit(test_event)
    
    # Verify event was received
    if received_events:
        logger.info("✓ Event bus is working correctly")
    else:
        logger.error("✗ Event bus failed to deliver events")
    
    # Test component registry
    class TestComponent:
        def __init__(self):
            self.initialized = True
    
    registry.register_component("test_component", TestComponent)
    component = registry.get_component("test_component")
    
    if hasattr(component, 'initialized') and component.initialized:
        logger.info("✓ Component registry is working correctly")
    else:
        logger.error("✗ Component registry failed to create components")
    
    # Show registry stats
    loaded = registry.get_loaded_components()
    registered = registry.get_registered_components()
    
    logger.info(f"Registry status: {len(registered)} registered, {len(loaded)} loaded")


def main() -> int:
    """
    Main entry point for the tino editor.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Check for special flags first
        if "--demo" in sys.argv:
            # Run Phase 0 infrastructure demo
            setup_basic_logging()
            logger = get_logger(__name__)
            
            logger.info("Starting tino Phase 0 demo")
            logger.info(f"Python version: {sys.version}")
            logger.info(f"Command line args: {sys.argv}")
            
            event_bus, registry = create_core_infrastructure()
            
            logger.info("Running core infrastructure demonstration")
            demonstrate_core_functionality(event_bus, registry)
            
            print("🎉 Tino Phase 0 Core Infrastructure Demo")
            print("=" * 45)
            print("✓ Event bus system initialized")
            print("✓ Component registry initialized")
            print("✓ Structured logging configured") 
            print("✓ All core interfaces defined")
            print()
            print("Phase 0 implementation complete!")
            print("Next: Phase 1 - File Manager Component")
            
            logger.info("Shutting down tino editor")
            registry.shutdown_all()
            return 0
        
        elif "--help" in sys.argv or "-h" in sys.argv:
            print("Tino - Terminal Interactive Nano-like Organizer")
            print("A modern TUI markdown editor")
            print()
            print("Usage: python -m tino [options] [file]")
            print()
            print("Options:")
            print("  -h, --help      Show this help message")
            print("  --demo          Run Phase 0 infrastructure demo")
            print("  --debug         Enable debug logging")
            print("  --minimal       Run minimal test app (for development)")
            print("")
            print("By default, runs the full markdown editor with live preview.")
            print()
            print("Current Status: Phase 2 Complete (Editor Component)")
            print("- ✓ Core infrastructure (Phase 0)")
            print("- ✓ File manager (Phase 1)")
            print("- ✓ Text editor (Phase 2)")
            print("- ○ Markdown renderer (Phase 3)")
            print("- ○ Command system (Phase 4)")
            print("- ○ Search functionality (Phase 5)")
            return 0
        
        elif "--minimal" in sys.argv:
            # Launch the minimal test app (for development/testing only)
            from .ui.minimal_app import run_minimal_app
            return run_minimal_app()
        
        else:
            # Launch the main editor application (default behavior)
            from .ui.preview_app import main as main_app
            main_app()
            return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())