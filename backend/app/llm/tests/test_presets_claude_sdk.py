from backend.app.llm.presets import LLM_PRESETS, get_pricing_map

CLAUDE_SDK_MODEL_NAMES = ['claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5', 'claude-fable-5-1']


def _claude_sdk_preset() -> dict:
    presets = [preset for preset in LLM_PRESETS if preset['provider_type'] == 'claude_sdk']
    assert len(presets) == 1, 'expected exactly one claude_sdk preset'
    return presets[0]


def test_claude_sdk_preset_lists_the_subscription_models() -> None:
    preset = _claude_sdk_preset()

    assert preset['label'] == 'Claude (Subscription)'
    assert [model['name'] for model in preset['models']] == CLAUDE_SDK_MODEL_NAMES


def test_claude_sdk_preset_has_no_api_base() -> None:
    assert len(_claude_sdk_preset()['api_base']) == 0


def test_claude_sdk_preset_prices_are_zero_because_billing_is_by_subscription() -> None:
    for model in _claude_sdk_preset()['models']:
        assert model['input_price'] == 0, model['name']
        assert model['cached_input_price'] == 0, model['name']
        assert model['output_price'] == 0, model['name']


def test_pricing_map_contains_zero_priced_claude_sdk_haiku() -> None:
    pricing = get_pricing_map()

    assert 'claude_sdk:claude-haiku-5-5' in pricing
    assert pricing['claude_sdk:claude-haiku-5-5'] == {
        'input_price': 0,
        'cached_input_price': 0,
        'output_price': 0,
        'currency': 'USD',
    }
