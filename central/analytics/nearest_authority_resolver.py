"""
Nearest Responsible Authority Resolver for Emergency & Accident Incidents.

Provides spatial lookup for nearest emergency dispatch stations based on junction GPS:
- Traffic Police Beat Posts & ICCC Patrol Units
- Hospital Trauma Centers & 108 Emergency Ambulance Hubs
- Fire & Rescue Stations

Pluggable architecture: uses static spatial routing for Nagpur corridors,
which can be seamlessly swapped with live CAD (Computer-Aided Dispatch) APIs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import math


@dataclass
class AuthorityContact:
    station_name: str
    authority_type: str  # "TRAFFIC_POLICE" | "HOSPITAL_TRAUMA" | "FIRE_RESCUE"
    distance_km: float
    estimated_arrival_minutes: float
    contact_number: str
    dispatch_unit_callsign: str
    patrol_vehicle: str
    latitude: float
    longitude: float


@dataclass
class ResolvedAuthorities:
    junction_id: str
    primary_authority: AuthorityContact
    medical_authority: AuthorityContact
    fire_authority: Optional[AuthorityContact] = None


class BaseAuthorityResolver(ABC):
    @abstractmethod
    def resolve_nearest_authorities(self, junction_id: str, gps_coords: Optional[Dict[str, float]] = None) -> ResolvedAuthorities:
        pass


class StaticNagpurAuthorityResolver(BaseAuthorityResolver):
    """
    Pluggable spatial lookup table for Nagpur Wardha Road and arterial intersections.
    """

    NAGPUR_AUTHORITY_DIRECTORY: Dict[str, Dict[str, Any]] = {
        "NGP_J01_SITABULDI": {
            "police": AuthorityContact(
                station_name="Sitabuldi Traffic Police Division & ICCC Beat #1",
                authority_type="TRAFFIC_POLICE",
                distance_km=0.35,
                estimated_arrival_minutes=1.5,
                contact_number="+91-712-2561100",
                dispatch_unit_callsign="POLICE_PATROL_CHARLIE_01",
                patrol_vehicle="Mahindra Bolero Police Interceptor",
                latitude=21.1470,
                longitude=79.0890,
            ),
            "medical": AuthorityContact(
                station_name="Government Medical College & Hospital (GMCH) Trauma Hub",
                authority_type="HOSPITAL_TRAUMA",
                distance_km=1.8,
                estimated_arrival_minutes=3.2,
                contact_number="108 / +91-712-2744100",
                dispatch_unit_callsign="108_AMBULANCE_GMCH_01",
                patrol_vehicle="Advanced Life Support (ALS) Ambulance",
                latitude=21.1340,
                longitude=79.0980,
            ),
            "fire": AuthorityContact(
                station_name="Central Fire Station Civil Lines",
                authority_type="FIRE_RESCUE",
                distance_km=1.2,
                estimated_arrival_minutes=2.4,
                contact_number="101 / +91-712-2567777",
                dispatch_unit_callsign="FIRE_RESCUE_TENDER_01",
                patrol_vehicle="Heavy Water Tender Foam Crash Truck",
                latitude=21.1530,
                longitude=79.0810,
            ),
        },
        "NGP_J02_VARIETIES_SQ": {
            "police": AuthorityContact(
                station_name="Sitabuldi Metro Interchange Traffic Post",
                authority_type="TRAFFIC_POLICE",
                distance_km=0.20,
                estimated_arrival_minutes=1.0,
                contact_number="+91-712-2561102",
                dispatch_unit_callsign="METRO_BEAT_PATROL_02",
                patrol_vehicle="Police Two-Wheeler Quick Response Team",
                latitude=21.1420,
                longitude=79.0840,
            ),
            "medical": AuthorityContact(
                station_name="Care Hospital Emergency & Cardiac Care",
                authority_type="HOSPITAL_TRAUMA",
                distance_km=1.4,
                estimated_arrival_minutes=2.8,
                contact_number="108 / +91-712-3982222",
                dispatch_unit_callsign="108_AMBULANCE_CARE_02",
                patrol_vehicle="Cardiac Mobile ICU Ambulance",
                latitude=21.1380,
                longitude=79.0750,
            ),
            "fire": AuthorityContact(
                station_name="Central Fire Station Civil Lines",
                authority_type="FIRE_RESCUE",
                distance_km=1.5,
                estimated_arrival_minutes=3.0,
                contact_number="101 / +91-712-2567777",
                dispatch_unit_callsign="FIRE_RESCUE_TENDER_01",
                patrol_vehicle="Water Tender Fire Truck",
                latitude=21.1530,
                longitude=79.0810,
            ),
        },
        "NGP_J03_RAHATE_COLONY": {
            "police": AuthorityContact(
                station_name="Dhantoli Traffic Division Beat #4",
                authority_type="TRAFFIC_POLICE",
                distance_km=0.50,
                estimated_arrival_minutes=1.8,
                contact_number="+91-712-2422204",
                dispatch_unit_callsign="DHANTOLI_TRAFFIC_PATROL_04",
                patrol_vehicle="Police Rapid Interceptor",
                latitude=21.1310,
                longitude=79.0770,
            ),
            "medical": AuthorityContact(
                station_name="GMCH Nagpur Emergency Ingress Trauma Gate",
                authority_type="HOSPITAL_TRAUMA",
                distance_km=0.40,
                estimated_arrival_minutes=1.2,
                contact_number="108 / +91-712-2744100",
                dispatch_unit_callsign="108_AMBULANCE_GMCH_RAPID",
                patrol_vehicle="Advanced Trauma Mobile Unit",
                latitude=21.1320,
                longitude=79.0820,
            ),
            "fire": AuthorityContact(
                station_name="Cotton Market Fire Sub-Station",
                authority_type="FIRE_RESCUE",
                distance_km=2.1,
                estimated_arrival_minutes=4.2,
                contact_number="101 / +91-712-2728811",
                dispatch_unit_callsign="FIRE_TENDER_03",
                patrol_vehicle="Rescue Tender",
                latitude=21.1410,
                longitude=79.0930,
            ),
        },
        "NGP_J04_AJNI_SQ": {
            "police": AuthorityContact(
                station_name="Ajni Railway & Highway Traffic Post",
                authority_type="TRAFFIC_POLICE",
                distance_km=0.30,
                estimated_arrival_minutes=1.5,
                contact_number="+91-712-2251104",
                dispatch_unit_callsign="AJNI_HIGHWAY_PATROL_01",
                patrol_vehicle="Highway Patrol Interceptor",
                latitude=21.1190,
                longitude=79.0720,
            ),
            "medical": AuthorityContact(
                station_name="AIIMS Nagpur Emergency Medical Hub",
                authority_type="HOSPITAL_TRAUMA",
                distance_km=2.5,
                estimated_arrival_minutes=4.5,
                contact_number="108 / +91-712-2811100",
                dispatch_unit_callsign="108_AMBULANCE_AIIMS_01",
                patrol_vehicle="AIIMS Level-1 Trauma Ambulance",
                latitude=21.0850,
                longitude=79.0350,
            ),
            "fire": AuthorityContact(
                station_name="Narendra Nagar Fire Station",
                authority_type="FIRE_RESCUE",
                distance_km=1.8,
                estimated_arrival_minutes=3.6,
                contact_number="101 / +91-712-2289911",
                dispatch_unit_callsign="FIRE_TENDER_05",
                patrol_vehicle="Multipurpose Fire Tender",
                latitude=21.1080,
                longitude=79.0780,
            ),
        },
        "NGP_J05_CHHATRAPATI_SQ": {
            "police": AuthorityContact(
                station_name="Pratap Nagar Traffic Police Division",
                authority_type="TRAFFIC_POLICE",
                distance_km=0.60,
                estimated_arrival_minutes=2.0,
                contact_number="+91-712-2234405",
                dispatch_unit_callsign="PRATAP_NAGAR_PATROL_05",
                patrol_vehicle="Police Flying Squad Car",
                latitude=21.1080,
                longitude=79.0640,
            ),
            "medical": AuthorityContact(
                station_name="Orange City Hospital & Research Institute",
                authority_type="HOSPITAL_TRAUMA",
                distance_km=1.1,
                estimated_arrival_minutes=2.2,
                contact_number="108 / +91-712-6652000",
                dispatch_unit_callsign="108_AMBULANCE_OCHRI_01",
                patrol_vehicle="Critical Care Transport Ambulance",
                latitude=21.1140,
                longitude=79.0550,
            ),
            "fire": AuthorityContact(
                station_name="Narendra Nagar Fire Station",
                authority_type="FIRE_RESCUE",
                distance_km=2.2,
                estimated_arrival_minutes=4.0,
                contact_number="101 / +91-712-2289911",
                dispatch_unit_callsign="FIRE_TENDER_05",
                patrol_vehicle="Multipurpose Fire Tender",
                latitude=21.1080,
                longitude=79.0780,
            ),
        },
    }

    def resolve_nearest_authorities(self, junction_id: str, gps_coords: Optional[Dict[str, float]] = None) -> ResolvedAuthorities:
        data = self.NAGPUR_AUTHORITY_DIRECTORY.get(junction_id, self.NAGPUR_AUTHORITY_DIRECTORY["NGP_J01_SITABULDI"])
        return ResolvedAuthorities(
            junction_id=junction_id,
            primary_authority=data["police"],
            medical_authority=data["medical"],
            fire_authority=data.get("fire"),
        )


# Global singleton
authority_resolver: BaseAuthorityResolver = StaticNagpurAuthorityResolver()
