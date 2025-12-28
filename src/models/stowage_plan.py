"""
Stowage Plan data models.
Ported from STOWAGEMASTER with simplifications for ULLAGEMASTER integration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
import uuid
from pathlib import Path
from datetime import datetime


@dataclass
class Receiver:
    """Represents a cargo receiver"""
    name: str
    
    def to_dict(self) -> dict:
        return {'name': self.name}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Receiver':
        return cls(name=data['name'])


@dataclass
class StowageCargo:
    """Represents a cargo for stowage planning.
    
    Simplified from STOWAGEMASTER - only fields needed for ULLAGEMASTER.
    """
    cargo_type: str  # Grade name (e.g., "MOTORIN", "FUEL OIL")
    quantity: float  # Volume in m³
    receivers: List[Receiver] = field(default_factory=list)
    unique_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    density: float = 0.85  # VAC density
    custom_color: Optional[str] = None  # Custom hex color
    
    def get_receiver_names(self) -> str:
        """
        Get a comma-separated string of all receiver names.
        Returns "Genel" (General) if no receivers are defined.
        """
        if not self.receivers:
            return "Genel"
        return ", ".join([r.name for r in self.receivers])
    
    def to_dict(self) -> dict:
        result = {
            'unique_id': self.unique_id,
            'cargo_type': self.cargo_type,
            'quantity': self.quantity,
            'receivers': [r.to_dict() for r in self.receivers],
            'density': self.density,
        }
        if self.custom_color:
            result['custom_color'] = self.custom_color
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StowageCargo':
        receivers = [Receiver.from_dict(r) for r in data.get('receivers', [])]
        return cls(
            unique_id=data.get('unique_id', str(uuid.uuid4())),
            cargo_type=data['cargo_type'],
            quantity=data.get('quantity', 0.0),
            receivers=receivers,
            density=data.get('density', 0.85),
            custom_color=data.get('custom_color'),
        )


@dataclass
class TankAssignment:
    """Represents a cargo assignment to a tank"""
    tank_id: str
    cargo: StowageCargo
    quantity_loaded: float  # Actual quantity loaded in this tank
    
    def to_dict(self) -> dict:
        return {
            'tank_id': self.tank_id,
            'cargo': self.cargo.to_dict(),
            'quantity_loaded': self.quantity_loaded
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TankAssignment':
        return cls(
            tank_id=data['tank_id'],
            cargo=StowageCargo.from_dict(data['cargo']),
            quantity_loaded=data['quantity_loaded']
        )


@dataclass
class StowagePlan:
    """Represents a complete stowage plan.
    
    Simplified from STOWAGEMASTER - no optimizer-specific fields.
    """
    ship_name: str = "New Ship"
    cargo_requests: List[StowageCargo] = field(default_factory=list)
    assignments: Dict[str, TankAssignment] = field(default_factory=dict)  # tank_id -> assignment
    excluded_tanks: List[str] = field(default_factory=list)
    created_date: Optional[datetime] = None
    plan_name: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        if not self.created_date:
            self.created_date = datetime.now()
        if not self.plan_name:
            self.plan_name = f"Plan_{self.created_date.strftime('%Y%m%d_%H%M%S')}"
    
    def add_cargo(self, cargo: StowageCargo):
        """Add a cargo to the plan"""
        self.cargo_requests.append(cargo)
    
    def remove_cargo(self, cargo_id: str):
        """Remove a cargo and all its assignments"""
        self.cargo_requests = [c for c in self.cargo_requests if c.unique_id != cargo_id]
        # Remove assignments for this cargo
        to_remove = [tid for tid, a in self.assignments.items() if a.cargo.unique_id == cargo_id]
        for tid in to_remove:
            del self.assignments[tid]
    
    def get_cargo_by_id(self, cargo_id: str) -> Optional[StowageCargo]:
        """Get cargo by unique ID"""
        for cargo in self.cargo_requests:
            if cargo.unique_id == cargo_id:
                return cargo
        return None
    
    def add_assignment(self, tank_id: str, assignment: TankAssignment):
        """Add or update a tank assignment"""
        self.assignments[tank_id] = assignment
    
    def get_assignment(self, tank_id: str) -> Optional[TankAssignment]:
        """Get assignment for a tank"""
        return self.assignments.get(tank_id)
    
    def remove_assignment(self, tank_id: str):
        """Remove assignment for a tank"""
        if tank_id in self.assignments:
            del self.assignments[tank_id]
    
    def get_cargo_total_loaded(self, cargo_unique_id: str) -> float:
        """
        Calculate the total quantity loaded for a specific cargo across all tanks.
        Iterates through all assignments and sums up quantity_loaded.
        
        Args:
            cargo_unique_id: Unique ID of the cargo to check
            
        Returns:
            Total volume loaded in m³
        """
        total = 0.0
        for assignment in self.assignments.values():
            if assignment.cargo.unique_id == cargo_unique_id:
                total += assignment.quantity_loaded
        return total
    
    def clear(self):
        """Clear all cargos and assignments"""
        self.cargo_requests.clear()
        self.assignments.clear()
        self.excluded_tanks.clear()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'plan_name': self.plan_name,
            'ship_name': self.ship_name,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'cargo_requests': [c.to_dict() for c in self.cargo_requests],
            'assignments': {tid: a.to_dict() for tid, a in self.assignments.items()},
            'excluded_tanks': list(self.excluded_tanks),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StowagePlan':
        cargo_requests = [StowageCargo.from_dict(c) for c in data.get('cargo_requests', [])]
        assignments = {tid: TankAssignment.from_dict(a) for tid, a in data.get('assignments', {}).items()}
        
        created_date = None
        if data.get('created_date'):
            created_date = datetime.fromisoformat(data['created_date'])
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            plan_name=data.get('plan_name', ''),
            ship_name=data.get('ship_name', 'Unknown Ship'),
            created_date=created_date,
            cargo_requests=cargo_requests,
            assignments=assignments,
            excluded_tanks=data.get('excluded_tanks', []),
        )
    
    def save_to_json(self, filepath: str):
        """Save plan to JSON file"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'StowagePlan':
        """Load plan from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
