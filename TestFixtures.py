from fastapi_wrapper import cli
import json

import unittest # https://docs.python.org/2/library/unittest.html

class FastAPIWrapperTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testFastAPIWrapper(self):
        '''
        ### Test FastAPI Wrapper
        '''
        print('### FastAPI Wrapper Test')

        # -- Default routes config --
        # cli.main(init_routes_with_config_db=True, start_server=False, host='localhost', port=8000)

        # -- Named routes config --
        # cli.main(config_db='routes_config.db', init_routes_with_config_db=True, start_server=False, host='localhost', port=8000)
        cli.main(config_db='apiness_routes_config_TEST.db', init_routes_with_config_db=True, start_server=False, host='localhost', port=8000)

        # -- In-memory db + server start --
        # cli.main(database=':memory:', data_path='./data/test.csv', data_format='CSV', start_server=True, if_exists='replace', host='localhost', port=8000)

        # -- Database creation --
        # cli.main(database='test', data_path='./data/test.csv', data_format='CSV', start_server=False, if_exists='replace', host='localhost', port=8000)
        # cli.main(database='gcfs', data_path='./data/GCFS Countries.xlsx', data_format='XLSX', host='localhost', port=8001)

class FastAPIRouterTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testFastAPIRouter(self):
        '''
        ### Test FastAPI Router
        '''
        print('### FastAPI Router Test')


        # /routers/my_router.py
        from fastapi import APIRouter

        router = APIRouter()

        @router.get("/some")
        @router.get("/someone")
        @router.get("/<path:path>")
        async def some_path(**kwargs):
            pass

        @router.get("/path")
        async def some_other_path(**kwargs):
            pass

        @router.post("/some_post_path")
        async def some_post_path(**kwargs):
            pass

        # /main.py
        # from routers import my_router
        from fastapi import FastAPI
        import uvicorn

        app = FastAPI()

        app.include_router(
            # my_router.router,
            router,
            prefix="/custom_path",
            tags=["Endpoints in my router!"],
        )

        uvicorn.run(app, host='localhost', port=9090)

class FastAPIMultiprocessTests(unittest.TestCase):

    def setUp(self):
        from fastapi import FastAPI

        class FastAPI_MiniWrapper(FastAPI):

            def __init__(self) -> None:
                """
                Initializes a FastAPI instance that serves data from a CSV file.
                """
                print('Initializing FastAPI_Wrapper...')
                
                super().__init__()
                
                from typing import Optional

                @self.get("/shutdown")
                async def shutdown():
                    # Add shutdown event (would only be of any use in a multi-process, not multi-thread situation)
                    import os
                    import time
                    import psutil
                    import threading

                    def suicide():
                        time.sleep(1)

                        # parent = psutil.Process(psutil.Process(os.getpid()).ppid())
                        # parent.kill()

                        myself = psutil.Process(os.getpid())
                        myself.kill()

                    threading.Thread(target=suicide, daemon=True).start()
                    print(f'>>> Successfully killed API <<<')
                    return {"success": True}        

                self.on_event('shutdown')(shutdown)

                @self.get("/")
                def read_root():
                    return {"Hello": "World"}

                @self.get("/items/{item_id}")
                def read_item(item_id: int, q: Optional[str] = None):
                    return {"item_id": item_id, "q": q}

                # Pickle/Dill hook
                def __getstate__(self):
                    # this method is called when you are
                    # going to pickle the class, to know what to pickle
                    state = self.__dict__.copy()
                    
                    # don't pickle the parameter openapi. otherwise will raise 
                    # AttributeError: Can't pickle local object 'FastAPI.setup.<locals>.openapi'
                    # E.g.
                    # del state['openapi']
                    # 
                    # See here for further inspiration: https://gist.github.com/aryzhov/067ecc12d39715217d787896a34915c6
                    
                    def do_something(val):
                        return val

                    for k, v in state.items():
                        if type(v) not in {int, float, str, tuple, None}:
                            state[k] = do_something(v)

                    return state
                
                # Pickle/Dill hook
                def __setstate__(self, state):
                    self.__dict__.update(state)


                # Pickle/Dill hook
                def __setstate__(self, state):

                    def do_something(state):
                        return state

                    ustate = do_something(state)

                    self.__dict__.update(ustate)


        self.app = FastAPI_MiniWrapper()

    def tearDown(self):
        pass

    # NOTE! Can't get this forked process to work since the FastAPI_Wrapper has nested
    # classes and methods which can't be serialized / pickled, so must use multi-threading :-(
    # (See:https://medium.com/@jwnx/multiprocessing-serialization-in-python-with-pickle-9844f6fa1812)
    def HIDDEN_testFastAPIProcessFork(self):
        '''
        ### Test FastAPI Process Fork
        '''
        print('### FastAPI Process Fork Test')

        import os
        from multiprocessing import Process
        import uvicorn
        import time
        import dill as pickle

        # A little check here to try to fix the pickle issues
        # Pickling will invoke the __getstate__, __setstate__ hooks
        # where the pickle state can be modified
        filepath = os.path.join('./pickle', f'fastapi-wrapper.pkl')
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self.app, f)
            with open(filepath, 'rb') as f:
                self.app = pickle.load(f)
        except Exception as e:
            print(f'Error - got into a pickle! {e}')

        proc = Process( target=uvicorn.run,
                        args=(self.app,),
                        kwargs={
                            'host': '127.0.0.1',
                            'port': 6000,
                            'log_level': 'info'
                        },
                        daemon=True )
        proc.start()
        time.sleep(1.0)  # time for the server to start

    # NOTE! This blocks so shouldn't really use in test suite
    def HIDDEN_testFastAPIThread(self):
        '''
        ### Test FastAPI Thread
        '''
        print('### FastAPI Thread Test')

        import threading
        import uvicorn


        # BLOCKING
        def thread_runner(app, host, port):
            uvicorn.run(app, host=host, port=port)

        thread_name = 'testFastAPIThread'
        print(f'>>> Starting {thread_name} <<<')

        thread = threading.Thread(name=thread_name, target=thread_runner, args=(self.app, '127.0.0.1', 7000))
        thread.start()

    def HIDDEN_testFastAPIStoppableThread(self):
        '''
        ### Test FastAPI StoppableThread
        '''
        print('### FastAPI StoppableThread Test')

        from utils.UvicornServer import Server

        server = Server(app=self.app, host='127.0.0.1', port=8000, log_level='info')

        # BLOCKING + AUTO-TERMINATING
        with server.run_in_thread():
            print('Server is started.')
            input('\n>>> Press Enter to stop...\n\n')
            # ...
            # Server will be stopped once code put here is completed
            # ...

        print('Server is stopped.')

    # WARNING: Run this test in the debugger
    # Terminate the job by calling /shutdown api
    def testFastAPIJobBootstrapper(self):
        '''
        ### Test FastAPI Job Bootstrapper
        '''
        print('### FastAPI Job Bootstraapper Test')

        import os
        import subprocess
        import threading
        import requests
        import time

        def run(job):
            print (f"\nRunning job: {job}\n")
            proc = subprocess.Popen(job)
            proc.wait()
            return proc

        def start_shutdown_thread(delay):
            def shutdown(delay):
                print (f"Sleeping for {delay} secs before shutdown...")
                time.sleep(delay)
                requests.get('http://127.0.0.1:8000/shutdown')

            thread = threading.Thread(target=shutdown, args=(delay,), daemon=True)
            thread.start()


        job = ['python', os.path.join('./', 'bootstrapper.py'), 'routes_config.db', '127.0.0.1', '8000']

        ### BLOCKING SERVER ###

        # start shutdown thread
        start_shutdown_thread(10)

        # THE MAIN THREAD WILL BLOCK (must be killed via /shutdown API call)
        run(job)


        ### NON-BLOCKING SERVER ###

        # start shutdown thread
        start_shutdown_thread(10)

        # NON-BLOCKING - THE MAIN THREAD WILL NOT BLOCK (the process will end when the test ends)
        thread = threading.Thread(name='FastAPI-Bootstrapper', target=run, args=(job,), daemon=True)
        thread.start()

        # we can wait for server to start, and then...
        time.sleep(5)
        # ...make a web request
        response = requests.get('http://127.0.0.1:8000/test/test?cmd=LIMIT%203')
        print(response.text)

        # this waits for the thread to end (i.e. when it's killed by the shutdown thread!)
        thread.join()


class MiscTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def HIDE_testRandom(self):
        '''
        ### Test Misc
        '''
        print('### Misc Test')

        from flatten_dict import flatten, unflatten
        from flatten_dict.reducer import make_reducer
        from flatten_dict.splitter import make_splitter
        from pprint import pprint

        state = {'a': {'b': {'c': 1, 'd': {'e': 2}, 'f': [3, 4, 5, {'g': {'h': 6}}]}}}
        pprint(state)
        fstate = flatten(state, reducer=make_reducer(delimiter='.'))
        pprint(fstate)
        state = unflatten(fstate, splitter=make_splitter(delimiter='.'))
        pprint(state)

    def testRoutesConfigDb(self):
        '''
        ### Test Routes Config
        '''
        print('### Misc Routes Config')

        from fastapi_wrapper.fastapi_wrapper import query_database

        routes = query_database('routes_config.db', 'select route_path from routes_config')
        print(routes)
        for route in routes:
            route_path = route['route_path']
            print(route_path)

            route_name = query_database('routes_config.db', f'select route_name from routes_config where route_path="{route_path}"')
            print(route_name[0]['route_name'])

            route_tags_json = query_database('routes_config.db', f'select route_tags from routes_config where route_path="{route_path}"')
            route_tags = json.loads(route_tags_json[0]['route_tags'])
            print(route_tags)

            query_params_json = query_database('routes_config.db', f'select query_params from routes_config where route_path="{route_path}"')
            query_params = json.loads(query_params_json[0]['query_params'])
            for query_param in query_params:
                qp = query_param[1]
                type_ = str if query_param[2] == 'str' else (float if query_param[2] == 'float' else int)
                print(f'{qp} / {type_}')


if __name__ == '__main__':
    # suite = unittest.TestLoader().loadTestsFromTestCase(MiscTests)
    # suite = unittest.TestLoader().loadTestsFromTestCase(FastAPIMultiprocessTests)
    suite = unittest.TestLoader().loadTestsFromTestCase(FastAPIWrapperTests)
    # suite = unittest.TestLoader().loadTestsFromTestCase(FastAPIRouterTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
    #unittest.main()

