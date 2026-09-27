import anyio

from anyio import open_file
from sqlparse import split

from backend.common.exception import errors


async def parse_sql_script(filepath: str) -> list[str]:
    """
    Parse a SQL script

    :param filepath: script file path
    :return:
    """
    path = anyio.Path(filepath)
    if not await path.exists():
        raise errors.NotFoundError(msg='SQL script file does not exist')

    async with await open_file(filepath, encoding='utf-8') as f:
        contents = await f.read(1024)
        while additional_contents := await f.read(1024):
            contents += additional_contents

    statements = [s for s in split(contents) if s.strip() and not s.strip().startswith('--')]
    for statement in statements:
        stripped = statement.strip().lower()
        if not any(stripped.startswith(_) for _ in ['select', 'insert']):
            raise errors.RequestError(
                msg='The SQL script file contains an illegal operation; only SELECT and INSERT are allowed'
            )

    return statements
