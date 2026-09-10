"""Port reference data and a small ocean waypoint network.

The network exists so generated routes follow plausible sea lanes (Malacca,
Suez, Gibraltar, Cape of Good Hope, Panama) instead of drawing straight lines
across continents. Coordinates are approximate pilot-station positions and are
sufficient for a prototype, not for navigation.
"""

from __future__ import annotations

Coord = tuple[float, float]

PORTS: dict[str, dict] = {
    "Singapore": {"unlocode": "SGSIN", "coord": (1.264, 103.822), "country": "Singapore"},
    "Rotterdam": {"unlocode": "NLRTM", "coord": (51.949, 4.140), "country": "Netherlands"},
    "Antwerp": {"unlocode": "BEANR", "coord": (51.259, 4.400), "country": "Belgium"},
    "Hamburg": {"unlocode": "DEHAM", "coord": (53.541, 9.968), "country": "Germany"},
    "Algeciras": {"unlocode": "ESALG", "coord": (36.132, -5.437), "country": "Spain"},
    "Port Said": {"unlocode": "EGPSD", "coord": (31.256, 32.301), "country": "Egypt"},
    "Fujairah": {"unlocode": "AEFJR", "coord": (25.166, 56.383), "country": "UAE"},
    "Jebel Ali": {"unlocode": "AEJEA", "coord": (25.010, 55.060), "country": "UAE"},
    "Ras Tanura": {"unlocode": "SARTA", "coord": (26.644, 50.160), "country": "Saudi Arabia"},
    "Mumbai": {"unlocode": "INNSA", "coord": (18.949, 72.951), "country": "India"},
    "Durban": {"unlocode": "ZADUR", "coord": (-29.868, 31.030), "country": "South Africa"},
    "Houston": {"unlocode": "USHOU", "coord": (29.616, -94.985), "country": "United States"},
    "New York": {"unlocode": "USNYC", "coord": (40.600, -74.045), "country": "United States"},
    "Los Angeles": {"unlocode": "USLAX", "coord": (33.730, -118.262), "country": "United States"},
    "Santos": {"unlocode": "BRSSZ", "coord": (-23.988, -46.299), "country": "Brazil"},
    "Shanghai": {"unlocode": "CNSHA", "coord": (30.626, 122.063), "country": "China"},
    "Ningbo": {"unlocode": "CNNGB", "coord": (29.868, 121.951), "country": "China"},
    "Qingdao": {"unlocode": "CNTAO", "coord": (36.068, 120.320), "country": "China"},
    "Busan": {"unlocode": "KRPUS", "coord": (35.096, 129.041), "country": "South Korea"},
    "Yokohama": {"unlocode": "JPYOK", "coord": (35.443, 139.663), "country": "Japan"},
    "Dampier": {"unlocode": "AUDAM", "coord": (-20.658, 116.712), "country": "Australia"},
}

