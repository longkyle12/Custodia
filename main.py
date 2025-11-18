from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable
import json




# Resources

@dataclass
class ResourcePool:
    gold: int=0
    food: int=0
    loyalty: int=50
    security: int=50

    raw_goods: int=0
    manufactured_goods: int=0
    rare_goods: int=0

    prosperity: int=0

    def apply_change(self, **changes):
        for k, v in changes.items():
            if hasattr(self,k):
                setattr(self, k, getattr(self, k)+v)
        

# City Statss

@dataclass
class CityStats:
    economy: int=0 # Gold Gen
    culture: int=0 # loyalty
    agriculture: int=0 # food
    industry: int=0 # Goods
    military: int=0 # Security

# Buildings
@dataclass
class BuildingProject:
    name: str
    total_time: int
    remaining_time: int
    description: str
    cost: Dict[str, int]
    production: Dict[str, int]
    consumption: Dict[str, int]


    def tick(self):
        # Reduces construction time by 1 and returns true when done
        self.remaining_time = max(0, self.remaining_time - 1)
        return self.remaining_time == 0
    
# Building
@dataclass
class Building:
    name: str
    production: Dict[str, int]
    consumption: Dict[str, int]
    description: str
    
# City
@dataclass
class City:
    name: str
    resources: ResourcePool = field(default_factory=ResourcePool)
    stats: CityStats = field(default_factory=CityStats)

    construction_queue: List[BuildingProject] = field(default_factory=list)
    completed_buildings: List["Building"] = field(default_factory=list)

    declared_action: Optional[str] = None

    # Construction

    def start_construction(self, project: BuildingProject):
        if self.construction_queue:
            raise ValueError("City already has an active project!")
        self.construction_queue.append(project)

    def process_construction(self):
        if not self.construction_queue:
            return []
        completed_projects = []
        project = self.construction_queue[0]
        if project.tick():
            self.construction_queue.pop(0)
            finished = Building(
                name=project.name,
                production=property.production,
                consumption=project.consumption,
                descritpion= project.description
            )
            self.completed_buildings.append(finished)
            completed_projects.append(finished)
            
        return completed_projects
    
    def apply_building_production(self):
        for building in self.completed_buildings:
            self.resources.apply_change(**building.production)
    
    # Actions

    def resolve_action(self):
        action = self.declared_action
        self.declared_action = None
        # Return results for log
        return f"{self.name} resolved action: {action}"
    
# Kingdom

@dataclass
class Kingdom:
    name: str
    cities: List[City] = field(default_factory=list)

    saftey: int=0
    happiness: int=0

    declared_kingdom_action: Optional[str] = None

    # Stat

    def update_kingdom_stats(self):
        if not self.cites:
            return
        
        self.saftey = int(sum(c.resources.security for c in self.cities) / len(self.cities))
        self.happiness = int(sum(c.resources.loyalty for c in self.cities) / len(self.cities))

    # Turn flow

    def resolve_turn(self):
        turn_log = []

        # Upkeep
        turn_log.append("=== UPKEEP PHASE ===")
        for city in self.cities:
            finished = city.process_construction()
            city.apply_building_production()
            for building in finished:
                turn_log.append(f"{city.name} finished {building.name}")

        # Declaration
        turn_log.append("=== DECLARATION PHASE ===")

        # Action
        if self.declared_kingdom_action:
            turn_log.append(f"Kingdom performs action: {self.declared_kingdom_action}")
            self.declared_kingdom_action = None

        for city in self.cities:
            result = city.resolve_action()
            turn_log.append(result)

        # Territory Claims
        turn_log.append("=== CLAIM TERRITORIES PHASE ===")

        # End
        turn_log.append("=== END PHASE ===")
        self.update_kingdom_stats()
        turn_log.append(f"Kingdom Safety: {self.safety}")
        turn_log.append(f"Kingdom Happiness: {self.happiness}")

        return turn_log


def to_dict(obj):
    return json.loads(json.dumps(asdict(obj)))

def save_kingdom(kingdom: Kingdom, filename="kingdom.json"):
    with open(filename, "w") as f:
        json.dump(to_dict(kingdom), f, indent=4)
   
def load_kingdom(filename="kingdom.json") -> Kingdom:
    with open(filename, "r") as f:
        data = json.load(f)

    cities = []
    for c in data["cities"]:

        resources=ResourcePool(**c["resources"])
        stats=CityStats(**c["stats"])

        construction_queue = []
        for proj in c.get("construction_queue", []):
            construction_queue.append(
                BuildingProject(
                    name=proj["name"],
                    total_time=proj["total_time"],
                    remaining_time=proj["remaining_time"],
                    description=proj["description"],
                    cost=proj["cost"],
                    production=proj["production"]
                )
            )
        completed_buildings = []
        for b in c.get("completed_buildings", []):
            city.completed_buildings.append(
                Building(name=b["name"], 
                         production=b["prodution"], 
                         consumption=b["consumption"],
                         description=b["description"])
            )

        city = City(
            name=c["name"],
            resources=resources,
            stats=stats,
            construction_queue=construction_queue,
            completed_buildings=completed_buildings,
            declared_action=c.get("declared_action")
        )

        cities.append(city)

    k = Kingdom(name=data["name"], cities=cities)
    return k