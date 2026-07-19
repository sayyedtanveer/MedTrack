from typing import List, Dict, Any, Optional

class ModuleDefinition:
    def __init__(self, id: str, name: str, route: str, dependencies: List[str], roles: List[str], status: str = "active", icon: str = "Box"):
        self.id = id
        self.name = name
        self.route = route
        self.dependencies = dependencies
        self.roles = roles
        self.status = status
        self.icon = icon

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "route": self.route,
            "dependencies": self.dependencies,
            "roles": self.roles,
            "status": self.status,
            "icon": self.icon
        }

class ModuleRegistry:
    _instance = None
    _modules: Dict[str, ModuleDefinition] = {}
    _locked: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModuleRegistry, cls).__new__(cls)
            cls._instance._modules = {}
            cls._instance._locked = False
        return cls._instance

    def register(self, id: str, name: str, route: str, dependencies: List[str], roles: List[str], status: str = "active", icon: str = "Box"):
        """Registers a module in the global ERP application registry."""
        if self._locked:
            raise RuntimeError(f"Cannot register module '{id}': Registry is locked.")
        if id in self._modules:
            raise ValueError(f"Module '{id}' is already registered.")

        self._modules[id] = ModuleDefinition(
            id=id,
            name=name,
            route=route,
            dependencies=dependencies,
            roles=roles,
            status=status,
            icon=icon
        )

    def lock(self):
        """Locks the registry and validates all dependencies."""
        if self._locked:
            return
            
        # Validate dependencies
        for mod in self._modules.values():
            for dep in mod.dependencies:
                if dep not in self._modules:
                    raise ValueError(f"Module '{mod.id}' depends on unregistered module '{dep}'.")
        
        self._locked = True

    def get_system_map(self, user_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns the visible modules and their connections based on the user's role.
        """
        accessible_modules = []
        for mod in self._modules.values():
            if not user_role or user_role in mod.roles:
                accessible_modules.append({
                    "id": mod.id,
                    "name": mod.name,
                    "route": mod.route,
                    "status": mod.status,
                    "icon": mod.icon
                })

        accessible_ids = {m["id"] for m in accessible_modules}
        connections = []
        
        for mod in self._modules.values():
            if mod.id in accessible_ids:
                for dep in mod.dependencies:
                    if dep in accessible_ids:
                        connections.append({
                            "source": mod.id,
                            "target": dep
                        })

        return {
            "modules": accessible_modules,
            "connections": connections
        }

# Global singleton instance
module_registry = ModuleRegistry()
