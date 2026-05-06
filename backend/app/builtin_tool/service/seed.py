"""系统内置工具种子数据：启动时自动注册所有系统工具（幂等）。"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.builtin_tool.crud.crud_builtin_tool import builtin_tool_dao
from backend.app.builtin_tool.model import BuiltinTool

log = logging.getLogger(__name__)

SYSTEM_TOOLS = [
    {
        'name': 'web_search',
        'display_name': '联网搜索',
        'description': (
            'Search the internet for current information. '
            'Use this when you need up-to-date information, facts, news, '
            'or any knowledge that might not be in your training data.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The search query to look up on the internet.',
                },
                'max_results': {
                    'type': 'integer',
                    'description': 'Maximum number of results to return (default: 5).',
                    'default': 5,
                },
            },
            'required': ['query'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'rag_retrieval',
        'display_name': '知识库检索',
        'description': (
            'Search the project knowledge base for relevant information. '
            'Use this when you need to look up specific facts, documents, '
            'or domain knowledge that might be stored in the knowledge base.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The search query to find relevant knowledge.',
                },
            },
            'required': ['query'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'calculate_distance',
        'display_name': '距离计算',
        'description': 'Calculate the Euclidean distance between two 3D positions on the battlefield.',
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'pos_a': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Position A as [x, y, z]'},
                'pos_b': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Position B as [x, y, z]'},
            },
            'required': ['pos_a', 'pos_b'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'assess_threats',
        'display_name': '威胁评估',
        'description': 'Analyze a situational report and assess threats for each friendly squad.',
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'situation_json': {'type': 'string', 'description': 'JSON string of the situation report'},
            },
            'required': ['situation_json'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'validate_orders',
        'display_name': '指令验证',
        'description': 'Validate a list of orders against known group IDs and valid command types.',
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'orders_json': {'type': 'string', 'description': 'JSON string of orders array'},
                'known_group_ids': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Valid group IDs'},
            },
            'required': ['orders_json', 'known_group_ids'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'get_squad_summary',
        'display_name': '小队查询',
        'description': 'Get a concise summary of a specific squad from the situation report.',
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'situation_json': {'type': 'string', 'description': 'JSON string of the situation report'},
                'group_id': {'type': 'string', 'description': 'Target group ID to query'},
            },
            'required': ['situation_json', 'group_id'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'generate_patrol_route',
        'display_name': '巡逻路线生成',
        'description': 'Generate a circular patrol route around a center point.',
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'center': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Center [x, y, z]'},
                'radius': {'type': 'number', 'description': 'Patrol radius in meters'},
                'num_points': {'type': 'integer', 'description': 'Number of waypoints (default: 4)'},
            },
            'required': ['center', 'radius'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'query_landmarks',
        'display_name': '查询地标',
        'description': 'Query landmarks near a position on the map within a given radius.',
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'position': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Center position [x, z]'},
                'radius': {'type': 'number', 'description': 'Search radius in meters'},
            },
            'required': ['position', 'radius'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'calculate_route',
        'display_name': '路线计算',
        'description': 'Calculate distance and road connectivity between two map positions.',
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'from_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Start position [x, z]'},
                'to_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'End position [x, z]'},
            },
            'required': ['from_pos', 'to_pos'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'get_terrain_profile',
        'display_name': '地形剖面',
        'description': 'Get terrain height profile between two positions on the map.',
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'from_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Start position [x, z]'},
                'to_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'End position [x, z]'},
                'samples': {'type': 'integer', 'description': 'Number of sample points (default: 10)', 'default': 10},
            },
            'required': ['from_pos', 'to_pos'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'get_area_intel',
        'display_name': '区域情报',
        'description': 'Get comprehensive intelligence about a map area: landmarks, zones, roads, terrain.',
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'position': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Center position [x, z]'},
                'radius': {'type': 'number', 'description': 'Area radius in meters'},
            },
            'required': ['position', 'radius'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'assess_threat_level',
        'display_name': '区域风险评估',
        'description': 'Assess risk level of a map area based on terrain, zone type, and landmarks.',
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'position': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Center position [x, z]'},
                'radius': {'type': 'number', 'description': 'Assessment radius in meters'},
            },
            'required': ['position', 'radius'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'view_map_image',
        'display_name': '查看地图图片',
        'description': 'Get map image URL and nearby landmarks for a specific area.',
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'position': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Center position [x, z]'},
                'zoom': {'type': 'number', 'description': 'Zoom level (default: 1.0)', 'default': 1.0},
            },
            'required': ['position'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'convert_coordinates',
        'display_name': '坐标转换',
        'description': 'Convert between world coordinates [x, z] and 6-digit military grid references.',
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'world_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'World coordinates [x, z]'},
                'grid_ref': {'type': 'string', 'description': '6-digit military grid reference'},
            },
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'plan_route',
        'display_name': '智能路径规划',
        'description': (
            'Plan an optimal movement route using A* pathfinding that considers terrain slope, '
            'water obstacles, and vegetation. Returns waypoints for unit movement.'
        ),
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'from_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Start position [x, z]'},
                'to_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'End position [x, z]'},
                'avoid_water': {'type': 'boolean', 'description': 'Avoid water obstacles (default: true)', 'default': True},
            },
            'required': ['from_pos', 'to_pos'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'get_terrain_summary',
        'display_name': '地形摘要',
        'description': (
            'Get a high-level terrain summary for the entire map divided into 9 macro-zones. '
            'Reports vegetation, trafficability, cover, slope, and water for each zone.'
        ),
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {},
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'get_mission_status',
        'display_name': '任务状态',
        'description': (
            'Get the current mission objective and status from the project Arma configuration. '
            'Returns the mission type, description, targets, and constraints. '
            'Only available for Arma-enabled projects.'
        ),
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'project_id': {'type': 'integer', 'description': 'Project ID'},
            },
            'required': ['project_id'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'estimate_travel_time',
        'display_name': '行军时间估算',
        'description': (
            'Estimate travel time between two positions considering distance, terrain, and road availability. '
            'Returns estimated time at different movement speeds.'
        ),
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'map_id': {'type': 'integer', 'description': 'Map ID'},
                'from_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Start position [x, z]'},
                'to_pos': {'type': 'array', 'items': {'type': 'number'}, 'description': 'End position [x, z]'},
            },
            'required': ['map_id', 'from_pos', 'to_pos'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'send_message_to_human',
        'display_name': '发送消息给指挥官',
        'description': (
            'Send a message to the human operator via the web interface. '
            'Use this to request clarification, report important events, or suggest changes.'
        ),
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'text': {'type': 'string', 'description': 'Message text to send to the human commander'},
            },
            'required': ['text'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'request_recon',
        'display_name': '请求侦察',
        'description': (
            'Mark an area as requiring reconnaissance. '
            'This flags the area for priority observation in subsequent decisions.'
        ),
        'category': 'arma',
        'input_schema': {
            'type': 'object',
            'properties': {
                'position': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Center of recon area [x, z]'},
                'radius': {'type': 'number', 'description': 'Recon radius in meters'},
                'reason': {'type': 'string', 'description': 'Why recon is needed'},
                'priority': {'type': 'string', 'enum': ['low', 'medium', 'high'], 'description': 'Recon priority'},
            },
            'required': ['position', 'reason'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'query_terrain_cells',
        'display_name': '地形智能检索',
        'description': (
            'Search terrain cells by location and/or natural language query. '
            'Uses H3 hexagonal grid pre-computed terrain features with semantic search.'
        ),
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'map_id': {'type': 'integer', 'description': 'Map ID'},
                'position': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Center position [x, z]'},
                'radius': {'type': 'number', 'description': 'Search radius in meters'},
                'query': {'type': 'string', 'description': 'Natural language terrain query'},
                'limit': {'type': 'integer', 'description': 'Max results'},
            },
            'required': ['map_id'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
    {
        'name': 'get_hex_neighbors',
        'display_name': '相邻地形查询',
        'description': (
            'Get terrain information for hexagonal cells adjacent to a position. '
            'Returns the center cell and all 6 neighbors.'
        ),
        'category': 'map',
        'input_schema': {
            'type': 'object',
            'properties': {
                'map_id': {'type': 'integer', 'description': 'Map ID'},
                'position': {'type': 'array', 'items': {'type': 'number'}, 'description': 'Position [x, z]'},
            },
            'required': ['map_id', 'position'],
        },
        'handler_type': 'python_builtin',
        'is_system': True,
        'is_active': True,
    },
]


async def seed_builtin_tools(db: AsyncSession) -> None:
    """确保系统内置工具存在于数据库中。幂等操作。"""
    for tool_data in SYSTEM_TOOLS:
        existing = await builtin_tool_dao.get_by_name(db, tool_data['name'])
        if existing:
            continue
        tool = BuiltinTool(**tool_data)
        db.add(tool)
        log.info(f'Seeded builtin tool: {tool_data["name"]}')

    await db.flush()