# Ocean waypoints. Nodes flagged as chokepoints are never laterally shifted by
# the weather-routing pass.
WAYPOINTS: dict[str, dict] = {
    "MALACCA_E": {"coord": (1.30, 104.30), "chokepoint": True},
    "MALACCA_W": {"coord": (5.60, 97.20), "chokepoint": True},
    "SCS_S": {"coord": (3.50, 106.50), "chokepoint": False},
    "SCS": {"coord": (14.00, 114.00), "chokepoint": False},
    "LUZON_STR": {"coord": (20.50, 121.00), "chokepoint": True},
    "ECS": {"coord": (30.00, 125.50), "chokepoint": False},
    "YELLOW_SEA": {"coord": (34.50, 123.00), "chokepoint": False},
    "JAPAN_S": {"coord": (33.50, 136.00), "chokepoint": False},
    "NW_PACIFIC": {"coord": (35.00, 155.00), "chokepoint": False},
    "MID_PACIFIC": {"coord": (36.00, -175.00), "chokepoint": False},
    "NE_PACIFIC": {"coord": (33.00, -135.00), "chokepoint": False},
    "PANAMA_PAC": {"coord": (7.50, -79.50), "chokepoint": True},
    "PANAMA_ATL": {"coord": (9.60, -79.00), "chokepoint": True},
    "BAY_BENGAL": {"coord": (6.00, 88.00), "chokepoint": False},
    "SRI_LANKA_S": {"coord": (4.80, 80.50), "chokepoint": False},
    "ARABIAN_SEA": {"coord": (11.00, 66.00), "chokepoint": False},
    "SOCOTRA": {"coord": (12.00, 54.00), "chokepoint": False},
    "GULF_OMAN": {"coord": (24.20, 58.80), "chokepoint": False},
    "HORMUZ": {"coord": (26.50, 56.50), "chokepoint": True},
    "ARAB_GULF": {"coord": (27.00, 51.50), "chokepoint": False},
    "ADEN": {"coord": (12.50, 45.50), "chokepoint": False},
    "BAB_EL_MANDEB": {"coord": (12.60, 43.40), "chokepoint": True},
    "RED_SEA_S": {"coord": (17.50, 40.00), "chokepoint": False},
    "RED_SEA_N": {"coord": (26.50, 34.80), "chokepoint": False},
    "SUEZ_S": {"coord": (29.50, 32.60), "chokepoint": True},
    "SUEZ_N": {"coord": (31.60, 32.40), "chokepoint": True},
    "EAST_MED": {"coord": (33.80, 27.00), "chokepoint": False},
    "CENTRAL_MED": {"coord": (36.00, 16.00), "chokepoint": False},
    "WEST_MED": {"coord": (37.50, 5.00), "chokepoint": False},
    "GIBRALTAR": {"coord": (35.95, -5.60), "chokepoint": True},
    "IBERIA_W": {"coord": (39.50, -10.50), "chokepoint": False},
    "BISCAY_W": {"coord": (45.50, -8.50), "chokepoint": False},
    "CHANNEL_W": {"coord": (49.30, -6.00), "chokepoint": True},
    "DOVER": {"coord": (50.90, 1.60), "chokepoint": True},
    "NORTH_SEA": {"coord": (52.40, 3.20), "chokepoint": False},
    "CANARY": {"coord": (25.00, -19.00), "chokepoint": False},
    "WAFR_W": {"coord": (10.00, -18.00), "chokepoint": False},
    "WAFR_N": {"coord": (2.00, -5.00), "chokepoint": False},
    "WAFR_S": {"coord": (-20.00, 5.00), "chokepoint": False},
    "CAPE_AGULHAS": {"coord": (-36.00, 20.00), "chokepoint": False},
    "SAFR_E": {"coord": (-31.00, 32.50), "chokepoint": False},
    "MADAGASCAR_E": {"coord": (-16.00, 55.00), "chokepoint": False},
    "INDIAN_C": {"coord": (-5.00, 85.00), "chokepoint": False},
    "SOUTH_INDIAN": {"coord": (-30.00, 62.00), "chokepoint": False},
    "INDIAN_SE": {"coord": (-25.00, 95.00), "chokepoint": False},
    "SUNDA_STR": {"coord": (-6.00, 105.50), "chokepoint": True},
    "NW_AUSTRALIA": {"coord": (-19.50, 114.00), "chokepoint": False},
    "ATL_EQ": {"coord": (2.00, -25.00), "chokepoint": False},
    "BRAZIL_E": {"coord": (-15.00, -33.00), "chokepoint": False},
    "SATL_W": {"coord": (-25.00, -40.00), "chokepoint": False},
    "ATL_MID_N": {"coord": (43.00, -40.00), "chokepoint": False},
    "ATL_NE": {"coord": (47.00, -17.00), "chokepoint": False},
    "NW_ATLANTIC": {"coord": (39.00, -70.00), "chokepoint": False},
    "BAHAMAS": {"coord": (26.00, -75.00), "chokepoint": False},
    "FLORIDA_STR": {"coord": (24.30, -80.80), "chokepoint": True},
    "GULF_MEXICO": {"coord": (26.50, -90.00), "chokepoint": False},
}

