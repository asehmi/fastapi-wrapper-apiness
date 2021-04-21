from fastapi_wrapper import cli

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

        cli.main(database='test', data_path='./test.csv', data_format='CSV', start_server=False, if_exists='replace', host='localhost', port=8000)
        # cli.main(database='gcfs', data_path='./GCFS Countries.xlsx', data_format='XLSX', host='localhost', port=8001)

class FastAPIRouterTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testFastAPIWrapper(self):
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


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(FastAPIWrapperTests)
    # suite = unittest.TestLoader().loadTestsFromTestCase(FastAPIRouterTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
    #unittest.main()

