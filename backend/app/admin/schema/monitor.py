from pydantic import Field

from backend.common.schema import SchemaBase


class CpuInfo(SchemaBase):
    """CPU info"""

    physical_num: int = Field(description='Number of physical cores')
    logical_num: int = Field(description='Number of logical cores')
    max_freq: float = Field(description='Max frequency (MHz)')
    min_freq: float = Field(description='Min frequency (MHz)')
    current_freq: float = Field(description='Current frequency (MHz)')
    usage: float = Field(description='Usage (%)')


class MemInfo(SchemaBase):
    """Memory info"""

    total: float = Field(description='Total capacity (GB)')
    used: float = Field(description='Used (GB)')
    free: float = Field(description='Free (GB)')
    usage: float = Field(description='Usage (%)')


class SysInfo(SchemaBase):
    """System info"""

    name: str = Field(description='Hostname')
    os: str = Field(description='Operating system')
    ip: str = Field(description='IP address')
    arch: str = Field(description='System architecture')


class DiskInfo(SchemaBase):
    """Disk info"""

    dir: str = Field(description='Mount point')
    device: str = Field(description='Device name')
    type: str = Field(description='File system type')
    total: str = Field(description='Total capacity')
    used: str = Field(description='Used')
    free: str = Field(description='Free')
    usage: str = Field(description='Usage (%)')


class ServiceInfo(SchemaBase):
    """Service process info"""

    name: str = Field(description='Service name')
    version: str = Field(description='Version')
    home: str = Field(description='Install path')
    startup: str = Field(description='Startup time')
    elapsed: str = Field(description='Uptime')
    cpu_usage: str = Field(description='CPU usage')
    mem_vms: str = Field(description='Virtual memory')
    mem_rss: str = Field(description='Physical memory')
    mem_free: str = Field(description='Free memory')


class ServerMonitorInfo(SchemaBase):
    """Server monitoring info"""

    cpu: CpuInfo = Field(description='CPU info')
    mem: MemInfo = Field(description='Memory info')
    sys: SysInfo = Field(description='System info')
    disk: list[DiskInfo] = Field(description='Disk info')
    service: ServiceInfo = Field(description='Service info')


class RedisServerInfo(SchemaBase):
    """Redis server info"""

    redis_version: str = Field(description='Version')
    redis_mode: str = Field(description='Run mode')
    role: str = Field(description='Node role')
    tcp_port: str = Field(description='Listening port')
    uptime: str = Field(description='Uptime')
    connected_clients: str = Field(description='Number of connected clients')
    blocked_clients: str = Field(description='Number of blocked clients')
    used_memory_human: str = Field(description='Used memory')
    used_memory_rss_human: str = Field(description='RSS memory')
    maxmemory_human: str = Field(description='Max memory limit')
    mem_fragmentation_ratio: str = Field(description='Memory fragmentation ratio')
    instantaneous_ops_per_sec: str = Field(description='Operations per second')
    total_commands_processed: str = Field(description='Total commands processed')
    rejected_connections: str = Field(description='Number of rejected connections')
    keys_num: str = Field(description='Total number of keys')


class RedisCommandStat(SchemaBase):
    """Redis command stats"""

    name: str = Field(description='Command name')
    value: str = Field(description='Call count')


class RedisMonitorInfo(SchemaBase):
    """Redis monitoring info"""

    info: RedisServerInfo = Field(description='Server info')
    stats: list[RedisCommandStat] = Field(description='Command stats')
