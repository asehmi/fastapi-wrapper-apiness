import contextlib
import time
import threading
import uvicorn

class Server(uvicorn.Server):

    def __init__(self, app=None, host='127.0.0.1', port=8000, log_level='info'):
        if app is None:
            raise RuntimeError('Error: uvicorn.Server app must be supplied.')
        config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
        super().__init__(config)

    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


'''
# How to use:
# -----------

# Reference:
# https://stackoverflow.com/questions/61577643/how-to-use-fastapi-and-uvicorn-run-without-blocking-the-thread
# https://stackoverflow.com/questions/57412825/how-to-start-a-uvicorn-fastapi-in-background-when-testing-with-pytest
# -----------

from typing import Optional
from fastapi import FastAPI
import uvicorn

from utils.UvicornServer import Server

class FastAPI_MiniWrapper(FastAPI):

    def __init__(self) -> None:
        """
        Initializes a FastAPI instance that serves data from a CSV file.
        """
        print('Initializing FastAPI_Wrapper...')
        
        super().__init__()
        
        @self.get("/")
        def read_root():
            return {"Hello": "World"}

        @self.get("/items/{item_id}")
        def read_item(item_id: int, q: Optional[str] = None):
            return {"item_id": item_id, "q": q}


app = FastAPI_MiniWrapper()
config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
server = Server(config=config)

with server.run_in_thread():
    print('Server is started.')
    input('\n>>> Press Enter to stop...\n\n')
    # ...
    # Server will be stopped once code put here has completed
    # (The server's finally block will be run and main thread will be joined.)
    # ...

print('Server is stopped.')
'''