# Undirected sea lanes.
LANES: list[tuple[str, str]] = [
    # South East Asia
    ("MALACCA_E", "MALACCA_W"),
    ("MALACCA_E", "SCS_S"),
    ("SCS_S", "SCS"),
    ("SCS", "LUZON_STR"),
    ("SCS", "ECS"),
    ("LUZON_STR", "NW_PACIFIC"),
    ("ECS", "YELLOW_SEA"),
    ("ECS", "JAPAN_S"),
    ("JAPAN_S", "NW_PACIFIC"),
    ("SCS_S", "SUNDA_STR"),
    ("SUNDA_STR", "NW_AUSTRALIA"),
    ("SUNDA_STR", "INDIAN_C"),
    ("NW_AUSTRALIA", "INDIAN_SE"),
    ("INDIAN_SE", "SOUTH_INDIAN"),
    # Pacific
    ("NW_PACIFIC", "MID_PACIFIC"),
    ("MID_PACIFIC", "NE_PACIFIC"),
    ("NE_PACIFIC", "PANAMA_PAC"),
    ("PANAMA_PAC", "PANAMA_ATL"),
    ("PANAMA_ATL", "BAHAMAS"),
    # Indian Ocean
    ("MALACCA_W", "BAY_BENGAL"),
    ("BAY_BENGAL", "SRI_LANKA_S"),
    ("SRI_LANKA_S", "ARABIAN_SEA"),
    ("ARABIAN_SEA", "SOCOTRA"),
    ("ARABIAN_SEA", "GULF_OMAN"),
    ("GULF_OMAN", "HORMUZ"),
    ("HORMUZ", "ARAB_GULF"),
    ("SOCOTRA", "ADEN"),
    ("GULF_OMAN", "SOCOTRA"),
    ("ARABIAN_SEA", "MADAGASCAR_E"),
    ("ADEN", "BAB_EL_MANDEB"),
    ("MALACCA_W", "INDIAN_C"),
    ("INDIAN_C", "MADAGASCAR_E"),
    ("INDIAN_C", "SRI_LANKA_S"),
    ("MADAGASCAR_E", "SAFR_E"),
    ("MADAGASCAR_E", "SOUTH_INDIAN"),
    ("SOUTH_INDIAN", "CAPE_AGULHAS"),
    ("SAFR_E", "CAPE_AGULHAS"),
    ("SOCOTRA", "MADAGASCAR_E"),
    # Red Sea / Suez / Mediterranean
    ("BAB_EL_MANDEB", "RED_SEA_S"),
    ("RED_SEA_S", "RED_SEA_N"),
    ("RED_SEA_N", "SUEZ_S"),
    ("SUEZ_S", "SUEZ_N"),
    ("SUEZ_N", "EAST_MED"),
    ("EAST_MED", "CENTRAL_MED"),
    ("CENTRAL_MED", "WEST_MED"),
    ("WEST_MED", "GIBRALTAR"),
    # North East Atlantic
    ("GIBRALTAR", "IBERIA_W"),
    ("IBERIA_W", "BISCAY_W"),
    ("IBERIA_W", "CANARY"),
    ("BISCAY_W", "CHANNEL_W"),
    ("CHANNEL_W", "DOVER"),
    ("DOVER", "NORTH_SEA"),
    ("BISCAY_W", "ATL_NE"),
    ("ATL_NE", "ATL_MID_N"),
    ("ATL_MID_N", "NW_ATLANTIC"),
    ("ATL_NE", "IBERIA_W"),
    # West Africa / South Atlantic
    ("CANARY", "WAFR_W"),
    ("WAFR_W", "WAFR_N"),
    ("WAFR_N", "WAFR_S"),
    ("WAFR_S", "CAPE_AGULHAS"),
    ("CANARY", "ATL_EQ"),
    ("ATL_EQ", "WAFR_N"),
    ("ATL_EQ", "BRAZIL_E"),
    ("BRAZIL_E", "SATL_W"),
    ("BRAZIL_E", "WAFR_S"),
    # North West Atlantic / Gulf of Mexico
    ("NW_ATLANTIC", "BAHAMAS"),
    ("BAHAMAS", "FLORIDA_STR"),
    ("FLORIDA_STR", "GULF_MEXICO"),
    ("BAHAMAS", "ATL_EQ"),
]

# Which waypoint each port joins the network through.
PORT_ENTRIES: dict[str, list[str]] = {
    "Singapore": ["MALACCA_E", "SCS_S"],
    "Rotterdam": ["NORTH_SEA"],
    "Antwerp": ["NORTH_SEA"],
    "Hamburg": ["NORTH_SEA"],
    "Algeciras": ["GIBRALTAR"],
    "Port Said": ["SUEZ_N"],
    "Fujairah": ["GULF_OMAN"],
    "Jebel Ali": ["HORMUZ"],
    "Ras Tanura": ["ARAB_GULF"],
    "Mumbai": ["ARABIAN_SEA"],
    "Durban": ["SAFR_E"],
    "Houston": ["GULF_MEXICO"],
    "New York": ["NW_ATLANTIC"],
    "Los Angeles": ["NE_PACIFIC"],
    "Santos": ["SATL_W", "BRAZIL_E"],
    "Shanghai": ["ECS"],
    "Ningbo": ["ECS"],
    "Qingdao": ["YELLOW_SEA"],
    "Busan": ["ECS", "YELLOW_SEA"],
    "Yokohama": ["JAPAN_S"],
    "Dampier": ["NW_AUSTRALIA"],
}


def port_coord(name: str) -> Coord | None:
    entry = PORTS.get(name)
    return entry["coord"] if entry else None


def chokepoint_coords() -> list[Coord]:
    return [w["coord"] for w in WAYPOINTS.values() if w["chokepoint"]]
