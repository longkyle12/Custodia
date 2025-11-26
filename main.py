from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable
import json





# Resources

@dataclass
class ResourcePool:
    gold: int=0
    population: int=0
    food: int=50
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
    
BUILDINGS_FILE = "buildings.json"
AVAILABLE_BUILDINGS: Dict[str, BuildingProject] = {}

def save_available_buildings():
    data = {
        name: asdict(project)
        for name, project in AVAILABLE_BUILDINGS.items()
    }
    with open(BUILDINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_available_buildings():
    try:
        with open(BUILDINGS_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return  # No file yet, that’s fine

    for name, proj in data.items():
        AVAILABLE_BUILDINGS[name] = BuildingProject(
            name=proj["name"],
            total_time=proj["total_time"],
            remaining_time=proj["remaining_time"],
            description=proj["description"],
            cost=proj.get("cost", {}),
            production=proj.get("production", {}),
            consumption=proj.get("consumption", {})
        )

# City
@dataclass
class City:
    name: str
    resources: ResourcePool = field(default_factory=ResourcePool)

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
                production=project.production,
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
    
# Building CLI
def manage_available_buildings():
    while True:
        print("\n=== BUILDABLE STRUCTURES MENU ===")
        print("1. List Buildable Structures")
        print("2. Add New Structure Template")
        print("0. Back")

        choice = input("> ").strip()

        if choice == "0":
            return

        elif choice == "1":
            if not AVAILABLE_BUILDINGS:
                print("No building templates added.")
            else:
                print("\nTemplates available to all cities:")
                for b in AVAILABLE_BUILDINGS.values():
                    print(f"• {b.name} ({b.total_time} days)")

        elif choice == "2":
            name = input("Name: ").strip()
            time = int(input("Construction time (days): ").strip())

            # Create dictionary entries
            production = {}
            consumption = {}
            cost = {}

            print("Enter production (empty key to stop):")
            while True:
                key = input(" Resource: ").strip()
                if key == "":
                    break
                value = int(input(" Amount: "))
                production[key] = value

            print("Enter consumption (empty key to stop):")
            while True:
                key = input(" Resource: ").strip()
                if key == "":
                    break
                value = int(input(" Amount: "))
                consumption[key] = value

            description = input("Description: ").strip()

            AVAILABLE_BUILDINGS[name] = BuildingProject(
                name=name,
                total_time=time,
                remaining_time=time,
                cost=cost,
                production=production,
                consumption=consumption,
                description=description
            )
            save_available_buildings()
            print(f"Added structure template: {name}")

        else:
            print("Invalid selection.")


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
        if not self.cities:
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
        turn_log.append(f"Kingdom Saftey: {self.saftey}")
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
            construction_queue=construction_queue,
            completed_buildings=completed_buildings,
            declared_action=c.get("declared_action")
        )

        cities.append(city)

    k = Kingdom(name=data["name"], cities=cities)
    return k

def add_city_cli(kingdom: Kingdom):
    name = input("Enter new city name: ").strip()
    if not name:
        print("City name cannot be empty.")
        return

    # Create new city
    new_city = City(name=name)

    kingdom.cities.append(new_city)
    print(f"City '{name}' added to the kingdom.")

    # Mark action for the turn
    kingdom.declared_kingdom_action = f"Added City: {name}"

# Kingdom Action Menu
def kingdom_action_menu(kingdom: Kingdom):
    print("\n=== KINGDOM ACTIONS ===")
    actions = [
        "Add New City",
        "Raise Taxes",
        "Hold Festival",
        "Do Nothing"
    ]

    for i, action in enumerate(actions, start=1):
        print(f"{i}. {action}")
    print("0. Cancel")

    choice = input("> ").strip()
    if choice == "0":
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(actions)):
        print("Invalid option.")
        return

    chosen = actions[int(choice) - 1]

    if chosen == "Add New City":
        add_city_cli(kingdom)
        return

    kingdom.declared_kingdom_action = chosen
    print(f"Kingdom will: {chosen}")


def run_cli(kingdom: Kingdom):
    while True:
        load_available_buildings()
        print("\n===== KINGDOM MENU =====")
        print(f"Kingdom: {kingdom.name}")
        print("1. List Cities")
        print("2. View Kingdom Stats")
        print("3. Save Kingdom")
        print("4. Next Turn")
        print("5. Manage Buildable Structures")
        print("6. Set Kingdom Action")
        print("0. Quit")

        choice = input("> ").strip()

        # ---- List Cities ----
        if choice == "1":
            city_selector(kingdom)

        # ---- Kingdom Stats ----
        elif choice == "2":
            print("\n=== KINGDOM STATS ===")
            print(f"Safety: {kingdom.saftey}")
            print(f"Happiness: {kingdom.happiness}")

        # ---- Save ----
        elif choice == "3":
            save_kingdom(kingdom)
            print("Kingdom saved.")

        # ---- Turn Resolution ----
        elif choice == "4":
            logs = kingdom.resolve_turn()
            print("\n".join(logs))
        
        elif choice == "5":
            manage_available_buildings()

        elif choice == "6":
            kingdom_action_menu(kingdom)

        # ---- Quit ----
        elif choice == "0":
            print("Exiting...")
            break

        else:
            print("Invalid selection. Try again.")


