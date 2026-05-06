"""战场状态机：peaceful → engaged → critical.

基于后端规则判定（零延迟），不经过 LLM。
状态跃迁才是紧急，持续状态不是。
"""

import logging
import time

from backend.database.redis import redis_client

log = logging.getLogger(__name__)

STATE_PREFIX = 'arma:battle_state:'
STATE_TTL = 7200

PEACEFUL = 'peaceful'
ENGAGED = 'engaged'
CRITICAL = 'critical'

DISENGAGE_ROUNDS = 3


def _state_key(conversation_id: str) -> str:
    return f'{STATE_PREFIX}{conversation_id}'


async def get_state(conversation_id: str) -> dict:
    """Get current battle state. Returns dict with state, last_change, rounds_no_contact."""
    raw = await redis_client.hgetall(_state_key(conversation_id))
    if not raw:
        return {
            'state': PEACEFUL,
            'last_change': time.time(),
            'rounds_no_contact': 0,
            'previous_enemies': 0,
        }
    return {
        'state': raw.get('state', PEACEFUL),
        'last_change': float(raw.get('last_change', time.time())),
        'rounds_no_contact': int(raw.get('rounds_no_contact', 0)),
        'previous_enemies': int(raw.get('previous_enemies', 0)),
    }


async def _set_state(conversation_id: str, state_data: dict) -> None:
    key = _state_key(conversation_id)
    await redis_client.hset(key, mapping={k: str(v) for k, v in state_data.items()})
    await redis_client.expire(key, STATE_TTL)


async def evaluate(conversation_id: str, situation_data: dict) -> dict:
    """Evaluate situation and return priority assessment.

    Returns dict with:
      - priority: 'normal' or 'critical'
      - state: current battle state after evaluation
      - transition: state change description or None
    """
    current = await get_state(conversation_id)
    old_state = current['state']

    groups = situation_data.get('groups', [])
    total_enemies = 0
    total_casualties = 0
    squad_destroyed = False

    for g in groups:
        ke = g.get('known_enemies', 0)
        total_enemies += len(ke) if isinstance(ke, list) else (ke if isinstance(ke, (int, float)) else 0)
        strength = g.get('strength', {})
        casualties = strength.get('casualties', 0)
        active = strength.get('active', 0)
        total_casualties += casualties
        if isinstance(active, int) and active == 0 and isinstance(casualties, int) and casualties > 0:
            squad_destroyed = True

    prev_enemies = current['previous_enemies']
    new_state = old_state
    priority = 'normal'
    transition = None

    if old_state == PEACEFUL:
        if total_enemies > 0 and prev_enemies == 0:
            new_state = CRITICAL
            priority = 'critical'
            transition = f'{PEACEFUL} → {CRITICAL}: first enemy contact ({total_enemies} enemies)'
        elif total_enemies > 0:
            new_state = ENGAGED
            transition = f'{PEACEFUL} → {ENGAGED}: enemies present'

    elif old_state == ENGAGED:
        if squad_destroyed:
            new_state = CRITICAL
            priority = 'critical'
            transition = f'{ENGAGED} → {CRITICAL}: squad destroyed'
        elif total_enemies == 0:
            rounds_no = current['rounds_no_contact'] + 1
            if rounds_no >= DISENGAGE_ROUNDS:
                new_state = PEACEFUL
                transition = f'{ENGAGED} → {PEACEFUL}: no contact for {rounds_no} rounds'
            current['rounds_no_contact'] = rounds_no
        else:
            current['rounds_no_contact'] = 0

    elif old_state == CRITICAL:
        if total_enemies == 0:
            rounds_no = current['rounds_no_contact'] + 1
            if rounds_no >= DISENGAGE_ROUNDS:
                new_state = PEACEFUL
                transition = f'{CRITICAL} → {PEACEFUL}: threat cleared after {rounds_no} rounds'
            current['rounds_no_contact'] = rounds_no
        elif not squad_destroyed and total_enemies <= prev_enemies:
            new_state = ENGAGED
            transition = f'{CRITICAL} → {ENGAGED}: situation stabilized'
        current['rounds_no_contact'] = 0 if total_enemies > 0 else current.get('rounds_no_contact', 0)

    if new_state != old_state:
        current['last_change'] = time.time()
        log.info('Battle state transition for conv=%s: %s', conversation_id, transition)

    current['state'] = new_state
    current['previous_enemies'] = total_enemies
    await _set_state(conversation_id, current)

    return {
        'priority': priority,
        'state': new_state,
        'transition': transition,
    }


async def reset(conversation_id: str) -> None:
    """Reset battle state (on logout)."""
    key = _state_key(conversation_id)
    await redis_client.delete(key)
