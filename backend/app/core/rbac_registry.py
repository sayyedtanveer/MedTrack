"""
Centralized RBAC endpoint registry.
Tracks required permissions for each endpoint.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum


class HTTPMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class EndpointRBACRule:
    """RBAC enforcement rule for an endpoint."""
    
    path: str                          # e.g., "/api/v1/products/templates"
    method: HTTPMethod                 # HTTP method
    required_permission: str           # e.g., "product:write"
    required_roles: Optional[Set[str]] # Optional: if only certain roles
    description: str                   # What this endpoint does
    audit_log: bool = True            # Log permission denials?
    
    def __str__(self) -> str:
        return f"{self.method:6} {self.path:50} → {self.required_permission:25} | {self.description}"


class RBACRegistry:
    """Centralized endpoint permission registry."""
    
    def __init__(self):
        self._rules: Dict[str, List[EndpointRBACRule]] = {}
    
    def register(self, rule: EndpointRBACRule) -> None:
        """Register an endpoint's RBAC rule."""
        key = f"{rule.method.value}:{rule.path}"
        if key not in self._rules:
            self._rules[key] = []
        self._rules[key].append(rule)
    
    def get_rule(self, method: str, path: str) -> Optional[EndpointRBACRule]:
        """Get RBAC rule for endpoint."""
        key = f"{method}:{path}"
        rules = self._rules.get(key, [])
        return rules[0] if rules else None
    
    def get_all_rules(self) -> Dict[str, List[EndpointRBACRule]]:
        """Export all rules (for audit/compliance)."""
        return dict(self._rules)
    
    def count_registered(self) -> int:
        """Get total number of registered endpoints."""
        return sum(len(rules) for rules in self._rules.values())
    
    def audit_report(self) -> str:
        """Generate human-readable audit report of all endpoints."""
        lines = ["=" * 120]
        lines.append(f"{'RBAC Endpoint Registry':^120}")
        lines.append(f"{'Total Endpoints Registered: ' + str(self.count_registered()):^120}")
        lines.append("=" * 120)
        lines.append("")
        
        for endpoint in sorted(self._rules.keys()):
            for rule in sorted(self._rules[endpoint], key=lambda r: r.description):
                lines.append(str(rule))
        
        lines.append("")
        lines.append("=" * 120)
        return "\n".join(lines)
    
    def endpoints_by_permission(self, permission: str) -> List[str]:
        """Get all endpoints requiring a specific permission."""
        endpoints = []
        for endpoint, rules in self._rules.items():
            if any(rule.required_permission == permission for rule in rules):
                endpoints.append(endpoint)
        return sorted(endpoints)
    
    def endpoints_by_role(self, role: str) -> List[str]:
        """Get all endpoints accessible by a specific role."""
        endpoints = []
        for endpoint, rules in self._rules.items():
            if any(
                rule.required_roles is None or role in rule.required_roles
                for rule in rules
            ):
                endpoints.append(endpoint)
        return sorted(endpoints)


# Singleton instance
rbac_registry = RBACRegistry()


def register_endpoint_rule(
    path: str,
    method: HTTPMethod,
    required_permission: str,
    description: str,
    required_roles: Optional[Set[str]] = None,
    audit_log: bool = True,
) -> None:
    """
    Convenience function to register an endpoint rule.
    
    Usage:
        register_endpoint_rule(
            path="/api/v1/products/templates",
            method=HTTPMethod.POST,
            required_permission="product:write",
            description="Create product template",
        )
    """
    rule = EndpointRBACRule(
        path=path,
        method=method,
        required_permission=required_permission,
        required_roles=required_roles,
        description=description,
        audit_log=audit_log,
    )
    rbac_registry.register(rule)
