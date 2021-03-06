"""
Simple bootstrapper intended to be used used to start the API as a daemon process
with routes supplied from a config database.
"""
import sys
import uvicorn

from fastapi_wrapper.fastapi_wrapper import FastAPI_Wrapper

def stand_up(config_db='routes_config.db', host='127.0.0.1', port=8000):
    app = FastAPI_Wrapper(init_routes_with_config_db=True, config_db=config_db)
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    stand_up(config_db=sys.argv[1], host=sys.argv[2], port=int(sys.argv[3]))