#  City Selector


def city_selector(kingdom: Kingdom):
    while True:
        print("\n===== CITY LIST =====")
        for i, c in enumerate(kingdom.cities, start=1):
            print(f"{i}. {c.name}")
        print("0. Back")

        choice = input("> ").strip()
        if choice == "0":
            return

        if not choice.isdigit() or not (1 <= int(choice) <= len(kingdom.cities)):
            print("Invalid selection.")
            continue

        city = kingdom.cities[int(choice) - 1]
        city_menu(city)


# City Menu

def city_menu(city: City):
    while True:
        print(f"\n===== CITY: {city.name} =====")
        print("1. View Resources")
        print("2. View Buildings")
        print("3. View Construction Queue")
        print("4. Start Construction")
        print("5. Set City Action")
        print("0. Back")

        choice = input("> ").strip()

        if choice == "0":
            return

        elif choice == "1":
            show_city_resources(city)

        elif choice == "2":
            buildings_menu(city)

        elif choice == "3":
            show_construction_queue(city)

        elif choice == "4":
            start_construction_cli(city)

        elif choice == "5":
            set_city_action(city)
        else:
            print("Invalid option.")

def set_city_action(city: City):
    print(f"\n=== ACTIONS FOR {city.name} ===")
    actions = [
        "Gather Resources",
        "Increase Loyalty",
        "Patrol City",
        "Train Militia",
        "Do Nothing"
    ]

    for i, action in enumerate(actions, start=1):
        print(f"{i}. {action}")
    print("0. Cancel")

    choice = input("> ").strip()
    if choice == "0":
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(actions)):
        print("Invalid action.")
        return

    city.declared_action = actions[int(choice) - 1]
    print(f"{city.name} will: {city.declared_action}")


def start_construction_cli(city: City):
    if city.construction_queue:
        print("City already has an active construction project!")
        return

    if not AVAILABLE_BUILDINGS:
        print("No available buildings to construct. Add some in the main menu.")
        return

    print("\n=== START CONSTRUCTION ===")
    print("Choose a building to start:")

    keys = list(AVAILABLE_BUILDINGS.keys())
    for i, name in enumerate(keys, start=1):
        b = AVAILABLE_BUILDINGS[name]
        print(f"{i}. {b.name} ({b.total_time} days)")

    print("0. Cancel")

    choice = input("> ").strip()
    if choice == "0":
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(keys)):
        print("Invalid selection.")
        return

    selected_name = keys[int(choice) - 1]
    template = AVAILABLE_BUILDINGS[selected_name]

    # Create a fresh project instance
    project = BuildingProject(
        name=template.name,
        total_time=template.total_time,
        remaining_time=template.total_time,
        description=template.description,
        cost=template.cost.copy(),
        production=template.production.copy(),
        consumption=template.consumption.copy()
    )

    city.start_construction(project)
    print(f"{city.name} has begun construction of {project.name}.")


#     Display Resources

def show_city_resources(city: City):
    print(f"\n=== RESOURCES: {city.name} ===")
    r = city.resources
    print(f"Gold: {r.gold}")
    print(f"Food: {r.food}")
    print(f"Loyalty: {r.loyalty}")
    print(f"Security: {r.security}")
    print(f"Raw Goods: {r.raw_goods}")
    print(f"Manufactured Goods: {r.manufactured_goods}")
    print(f"Rare Goods: {r.rare_goods}")
    print(f"Prosperity: {r.prosperity}")


#   Buildings Menu

def buildings_menu(city: City):
    while True:
        print(f"\n=== BUILDINGS IN {city.name} ===")

        if not city.completed_buildings:
            print("No completed buildings.")
            return

        for i, b in enumerate(city.completed_buildings, start=1):
            print(f"{i}. {b.name}")
        print("0. Back")

        choice = input("> ").strip()
        if choice == "0":
            return

        if not choice.isdigit() or not (1 <= int(choice) <= len(city.completed_buildings)):
            print("Invalid selection.")
            continue

        building = city.completed_buildings[int(choice) - 1]
        show_building_details(building)


# Display Buildings Details

def show_building_details(building: Building):
    print(f"\n=== {building.name.upper()} ===")
    print(f"Description: {building.description}")

    print("\nProduction:")
    for k, v in building.production.items():
        print(f"  +{v} {k}")

    print("\nConsumption:")
    if building.consumption:
        for k, v in building.consumption.items():
            print(f"  -{v} {k}")
    else:
        print("  None")


# Construction Queue

def show_construction_queue(city: City):
    print(f"\n=== CONSTRUCTION QUEUE: {city.name} ===")
    if not city.construction_queue:
        print("No active construction projects.")
        return

    for project in city.construction_queue:
        print(f"- {project.name}: {project.remaining_time}/{project.total_time} days remaining")


















if __name__ == "__main__":
    try:
        kingdom = load_kingdom()
        print("Loaded existing kingdom.")
    except:
        kingdom = Kingdom(name="My Kingdom")
        print("Created new kingdom.")

    run_cli(kingdom)