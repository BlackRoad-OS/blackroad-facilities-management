#!/usr/bin/env python3
"""BlackRoad Facilities Management - buildings, rooms, assets."""

from __future__ import annotations
import argparse
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

GREEN = "\033[0;32m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
NC = "\033[0m"

DB_PATH = Path.home() / ".blackroad" / "facilities-management.db"


@dataclass
class Building:
    id: int
    name: str
    address: str
    floors: int
    total_sqft: float
    building_type: str
    created_at: str
    active: int


@dataclass
class Room:
    id: int
    building_id: int
    name: str
    floor: int
    capacity: int
    room_type: str
    status: str
    created_at: str


@dataclass
class Asset:
    id: int
    room_id: int
    name: str
    asset_type: str
    serial_number: str
    purchase_date: str
    condition: str
    last_inspected: str
    notes: str


class FacilitiesManagement:
    """Facilities management system with full asset tracking."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS buildings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    address TEXT DEFAULT '',
                    floors INTEGER DEFAULT 1,
                    total_sqft REAL DEFAULT 0,
                    building_type TEXT DEFAULT 'office',
                    created_at TEXT NOT NULL,
                    active INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    building_id INTEGER NOT NULL REFERENCES buildings(id),
                    name TEXT NOT NULL,
                    floor INTEGER DEFAULT 1,
                    capacity INTEGER DEFAULT 10,
                    room_type TEXT DEFAULT 'office',
                    status TEXT DEFAULT 'available',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL REFERENCES rooms(id),
                    name TEXT NOT NULL,
                    asset_type TEXT DEFAULT 'equipment',
                    serial_number TEXT DEFAULT '',
                    purchase_date TEXT DEFAULT '',
                    condition TEXT DEFAULT 'good',
                    last_inspected TEXT DEFAULT '',
                    notes TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_rooms_building ON rooms(building_id);
                CREATE INDEX IF NOT EXISTS idx_assets_room ON assets(room_id);
            """)

    def add_building(self, name: str, address: str = "", floors: int = 1,
                     sqft: float = 0, building_type: str = "office") -> Building:
        """Register a building."""
        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now().isoformat()
            cur = conn.execute(
                "INSERT INTO buildings (name,address,floors,total_sqft,building_type,created_at)"
                " VALUES (?,?,?,?,?,?)",
                (name, address, floors, sqft, building_type, now),
            )
            return Building(cur.lastrowid, name, address, floors, sqft, building_type, now, 1)

    def add_room(self, building_name: str, room_name: str, floor: int = 1,
                 capacity: int = 10, room_type: str = "office") -> Room:
        """Add a room to a building."""
        with sqlite3.connect(self.db_path) as conn:
            b = conn.execute(
                "SELECT id FROM buildings WHERE name=?", (building_name,)
            ).fetchone()
            if not b:
                raise ValueError(f"Building '{building_name}' not found")
            now = datetime.now().isoformat()
            cur = conn.execute(
                "INSERT INTO rooms (building_id,name,floor,capacity,room_type,created_at)"
                " VALUES (?,?,?,?,?,?)",
                (b[0], room_name, floor, capacity, room_type, now),
            )
            return Room(cur.lastrowid, b[0], room_name, floor, capacity, room_type, "available", now)

    def add_asset(self, room_id: int, name: str, asset_type: str = "equipment",
                  serial_number: str = "", purchase_date: str = "",
                  condition: str = "good", notes: str = "") -> Asset:
        """Register an asset in a room."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO assets"
                " (room_id,name,asset_type,serial_number,purchase_date,condition,last_inspected,notes)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (room_id, name, asset_type, serial_number, purchase_date, condition, now, notes),
            )
            return Asset(cur.lastrowid, room_id, name, asset_type,
                         serial_number, purchase_date, condition, now, notes)

    def list_buildings(self) -> list:
        """Return active buildings."""
        with sqlite3.connect(self.db_path) as conn:
            return [Building(*r) for r in
                    conn.execute("SELECT * FROM buildings WHERE active=1").fetchall()]

    def list_rooms(self, building_name: str = None) -> list:
        """Return rooms, optionally filtered by building."""
        with sqlite3.connect(self.db_path) as conn:
            if building_name:
                b = conn.execute(
                    "SELECT id FROM buildings WHERE name=?", (building_name,)
                ).fetchone()
                if not b:
                    return []
                rows = conn.execute(
                    "SELECT * FROM rooms WHERE building_id=?", (b[0],)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM rooms").fetchall()
            return [Room(*r) for r in rows]

    def list_assets(self, room_id: int = None) -> list:
        """Return assets, optionally filtered by room."""
        with sqlite3.connect(self.db_path) as conn:
            if room_id:
                rows = conn.execute(
                    "SELECT * FROM assets WHERE room_id=?", (room_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM assets").fetchall()
            return [Asset(*r) for r in rows]

    def status(self) -> dict:
        """Summary statistics."""
        with sqlite3.connect(self.db_path) as conn:
            buildings = conn.execute("SELECT COUNT(*) FROM buildings WHERE active=1").fetchone()[0]
            rooms = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
            assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
            avail = conn.execute(
                "SELECT COUNT(*) FROM rooms WHERE status='available'"
            ).fetchone()[0]
        return {"active_buildings": buildings, "total_rooms": rooms,
                "available_rooms": avail, "total_assets": assets,
                "db_path": str(self.db_path)}

    def export_data(self) -> dict:
        """Export full dataset."""
        with sqlite3.connect(self.db_path) as conn:
            buildings = [Building(*r) for r in conn.execute("SELECT * FROM buildings").fetchall()]
            rooms = [Room(*r) for r in conn.execute("SELECT * FROM rooms").fetchall()]
            assets = [Asset(*r) for r in conn.execute("SELECT * FROM assets").fetchall()]
        return {
            "buildings": [asdict(b) for b in buildings],
            "rooms": [asdict(r) for r in rooms],
            "assets": [asdict(a) for a in assets],
            "exported_at": datetime.now().isoformat(),
        }


def _cond_color(cond: str) -> str:
    return {"excellent": GREEN, "good": CYAN, "fair": YELLOW, "poor": RED}.get(cond, NC)


def _fmt_building(b: Building) -> None:
    print(f"  {CYAN}[{b.id}]{NC} {BOLD}{b.name}{NC}  {b.address}"
          f"  floors={b.floors}  {b.total_sqft:.0f}sqft  type={YELLOW}{b.building_type}{NC}")


def _fmt_room(r: Room) -> None:
    sc = GREEN if r.status == "available" else YELLOW
    print(f"  {CYAN}[{r.id}]{NC} {BOLD}{r.name}{NC}  floor={r.floor}"
          f"  cap={r.capacity}  type={YELLOW}{r.room_type}{NC}  [{sc}{r.status}{NC}]")


def _fmt_asset(a: Asset) -> None:
    cc = _cond_color(a.condition)
    print(f"  {CYAN}[{a.id}]{NC} {BOLD}{a.name}{NC}  type={YELLOW}{a.asset_type}{NC}"
          f"  s/n={a.serial_number}  condition={cc}{a.condition}{NC}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="facilities_management",
        description=f"{BOLD}BlackRoad Facilities Management{NC}",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="System status")
    sub.add_parser("export", help="Export data as JSON")

    ls = sub.add_parser("list", help="List buildings, rooms, or assets")
    ls.add_argument("target", choices=["buildings", "rooms", "assets"], nargs="?", default="buildings")
    ls.add_argument("--building", default=None)
    ls.add_argument("--room-id", type=int, default=None)

    ab = sub.add_parser("add-building", help="Register a building")
    ab.add_argument("name")
    ab.add_argument("--address", default="")
    ab.add_argument("--floors", type=int, default=1)
    ab.add_argument("--sqft", type=float, default=0)
    ab.add_argument("--type", dest="building_type", default="office")

    ar = sub.add_parser("add-room", help="Add a room to a building")
    ar.add_argument("building")
    ar.add_argument("room_name")
    ar.add_argument("--floor", type=int, default=1)
    ar.add_argument("--capacity", type=int, default=10)
    ar.add_argument("--type", dest="room_type", default="office")

    aa = sub.add_parser("add-asset", help="Register an asset in a room")
    aa.add_argument("room_id", type=int)
    aa.add_argument("name")
    aa.add_argument("--type", dest="asset_type", default="equipment")
    aa.add_argument("--serial", default="")
    aa.add_argument("--condition", default="good")
    aa.add_argument("--notes", default="")

    args = parser.parse_args()
    fm = FacilitiesManagement()

    if args.cmd == "list":
        target = getattr(args, "target", "buildings")
        if target == "buildings":
            items = fm.list_buildings()
            print(f"\n{BOLD}{BLUE}Buildings ({len(items)}){NC}")
            [_fmt_building(b) for b in items] or print(f"  {YELLOW}none{NC}")
        elif target == "rooms":
            items = fm.list_rooms(args.building)
            label = f"building={args.building}" if args.building else "all buildings"
            print(f"\n{BOLD}{BLUE}Rooms ({len(items)}) — {label}{NC}")
            [_fmt_room(r) for r in items] or print(f"  {YELLOW}none{NC}")
        else:
            items = fm.list_assets(args.room_id)
            label = f"room={args.room_id}" if args.room_id else "all rooms"
            print(f"\n{BOLD}{BLUE}Assets ({len(items)}) — {label}{NC}")
            [_fmt_asset(a) for a in items] or print(f"  {YELLOW}none{NC}")

    elif args.cmd == "add-building":
        b = fm.add_building(args.name, args.address, args.floors, args.sqft, args.building_type)
        print(f"{GREEN}✓{NC} Building {BOLD}{b.name}{NC} registered (id={b.id})")

    elif args.cmd == "add-room":
        r = fm.add_room(args.building, args.room_name, args.floor, args.capacity, args.room_type)
        print(f"{GREEN}✓{NC} Room {BOLD}{r.name}{NC} added (id={r.id})")

    elif args.cmd == "add-asset":
        a = fm.add_asset(args.room_id, args.name, args.asset_type,
                         args.serial, condition=args.condition, notes=args.notes)
        print(f"{GREEN}✓{NC} Asset {BOLD}{a.name}{NC} registered (id={a.id})")

    elif args.cmd == "status":
        st = fm.status()
        print(f"\n{BOLD}{BLUE}Facilities Management Status{NC}")
        for k, v in st.items():
            print(f"  {CYAN}{k}{NC}: {GREEN}{v}{NC}")

    elif args.cmd == "export":
        print(json.dumps(fm.export_data(), indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
