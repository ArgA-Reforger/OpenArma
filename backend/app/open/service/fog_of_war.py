"""Fog of War — filter a full battle snapshot to a single faction's perspective.

Each LLM-controlled faction only sees:
- Own groups/units: full data (position, members, ammo, orders, etc.)
- Enemy groups/units: ONLY what own groups have detected via known_enemies
- Own vehicles: full data
- Enemy vehicles: only if detected by own groups
- Events: only events involving own faction or observed enemies
"""

from __future__ import annotations

from typing import Any


def filter_for_faction(
    snapshot_data: dict[str, Any],
    my_faction: str,
    all_sides: list[dict],
) -> dict[str, Any]:
    """Build a faction-specific view of the battlefield.

    Args:
        snapshot_data: Full situation data from the mod heartbeat.
        my_faction: The faction key this LLM controls (e.g. 'US').
        all_sides: All configured sides for context.

    Returns:
        Filtered data containing only what this faction can see.
    """
    groups = snapshot_data.get('groups', [])
    units = snapshot_data.get('units', [])
    vehicles = snapshot_data.get('vehicles', [])
    events = snapshot_data.get('events', [])
    markers = snapshot_data.get('markers', [])

    my_groups = [g for g in groups if g.get('faction') == my_faction]
    my_group_ids = {g.get('id') for g in my_groups if g.get('id')}

    my_units = [u for u in units if u.get('faction') == my_faction]
    my_vehicles = [v for v in vehicles if v.get('faction') == my_faction]

    detected_enemies = _collect_detected_enemies(my_groups)

    detected_entity_ids = {e.get('entity_id') for e in detected_enemies if e.get('entity_id')}

    detected_enemy_vehicles = [
        _sanitize_vehicle(v) for v in vehicles
        if v.get('faction') != my_faction and v.get('entity_id') in detected_entity_ids
    ]

    visible_events = [
        e for e in events
        if _is_event_visible(e, my_faction, my_group_ids, detected_entity_ids)
    ]

    return {
        'game_state': snapshot_data.get('game_state', {}),
        'groups': my_groups,
        'units': my_units,
        'vehicles': my_vehicles + detected_enemy_vehicles,
        'detected_enemies': detected_enemies,
        'events': visible_events,
        'markers': markers,
        'human_messages': snapshot_data.get('human_messages', []),
        'timestamp': snapshot_data.get('timestamp', 0),
        'request_id': snapshot_data.get('request_id', 0),
        'priority': snapshot_data.get('priority', 'normal'),
    }


def _collect_detected_enemies(my_groups: list[dict]) -> list[dict]:
    """Extract all detected enemies from own groups' known_enemies lists."""
    seen_ids: set[str] = set()
    result: list[dict] = []

    for g in my_groups:
        group_id = g.get('id', '')
        group_faction = g.get('faction', '')
        enemies = g.get('known_enemies', [])
        if not isinstance(enemies, list):
            continue

        for e in enemies:
            eid = e.get('entity_id', '')
            key = eid or f"{e.get('position', [])}"
            if key in seen_ids:
                continue
            seen_ids.add(key)

            result.append({
                'observer_group_id': group_id,
                'observer_faction': group_faction,
                'entity_id': eid,
                'position': e.get('position', []),
                'detected_position': e.get('detected_position', []),
                'distance': e.get('distance', -1),
                'time_since_seen': e.get('time_since_seen', 999),
                'time_since_detected': e.get('time_since_detected', 999),
                'time_since_side_recognized': e.get('time_since_side_recognized', 9999),
                'time_since_type_recognized': e.get('time_since_type_recognized', 9999),
                'time_since_endangered': e.get('time_since_endangered', 9999),
                'unit_type': e.get('unit_type', 'unknown'),
                'is_disarmed': e.get('is_disarmed', False),
                'perceived_faction': e.get('perceived_faction', 'unknown'),
            })

    return result


def _sanitize_vehicle(v: dict) -> dict:
    """Strip sensitive details from an enemy vehicle — only expose what's observable."""
    return {
        'entity_id': v.get('entity_id', ''),
        'position': v.get('position', []),
        'faction': v.get('faction', 'unknown'),
        'type': v.get('type', 'unknown'),
    }


def _is_event_visible(
    event: dict,
    my_faction: str,
    my_group_ids: set[str],
    detected_entity_ids: set[str],
) -> bool:
    """Determine if an event is visible to this faction."""
    victim_faction = event.get('victim_faction', '')
    killer_faction = event.get('killer_faction', '')
    if victim_faction == my_faction or killer_faction == my_faction:
        return True

    victim_id = event.get('victim_id', '')
    killer_id = event.get('killer_id', '')
    if victim_id in detected_entity_ids or killer_id in detected_entity_ids:
        return True

    return False
