"""
Component registry for dependency injection and lifecycle management.

Provides centralized management of component instances, dependency resolution,
and initialization order handling for the tino editor architecture.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable
from collections import defaultdict, deque
from threading import Lock
import time
import inspect

from .events import EventBus, ComponentLoadedEvent, ComponentUnloadedEvent

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ComponentRegistry:
    """
    Registry for managing component lifecycle and dependencies.
    
    Provides dependency injection, initialization order resolution, and
    component lifecycle management with thread safety and error handling.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the component registry.
        
        Args:
            event_bus: Optional event bus for lifecycle notifications
        """
        self._event_bus = event_bus or EventBus()
        self._components: Dict[str, Any] = {}
        self._component_types: Dict[str, Type] = {}
        self._factories: Dict[str, Callable[..., Any]] = {}
        self._dependencies: Dict[str, List[str]] = defaultdict(list)
        self._dependents: Dict[str, List[str]] = defaultdict(list)
        self._initialization_order: List[str] = []
        self._initialized: set[str] = set()
        self._loading: set[str] = set()
        self._lock = Lock()
        self._singleton_instances: Dict[str, Any] = {}
        self._lifecycle_listeners: Dict[str, List[Callable]] = defaultdict(list)
        
    def register_component(
        self,
        name: str,
        component_type: Type[T],
        factory: Optional[Callable[..., T]] = None,
        dependencies: Optional[List[str]] = None,
        singleton: bool = True
    ) -> None:
        """
        Register a component type with the registry.
        
        Args:
            name: Unique name for the component
            component_type: The class/type of the component
            factory: Optional factory function to create instances
            dependencies: List of component names this depends on
            singleton: Whether to maintain single instance
        """
        with self._lock:
            if name in self._component_types:
                logger.warning(f"Component {name} is already registered, overriding")
            
            self._component_types[name] = component_type
            self._factories[name] = factory or component_type
            self._dependencies[name] = dependencies or []
            
            # Update dependent tracking
            for dep in self._dependencies[name]:
                self._dependents[dep].append(name)
            
            # Mark for singleton handling
            if singleton:
                self._singleton_instances[name] = None
            elif name in self._singleton_instances:
                del self._singleton_instances[name]
            
            logger.debug(f"Registered component: {name} ({component_type.__name__})")
    
    def register_instance(self, name: str, instance: Any) -> None:
        """
        Register a pre-created instance.
        
        Args:
            name: Unique name for the component
            instance: The component instance
        """
        with self._lock:
            self._components[name] = instance
            self._component_types[name] = type(instance)
            self._singleton_instances[name] = instance
            self._initialized.add(name)
            
            logger.debug(f"Registered instance: {name} ({type(instance).__name__})")
    
    def get_component(self, name: str, component_type: Optional[Type[T]] = None) -> T:
        """
        Get a component instance, creating it if necessary.
        
        Args:
            name: Name of the component to get
            component_type: Optional type for type checking
            
        Returns:
            Component instance
            
        Raises:
            ComponentNotFoundError: If component is not registered
            CircularDependencyError: If circular dependency detected
            ComponentCreationError: If component cannot be created
        """
        with self._lock:
            # Check if component is registered
            if name not in self._component_types:
                raise ComponentNotFoundError(f"Component '{name}' is not registered")
            
            # Return existing singleton instance
            if name in self._singleton_instances and self._singleton_instances[name] is not None:
                instance = self._singleton_instances[name]
                if component_type and not isinstance(instance, component_type):
                    raise TypeError(f"Component {name} is not of type {component_type}")
                return instance  # type: ignore[return-value]
            
            # Return existing non-singleton instance
            if name in self._components:
                instance = self._components[name]
                if component_type and not isinstance(instance, component_type):
                    raise TypeError(f"Component {name} is not of type {component_type}")
                return instance  # type: ignore[return-value]
            
            # Create new instance
            return self._create_component(name, component_type)
    
    def _create_component(self, name: str, expected_type: Optional[Type[T]] = None) -> T:
        """Create a component instance with dependency resolution."""
        
        # Check for circular dependency
        if name in self._loading:
            cycle = list(self._loading) + [name]
            raise CircularDependencyError(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        self._loading.add(name)
        
        try:
            start_time = time.time()
            
            # Create dependency instances first
            dependency_instances: Dict[str, Any] = {}
            for dep_name in self._dependencies[name]:
                dependency_instances[dep_name] = self.get_component(dep_name)
            
            # Get factory function
            factory = self._factories[name]
            
            # Inspect factory signature to inject dependencies
            sig = inspect.signature(factory)
            kwargs = {}
            
            for param_name, param in sig.parameters.items():
                if param_name in dependency_instances:
                    kwargs[param_name] = dependency_instances[param_name]
                elif param_name == 'event_bus':
                    kwargs['event_bus'] = self._event_bus
                elif param_name == 'registry':
                    kwargs['registry'] = self
            
            # Create the instance
            instance = factory(**kwargs)
            
            # Validate type if specified
            if expected_type and not isinstance(instance, expected_type):
                raise TypeError(f"Factory for {name} returned {type(instance)}, expected {expected_type}")
            
            # Store the instance
            if name in self._singleton_instances:
                self._singleton_instances[name] = instance
            else:
                self._components[name] = instance
            
            self._initialized.add(name)
            
            # Calculate load time
            load_time = (time.time() - start_time) * 1000
            
            # Emit loaded event
            if self._event_bus:
                event = ComponentLoadedEvent(
                    component_name=name,
                    component_type=type(instance).__name__,
                    load_time_ms=load_time
                )
                self._event_bus.emit(event)
            
            # Call lifecycle listeners
            for listener in self._lifecycle_listeners.get(name, []):
                try:
                    listener(instance, 'loaded')
                except Exception as e:
                    logger.error(f"Error in lifecycle listener for {name}: {e}")
            
            logger.debug(f"Created component {name} in {load_time:.2f}ms")
            return instance
            
        except Exception as e:
            raise ComponentCreationError(f"Failed to create component '{name}': {e}") from e
        finally:
            self._loading.discard(name)
    
    def unload_component(self, name: str) -> bool:
        """
        Unload a component and its dependents.
        
        Args:
            name: Name of component to unload
            
        Returns:
            True if component was unloaded
        """
        with self._lock:
            if name not in self._initialized:
                return False
            
            start_time = time.time()
            
            # Unload dependents first
            for dependent in self._dependents[name]:
                self.unload_component(dependent)
            
            # Get the instance before removing it
            instance = None
            if name in self._singleton_instances:
                instance = self._singleton_instances[name]
                self._singleton_instances[name] = None
            elif name in self._components:
                instance = self._components.pop(name)
            
            # Call cleanup if available
            if instance and hasattr(instance, 'cleanup'):
                try:
                    instance.cleanup()
                except Exception as e:
                    logger.error(f"Error during cleanup of {name}: {e}")
            
            self._initialized.discard(name)
            
            # Calculate unload time
            unload_time = (time.time() - start_time) * 1000
            
            # Emit unloaded event
            if self._event_bus and instance:
                event = ComponentUnloadedEvent(
                    component_name=name,
                    component_type=type(instance).__name__,
                    unload_time_ms=unload_time
                )
                self._event_bus.emit(event)
            
            # Call lifecycle listeners
            for listener in self._lifecycle_listeners.get(name, []):
                try:
                    listener(instance, 'unloaded')
                except Exception as e:
                    logger.error(f"Error in lifecycle listener for {name}: {e}")
            
            logger.debug(f"Unloaded component {name} in {unload_time:.2f}ms")
            return True
    
    def is_loaded(self, name: str) -> bool:
        """Check if a component is loaded."""
        return name in self._initialized
    
    def get_loaded_components(self) -> List[str]:
        """Get list of loaded component names."""
        return list(self._initialized)
    
    def get_registered_components(self) -> List[str]:
        """Get list of registered component names."""
        return list(self._component_types.keys())
    
    def resolve_initialization_order(self) -> List[str]:
        """
        Resolve component initialization order based on dependencies.
        
        Returns:
            List of component names in initialization order
            
        Raises:
            CircularDependencyError: If circular dependencies exist
        """
        # Topological sort using Kahn's algorithm
        in_degree = {name: 0 for name in self._component_types}
        
        # Calculate in-degrees
        for name, deps in self._dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[name] += 1
        
        # Queue components with no dependencies
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Reduce in-degree for dependents
            for dependent in self._dependents[current]:
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for circular dependencies
        if len(result) != len(self._component_types):
            remaining = [name for name, degree in in_degree.items() if degree > 0]
            raise CircularDependencyError(f"Circular dependencies detected: {remaining}")
        
        self._initialization_order = result
        return result
    
    def initialize_all(self) -> List[str]:
        """
        Initialize all registered components in dependency order.
        
        Returns:
            List of successfully initialized component names
        """
        order = self.resolve_initialization_order()
        initialized = []
        
        for name in order:
            try:
                self.get_component(name)
                initialized.append(name)
            except Exception as e:
                logger.error(f"Failed to initialize component {name}: {e}")
                break
        
        return initialized
    
    def shutdown_all(self) -> List[str]:
        """
        Shutdown all components in reverse dependency order.
        
        Returns:
            List of successfully shutdown component names
        """
        # Shutdown in reverse order
        if not self._initialization_order:
            self.resolve_initialization_order()
        
        shutdown_order = reversed(self._initialization_order)
        shutdown_components = []
        
        for name in shutdown_order:
            if self.unload_component(name):
                shutdown_components.append(name)
        
        return shutdown_components
    
    def add_lifecycle_listener(self, component_name: str, listener: Callable) -> None:
        """
        Add a lifecycle listener for a component.
        
        Args:
            component_name: Name of component to listen to
            listener: Function to call on lifecycle events (instance, event_type)
        """
        self._lifecycle_listeners[component_name].append(listener)
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get the complete dependency graph."""
        return dict(self._dependencies)
    
    def get_component_info(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a component.
        
        Args:
            name: Component name
            
        Returns:
            Dictionary with component information
        """
        if name not in self._component_types:
            return {}
        
        return {
            'name': name,
            'type': self._component_types[name].__name__,
            'dependencies': list(self._dependencies[name]),
            'dependents': list(self._dependents[name]),
            'loaded': self.is_loaded(name),
            'singleton': name in self._singleton_instances,
            'factory': self._factories[name].__name__ if self._factories.get(name) else None
        }
    
    def validate_dependencies(self) -> List[str]:
        """
        Validate all component dependencies.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        for name, deps in self._dependencies.items():
            for dep in deps:
                if dep not in self._component_types:
                    errors.append(f"Component '{name}' depends on unregistered component '{dep}'")
        
        try:
            self.resolve_initialization_order()
        except CircularDependencyError as e:
            errors.append(str(e))
        
        return errors


class ComponentNotFoundError(Exception):
    """Raised when a requested component is not registered."""
    pass


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""
    pass


class ComponentCreationError(Exception):
    """Raised when a component cannot be created."""
    pass


# Global registry instance
_default_registry: Optional[ComponentRegistry] = None


def get_default_registry() -> ComponentRegistry:
    """Get the default global component registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ComponentRegistry()
    return _default_registry


def set_default_registry(registry: ComponentRegistry) -> None:
    """Set the default global component registry."""
    global _default_registry
    _default_registry = registry


if __name__ == "__main__":
    """
    Demo script showing component registry functionality.
    Run with: python -m tino.core.registry
    """
    print("=== Tino Component Registry Demo ===")
    
    # Create event bus and registry
    from tino.core.events import EventBus
    
    event_bus = EventBus()
    registry = ComponentRegistry(event_bus)
    
    # Example component classes
    class DatabaseConnection:
        def __init__(self) -> None:
            self.connected = False
            print("DatabaseConnection created")
        
        def connect(self) -> None:
            self.connected = True
            print("Database connected")
    
    class UserService:
        def __init__(self, database: DatabaseConnection):
            self.database = database
            print("UserService created with database dependency")
        
        def get_users(self) -> List[str]:
            if self.database.connected:
                return ["Alice", "Bob", "Charlie"]
            return []
    
    # Register components with dependencies
    print("\n1. Registering components...")
    registry.register_component("database", DatabaseConnection)
    registry.register_component("user_service", UserService, dependencies=["database"])
    
    # Show dependency graph
    print("\n2. Dependency graph:")
    dep_graph = registry.get_dependency_graph()
    for component, deps in dep_graph.items():
        print(f"  {component} depends on: {deps}")
    
    # Resolve initialization order
    print("\n3. Resolving initialization order...")
    init_order = registry.resolve_initialization_order()
    print(f"  Initialization order: {init_order}")
    
    # Get components (this will create them in dependency order)
    print("\n4. Creating components...")
    database = registry.get_component("database", DatabaseConnection)
    database.connect()
    
    user_service = registry.get_component("user_service", UserService)
    
    # Use the components
    print("\n5. Using components...")
    users = user_service.get_users()
    print(f"  Retrieved users: {users}")
    
    # Show component status
    print("\n6. Component status:")
    loaded_components = registry.get_loaded_components()
    for name in loaded_components:
        info = registry.get_component_info(name)
        print(f"  {name}: {info['type']} (loaded: {info['loaded']})")
    
    # Validate dependencies
    print("\n7. Validating dependencies...")
    validation_errors = registry.validate_dependencies()
    if validation_errors:
        print(f"  Validation errors: {validation_errors}")
    else:
        print("  All dependencies are valid!")
    
    # Demonstrate error handling
    print("\n8. Error handling demo...")
    try:
        registry.get_component("non_existent")
    except ComponentNotFoundError as e:
        print(f"  Caught expected error: {e}")
    
    print("\n=== Demo Complete ===")
    print(f"Registry successfully demonstrated dependency injection with {len(loaded_components)} components!")
    print("\nComponent Registry Features Demonstrated:")
    print("  ✓ Component registration with dependencies")
    print("  ✓ Automatic dependency resolution")
    print("  ✓ Topological sort for initialization order")
    print("  ✓ Singleton instance management")
    print("  ✓ Component lifecycle tracking")
    print("  ✓ Dependency validation")
    print("  ✓ Error handling for missing components")