"""LLM 服务商预设配置：常用服务商、模型、API 地址、定价信息。"""

LLM_PRESETS: list[dict] = [
    {
        'provider_type': 'deepseek',
        'label': 'DeepSeek',
        'api_base': 'https://api.deepseek.com/v1',
        'currency': 'USD',
        'models': [
            {
                'name': 'deepseek-chat',
                'label': 'DeepSeek V3 (Chat)',
                'context_length': 128000,
                'input_price': 0.28,
                'cached_input_price': 0.014,
                'output_price': 0.42,
            },
            {
                'name': 'deepseek-reasoner',
                'label': 'DeepSeek V3 (Reasoner)',
                'context_length': 128000,
                'input_price': 0.28,
                'cached_input_price': 0.014,
                'output_price': 0.42,
            },
        ],
    },
    {
        'provider_type': 'openai',
        'label': 'OpenAI',
        'api_base': 'https://api.openai.com/v1',
        'currency': 'USD',
        'models': [
            {
                'name': 'gpt-4o',
                'label': 'GPT-4o',
                'context_length': 128000,
                'input_price': 2.50,
                'cached_input_price': 1.25,
                'output_price': 10.00,
            },
            {
                'name': 'gpt-4o-mini',
                'label': 'GPT-4o Mini',
                'context_length': 128000,
                'input_price': 0.15,
                'cached_input_price': 0.075,
                'output_price': 0.60,
            },
            {
                'name': 'o3',
                'label': 'O3 (Reasoning)',
                'context_length': 200000,
                'input_price': 10.00,
                'cached_input_price': 5.00,
                'output_price': 40.00,
            },
            {
                'name': 'o3-mini',
                'label': 'O3 Mini (Reasoning)',
                'context_length': 200000,
                'input_price': 1.10,
                'cached_input_price': 0.55,
                'output_price': 4.40,
            },
            {
                'name': 'o1',
                'label': 'O1 (Reasoning)',
                'context_length': 200000,
                'input_price': 15.00,
                'cached_input_price': 7.50,
                'output_price': 60.00,
            },
        ],
    },
    {
        'provider_type': 'anthropic',
        'label': 'Anthropic',
        'api_base': 'https://api.anthropic.com',
        'currency': 'USD',
        'models': [
            {
                'name': 'claude-opus-4-6',
                'label': 'Claude Opus 4.6',
                'context_length': 200000,
                'input_price': 5.00,
                'cached_input_price': 2.50,
                'output_price': 25.00,
            },
            {
                'name': 'claude-sonnet-4-6',
                'label': 'Claude Sonnet 4.6',
                'context_length': 200000,
                'input_price': 3.00,
                'cached_input_price': 1.50,
                'output_price': 15.00,
            },
            {
                'name': 'claude-haiku-4-5',
                'label': 'Claude Haiku 4.5',
                'context_length': 200000,
                'input_price': 1.00,
                'cached_input_price': 0.50,
                'output_price': 5.00,
            },
        ],
    },
    {
        'provider_type': 'openai_compatible',
        'label': 'Google Gemini (OpenAI Compatible)',
        'api_base': 'https://generativelanguage.googleapis.com/v1beta/openai/',
        'currency': 'USD',
        'models': [
            {
                'name': 'gemini-2.0-flash',
                'label': 'Gemini 2.0 Flash',
                'context_length': 1000000,
                'input_price': 0.10,
                'output_price': 0.40,
            },
            {
                'name': 'gemini-2.0-flash-lite',
                'label': 'Gemini 2.0 Flash Lite',
                'context_length': 1000000,
                'input_price': 0.075,
                'output_price': 0.30,
            },
        ],
    },
    {
        'provider_type': 'openai_compatible',
        'label': '通义千问 / Qwen (百炼)',
        'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'currency': 'CNY',
        'models': [
            {
                'name': 'qwen-max',
                'label': 'Qwen Max',
                'context_length': 32768,
                'input_price': 20.00,
                'output_price': 60.00,
            },
            {
                'name': 'qwen-plus',
                'label': 'Qwen Plus',
                'context_length': 131072,
                'input_price': 0.80,
                'output_price': 2.00,
            },
            {
                'name': 'qwen-turbo',
                'label': 'Qwen Turbo',
                'context_length': 1000000,
                'input_price': 0.30,
                'output_price': 0.60,
            },
        ],
    },
    {
        'provider_type': 'openai_compatible',
        'label': 'Moonshot / Kimi',
        'api_base': 'https://api.moonshot.cn/v1',
        'currency': 'CNY',
        'models': [
            {
                'name': 'kimi-k2.5',
                'label': 'Kimi K2.5',
                'context_length': 262144,
                'input_price': 3.24,
                'output_price': 15.84,
            },
            {
                'name': 'kimi-k2-0905',
                'label': 'Kimi K2',
                'context_length': 131072,
                'input_price': 2.88,
                'output_price': 14.40,
            },
        ],
    },
    {
        'provider_type': 'openai_compatible',
        'label': 'OpenRouter (中转聚合)',
        'api_base': 'https://openrouter.ai/api/v1',
        'currency': 'USD',
        'models': [
            {
                'name': 'anthropic/claude-sonnet-4.6',
                'label': 'Claude Sonnet 4.6 (via OpenRouter)',
                'context_length': 200000,
                'input_price': 3.00,
                'output_price': 15.00,
            },
            {
                'name': 'openai/gpt-4o',
                'label': 'GPT-4o (via OpenRouter)',
                'context_length': 128000,
                'input_price': 2.50,
                'output_price': 10.00,
            },
            {
                'name': 'deepseek/deepseek-chat',
                'label': 'DeepSeek Chat (via OpenRouter)',
                'context_length': 128000,
                'input_price': 0.32,
                'output_price': 0.89,
            },
            {
                'name': 'google/gemini-2.0-flash',
                'label': 'Gemini 2.0 Flash (via OpenRouter)',
                'context_length': 1000000,
                'input_price': 0.10,
                'output_price': 0.40,
            },
        ],
    },
    {
        'provider_type': 'openai_compatible',
        'label': 'API易 / Apiyi (中转)',
        'api_base': 'https://api.apiyi.com/v1',
        'currency': 'CNY',
        'models': [
            {
                'name': 'gpt-4o',
                'label': 'GPT-4o (中转)',
                'context_length': 128000,
                'input_price': 18.00,
                'output_price': 72.00,
            },
            {
                'name': 'claude-sonnet-4-6',
                'label': 'Claude Sonnet 4.6 (中转)',
                'context_length': 200000,
                'input_price': 21.60,
                'output_price': 108.00,
            },
        ],
    },
    {
        'provider_type': 'openai_compatible',
        'label': 'One API / New API (自建中转)',
        'api_base': 'http://localhost:3000/v1',
        'currency': 'USD',
        'models': [
            {
                'name': 'gpt-4o',
                'label': 'GPT-4o',
                'context_length': 128000,
                'input_price': 2.50,
                'output_price': 10.00,
            },
            {
                'name': 'claude-sonnet-4-6',
                'label': 'Claude Sonnet 4.6',
                'context_length': 200000,
                'input_price': 3.00,
                'output_price': 15.00,
            },
            {
                'name': 'deepseek-chat',
                'label': 'DeepSeek Chat',
                'context_length': 128000,
                'input_price': 0.28,
                'output_price': 0.42,
            },
        ],
    },
    {
        'provider_type': 'ollama',
        'label': 'Ollama (本地)',
        'api_base': 'http://localhost:11434',
        'currency': 'USD',
        'models': [
            {
                'name': 'llama3.3',
                'label': 'Llama 3.3 70B',
                'context_length': 128000,
                'input_price': 0,
                'output_price': 0,
            },
            {
                'name': 'qwen2.5',
                'label': 'Qwen 2.5',
                'context_length': 128000,
                'input_price': 0,
                'output_price': 0,
            },
            {
                'name': 'deepseek-r1',
                'label': 'DeepSeek R1',
                'context_length': 128000,
                'input_price': 0,
                'output_price': 0,
            },
        ],
    },
]


def get_pricing_map() -> dict[str, dict]:
    """构建 (provider_type, model_name) -> pricing 的快速查找表。"""
    result: dict[str, dict] = {}
    for preset in LLM_PRESETS:
        for model in preset['models']:
            key = f"{preset['provider_type']}:{model['name']}"
            result[key] = {
                'input_price': model['input_price'],
                'cached_input_price': model.get('cached_input_price', model['input_price'] * 0.5),
                'output_price': model['output_price'],
                'currency': preset['currency'],
            }
    return result
