import os

import uvicorn

if __name__ == '__main__':
    # Why this startup file is kept separate: https://stackoverflow.com/questions/64003384

    # DEBUG:
    # If you prefer debugging in your IDE, you can right-click and run this file directly in the IDE
    # If you prefer debugging via print statements, it's recommended to start the service via the fba CLI

    # Warning:
    # If you are starting this file via the python command, please follow these steps:
    # 1. Install dependencies via uv according to the official documentation
    # 2. Run the command from within the backend directory
    uvicorn.run(
        app='backend.main:app',
        host='127.0.0.1',
        port=28000,
        reload=True,
        reload_excludes=[os.path.abspath('../.venv')],
    )
