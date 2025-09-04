"""
Tests for the ComponentRegistry system.

Tests component registration, dependency injection, lifecycle management,
and initialization order resolution.
"""


import pytest

from tino.core.events import EventBus
from tino.core.registry import (
    CircularDependencyError,
    ComponentCreationError,
    ComponentNotFoundError,
    ComponentRegistry,
)


class MockComponentA:
    """Mock component for testing."""

    def __init__(self):
        self.initialized = True

    def cleanup(self):
        self.cleaned_up = True


class MockComponentB:
    """Mock component that depends on A."""

    def __init__(self, component_a: MockComponentA):
        self.component_a = component_a
        self.initialized = True


class MockComponentC:
    """Mock component that depends on B."""

    def __init__(self, component_b: MockComponentB):
        self.component_b = component_b
        self.initialized = True


class MockComponentWithEventBus:
    """Mock component that needs event bus."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.initialized = True


def mock_factory_a():
    """Factory function for MockComponentA."""
    return MockComponentA()


def mock_factory_b(component_a: MockComponentA):
    """Factory function for MockComponentB."""
    return MockComponentB(component_a)


class TestComponentRegistry:
    """Test cases for ComponentRegistry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.registry = ComponentRegistry(self.event_bus)

    def test_register_component_basic(self):
        """Test basic component registration."""
        self.registry.register_component("test_a", MockComponentA)

        # Check registration
        registered = self.registry.get_registered_components()
        assert "test_a" in registered

        # Get component info
        info = self.registry.get_component_info("test_a")
        assert info["name"] == "test_a"
        assert info["type"] == "MockComponentA"
        assert info["singleton"] is True
        assert info["loaded"] is False

    def test_register_component_with_factory(self):
        """Test component registration with custom factory."""
        self.registry.register_component(
            "test_a", MockComponentA, factory=mock_factory_a
        )

        info = self.registry.get_component_info("test_a")
        assert info["factory"] == "mock_factory_a"

    def test_register_component_with_dependencies(self):
        """Test component registration with dependencies."""
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        info_b = self.registry.get_component_info("test_b")
        assert "test_a" in info_b["dependencies"]

        info_a = self.registry.get_component_info("test_a")
        assert "test_b" in info_a["dependents"]

    def test_get_component_basic(self):
        """Test getting a component instance."""
        self.registry.register_component("test_a", MockComponentA)

        # Get component
        component = self.registry.get_component("test_a")
        assert isinstance(component, MockComponentA)
        assert component.initialized is True

        # Should be singleton by default
        component2 = self.registry.get_component("test_a")
        assert component is component2

    def test_get_component_with_type_checking(self):
        """Test getting component with type checking."""
        self.registry.register_component("test_a", MockComponentA)

        # Correct type
        component = self.registry.get_component("test_a", MockComponentA)
        assert isinstance(component, MockComponentA)

        # Wrong type should raise TypeError
        with pytest.raises(TypeError):
            self.registry.get_component("test_a", MockComponentB)

    def test_get_component_not_registered(self):
        """Test getting component that's not registered."""
        with pytest.raises(ComponentNotFoundError):
            self.registry.get_component("nonexistent")

    def test_dependency_injection(self):
        """Test automatic dependency injection."""
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        # Get component B - should automatically inject A
        component_b = self.registry.get_component("test_b")
        assert isinstance(component_b, MockComponentB)
        assert isinstance(component_b.component_a, MockComponentA)

    def test_event_bus_injection(self):
        """Test automatic event bus injection."""
        self.registry.register_component("test_bus", MockComponentWithEventBus)

        component = self.registry.get_component("test_bus")
        assert component.event_bus is self.event_bus

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        # Create circular dependency: A -> B -> A
        self.registry.register_component(
            "test_a", MockComponentA, dependencies=["test_b"]
        )
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        with pytest.raises(CircularDependencyError):
            self.registry.get_component("test_a")

    def test_initialization_order_resolution(self):
        """Test dependency-based initialization order."""
        # Register in random order
        self.registry.register_component(
            "test_c", MockComponentC, dependencies=["test_b"]
        )
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        # Resolve order
        order = self.registry.resolve_initialization_order()

        # Should be A, B, C
        a_index = order.index("test_a")
        b_index = order.index("test_b")
        c_index = order.index("test_c")

        assert a_index < b_index < c_index

    def test_initialize_all(self):
        """Test initializing all components in order."""
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        # Initialize all
        initialized = self.registry.initialize_all()

        assert "test_a" in initialized
        assert "test_b" in initialized

        # Both should be loaded
        assert self.registry.is_loaded("test_a")
        assert self.registry.is_loaded("test_b")

    def test_unload_component(self):
        """Test unloading a component."""
        self.registry.register_component("test_a", MockComponentA)

        # Load component
        component = self.registry.get_component("test_a")
        assert self.registry.is_loaded("test_a")

        # Unload it
        result = self.registry.unload_component("test_a")
        assert result is True
        assert not self.registry.is_loaded("test_a")

        # Should call cleanup if available
        assert hasattr(component, "cleaned_up")

    def test_unload_with_dependents(self):
        """Test unloading component with dependents."""
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        # Load both
        self.registry.get_component("test_a")
        self.registry.get_component("test_b")

        # Unload A - should also unload B
        self.registry.unload_component("test_a")

        assert not self.registry.is_loaded("test_a")
        assert not self.registry.is_loaded("test_b")

    def test_shutdown_all(self):
        """Test shutting down all components."""
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        # Initialize all
        self.registry.initialize_all()

        # Shutdown all
        shutdown = self.registry.shutdown_all()

        assert "test_a" in shutdown
        assert "test_b" in shutdown
        assert not self.registry.is_loaded("test_a")
        assert not self.registry.is_loaded("test_b")

    def test_register_instance(self):
        """Test registering pre-created instances."""
        instance = MockComponentA()
        self.registry.register_instance("test_instance", instance)

        # Should be immediately available
        assert self.registry.is_loaded("test_instance")

        # Getting it should return the same instance
        retrieved = self.registry.get_component("test_instance")
        assert retrieved is instance

    def test_non_singleton_components(self):
        """Test non-singleton component behavior."""
        self.registry.register_component("test_a", MockComponentA, singleton=False)

        # Get two instances
        instance1 = self.registry.get_component("test_a")
        instance2 = self.registry.get_component("test_a")

        # Should be different instances
        assert instance1 is not instance2
        assert isinstance(instance1, MockComponentA)
        assert isinstance(instance2, MockComponentA)

    def test_lifecycle_listeners(self):
        """Test component lifecycle listeners."""
        events = []

        def lifecycle_listener(instance, event_type):
            events.append((type(instance).__name__, event_type))

        self.registry.add_lifecycle_listener("test_a", lifecycle_listener)
        self.registry.register_component("test_a", MockComponentA)

        # Load component
        self.registry.get_component("test_a")

        # Should have received loaded event
        assert len(events) == 1
        assert events[0] == ("MockComponentA", "loaded")

        # Unload component
        self.registry.unload_component("test_a")

        # Should have received unloaded event
        assert len(events) == 2
        assert events[1] == ("MockComponentA", "unloaded")

    def test_get_dependency_graph(self):
        """Test getting the dependency graph."""
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )
        self.registry.register_component(
            "test_c", MockComponentC, dependencies=["test_b"]
        )

        graph = self.registry.get_dependency_graph()

        assert graph["test_a"] == []
        assert graph["test_b"] == ["test_a"]
        assert graph["test_c"] == ["test_b"]

    def test_validate_dependencies(self):
        """Test dependency validation."""
        # Valid dependencies
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component(
            "test_b", MockComponentB, dependencies=["test_a"]
        )

        errors = self.registry.validate_dependencies()
        assert len(errors) == 0

        # Invalid dependency
        self.registry.register_component(
            "test_bad", MockComponentA, dependencies=["nonexistent"]
        )

        errors = self.registry.validate_dependencies()
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_component_creation_error(self):
        """Test handling of component creation errors."""

        def failing_factory():
            raise Exception("Creation failed")

        self.registry.register_component(
            "test_fail", MockComponentA, factory=failing_factory
        )

        with pytest.raises(ComponentCreationError):
            self.registry.get_component("test_fail")

    def test_event_emission_on_load_unload(self):
        """Test that events are emitted on component load/unload."""
        received_events = []

        def event_handler(event):
            received_events.append(event)

        # Subscribe to component events
        from tino.core.events import ComponentLoadedEvent, ComponentUnloadedEvent

        self.event_bus.subscribe(ComponentLoadedEvent, event_handler)
        self.event_bus.subscribe(ComponentUnloadedEvent, event_handler)

        self.registry.register_component("test_a", MockComponentA)

        # Load component
        self.registry.get_component("test_a")

        # Should have emitted loaded event
        assert len(received_events) == 1
        assert isinstance(received_events[0], ComponentLoadedEvent)
        assert received_events[0].component_name == "test_a"

        # Unload component
        self.registry.unload_component("test_a")

        # Should have emitted unloaded event
        assert len(received_events) == 2
        assert isinstance(received_events[1], ComponentUnloadedEvent)
        assert received_events[1].component_name == "test_a"

    def test_get_loaded_components(self):
        """Test getting list of loaded components."""
        self.registry.register_component("test_a", MockComponentA)
        self.registry.register_component("test_b", MockComponentB)

        # Initially no loaded components
        assert len(self.registry.get_loaded_components()) == 0

        # Load one component
        self.registry.get_component("test_a")
        loaded = self.registry.get_loaded_components()
        assert len(loaded) == 1
        assert "test_a" in loaded

        # Load another
        self.registry.get_component("test_b")
        loaded = self.registry.get_loaded_components()
        assert len(loaded) == 2
        assert "test_a" in loaded
        assert "test_b" in loaded

    def test_thread_safety_basic(self):
        """Test basic thread safety of registry operations."""
        import threading
        import time

        self.registry.register_component("test_a", MockComponentA)

        instances = []
        exceptions = []

        def worker():
            try:
                instance = self.registry.get_component("test_a")
                instances.append(instance)
                time.sleep(0.01)  # Small delay to encourage race conditions
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should have no exceptions
        assert len(exceptions) == 0

        # All instances should be the same (singleton)
        assert len(instances) == 10
        for instance in instances:
            assert instance is instances[0]
