from fastapi_wrapper.fastapi_wrapper import FastAPI_Wrapper
import os
import threading
from concurrent import futures
import time
import streamlit as st
import pandas as pd
import uvicorn
import requests
from random import randint
import logging

from data import csv_to_df, excel_to_df

from utils.LayoutAndStyleUtils import (Grid, Cell, BlockContainerStyler)
BlockContainerStyler().set_default_block_container_style()

try:
    import ptvsd
    ptvsd.enable_attach(address=('localhost', 6789))
    # ptvsd.wait_for_attach() # Only include this line if you always want to manually attach the debugger
except:
    # Ignore... for Heroku deployments!
    pass

# --------------------------------------------------------------------------------

# NOTE! Must be False. We can't use forked processes since the FastAPI_Wrapper has nested
# classes and methods which can't be serialized / pickled, so for now we're stuck with multi-threading :-(
# (See:https://medium.com/@jwnx/multiprocessing-serialization-in-python-with-pickle-9844f6fa1812)
USE_MULTIPROCESSING = False

from utils import SessionState
# Session State variables:
state = SessionState.get(
    message='To use this application, please login...',
    token={'value': None, 'expiry': None},
    user=None,
    email=None,
    report=[],

    FILE_UPLOADER_KEY = str(randint(1000,9999)),

    API_APP = None,
    API_INFO={}, # {'db#tbl': {'api_base_url': url, 'database': db, 'table': tbl, 'host': host, 'port': port}, ...}
    API_HOST='127.0.0.1',
    API_PORT=8000,
    API_THREAD_OR_PROC=None,
    API_STARTED=False,
)

# --------------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format='(%(threadName)-10s) %(message)s',
)

# --------------------------------------------------------------------------------

def main():
    st.title('APINESS')
    st.write('Apiness is being open... upload and convert Excel data files into API endpoints and backing SQLite databases!')

    if state.API_APP is None:
        print('>>> Creating new FastAPI_Wrapper <<<')
        
        # Need to put this import here otherwise it gets reloaded in Streamlit's reruns
        # and messes up registration of routes which are dynamically created
        from fastapi_wrapper.fastapi_wrapper import FastAPI_Wrapper

        app = FastAPI_Wrapper()
        state.API_APP = app

    app = state.API_APP

    # STEP 1: UPLOAD FILES AND GET DATABASE INFO
    if not state.API_STARTED:
        st.markdown('## \U0001F4C2 Upload data files')
        st.write('Upload one or more Excel data files. Duplicate files and files already processed will be ignored.')
        excel_files =  st.file_uploader('', type=['xlsx', 'csv'], accept_multiple_files=True, key=state.FILE_UPLOADER_KEY)
        _, _, _, _, _, _, c7 = st.beta_columns(7) 
        if len(excel_files) > 0 and c7.button('\U00002716 Clear all'):
            state.FILE_UPLOADER_KEY = str(randint(1000,9999))
            st.experimental_rerun()

    # STEP 2: CONFIGURE NAMES & MODE
    if not state.API_STARTED and len(excel_files) > 0:
        st.markdown('## \U0001F3AF Configure and process targets')
        st.write('_Optionally_, edit default targets for your sqlite database and table names and the update mode ' + 
                 'applied with the file.\n\nClick \U0001F528 **Process** to create sqlite databases and API routes ' +
                 'for each data file. _Repeat_ as many times as required.')
        excel_files_dict, custom_info = get_database_info(excel_files)
        _, _, _, _, _, _, c7 = st.beta_columns(7) 
        if c7.button('\U0001F528 Process'):
            create_databases(app, excel_files_dict, custom_info)

    # STEP 4: EXPOSE AS APIS
    if not state.API_STARTED and len(excel_files) > 0 and len(state.API_INFO.items()) > 0:
        st.markdown('## \U0001F3F3\U0000FE0F\U0000200D\U0001F308 Launch API')
        st.write('When configuration is complete, click \U0001F680 **Launch** to start the API endpoints.')
        if st.button('\U0001F680 Launch'):
            launch_api(app)
            state.FILE_UPLOADER_KEY = str(randint(1000,9999))
            st.experimental_rerun()

    st.write('---')
    with st.beta_expander('API endpoint details', expanded=(state.API_STARTED or len(state.API_INFO.items()) > 0)):
        if len(state.API_INFO.items()) > 0:
            for t in threading.enumerate():
                if t is threading.currentThread():
                    continue  # as t == main thread
                elif t == state.API_THREAD_OR_PROC:
                    st.write('\nTo stop the API you must terminate the app \U0001F631')

            st.markdown('### \U0001F4E1 API endpoints')
            status = 'API IS LIVE \U0001F7E2' if state.API_STARTED else 'WAITING FOR LAUNCH \U0001F534'
            st.markdown(f'### Status is {status}')

            ports = [v['port'] for (_, v) in state.API_INFO.items()]
            # st.write(ports)

            st.write(state.API_INFO)
        else:
            st.write('\U0001F4E1 API details will be shown here when \U0001F4C2 uploaded files have been \U0001F528 processed.')


def get_database_info(excel_files):

    # This will remove duplicate files
    excel_files_dict = {}
    for excel_file in excel_files:
        excel_files_dict[excel_file.name] = excel_file

    if len(excel_files) > len(excel_files_dict.items()):
        st.info('Duplicate file removed from customisation below!')

    custom_info = {}
    for _, excel_file in excel_files_dict.items():
        key = excel_file.name.lower().replace('.csv', '').replace('.xlsx', '').replace(' ', '_').replace('.', '_')

        c1, c2, c3, c4 = st.beta_columns(4)
        if len(custom_info.items()) == 0:
            c1.markdown('### File')
            c2.markdown('### Custom DB name')
            c3.markdown('### Custom table name')
            c4.markdown('### Update mode')

        with c1:
            st.write('\n')
            st.markdown(f'#### {excel_file.name}')
        with c2:
            db_name_key = f'db_name#{key}'
            custom_info[db_name_key] = st.text_input('', value=key, key=db_name_key)
        with c3:
            table_name_key = f'table_name#{key}'
            custom_info[table_name_key] = st.text_input('', value=key, key=table_name_key)
        with c4:
            update_mode_key = f'update_mode#{key}'
            custom_info[update_mode_key] = st.selectbox('', ['replace', 'append', 'fail'], key=update_mode_key)

    return excel_files_dict, custom_info

def create_databases(app, excel_files_dict, custom_info):
    message = st.empty()

    for _, excel_file in excel_files_dict.items():
        message.info(f'Loading {excel_file.name}...')
        time.sleep(0.5)

        if excel_file.type == 'application/vnd.ms-excel':
            df = csv_to_df(excel_file)
        else: # 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            df = excel_to_df(excel_file)
        
        key = excel_file.name.lower().replace('.csv', '').replace('.xlsx', '').replace(' ', '_').replace('.', '_')

        db_name = custom_info[f'db_name#{key}']
        table_name = custom_info[f'table_name#{key}']
        update_mode = custom_info[f'update_mode#{key}']

        # Allows the same db+table combination if update_mode is 'append'
        api_info_key = f'{db_name}#{table_name}'
        if api_info_key not in state.API_INFO.keys() or (update_mode == 'append'):

            message.info(f'Working on /{db_name}/{table_name}...')
            time.sleep(0.5)

            if state.API_THREAD_OR_PROC is None:
                app.create_database(database=db_name, data_path=table_name, if_exists=update_mode, df=df)
            else:
                with futures.ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(app.create_database, database=db_name, data_path=table_name, if_exists=update_mode, df=df)

            message.info(f'Done /{db_name}/{table_name}.')
            time.sleep(0.5)

            state.API_INFO[api_info_key] = {
                'api_base_url': f'http://{state.API_HOST}:{state.API_PORT}/{db_name}/{table_name}',
                'database': db_name,
                'table': table_name,
                'host': state.API_HOST,
                'port': state.API_PORT,
            }
        else:
            port = state.API_INFO[api_info_key]['port']
            message.warning(f'Skipping {api_info_key} API creation as it exists already on port {port}!')
            time.sleep(1)

    message.empty()

def launch_api(app):
    if state.API_STARTED:
        return

    if USE_MULTIPROCESSING:
        # Process fork ------------------------------------------------
        from multiprocessing import Process
        proc = Process( target=uvicorn.run,
                        args=(app,),
                        # args=(app,),
                        kwargs={
                            'host': 'localhost',
                            'port': state.API_PORT,
                            'log_level': 'info'
                        },
                        daemon=False )
        proc.start()
        time.sleep(1.0)  # time for the server to start

        state.API_THREAD_OR_PROC = proc
    else:
        # Threading ---------------------------------------------------
        def thread_runner(app, host, port):
            uvicorn.run(app, host=host, port=port)

        thread_name = f'API_THREAD_{state.API_PORT}'
        print(f'>>> Starting {thread_name} <<<')

        thread = threading.Thread(name=thread_name, target=thread_runner, args=(app, 'localhost', state.API_PORT))
        thread.start()

        state.API_THREAD_OR_PROC = thread

    state.API_STARTED = True

def terminate_api():
    if not state.API_STARTED:
        return

    if USE_MULTIPROCESSING:
        proc = state.API_THREAD_OR_PROC
        proc.terminate()
        state.API_THREAD_OR_PROC = None
        state.API_STARTED = False

def sidebar():
    st.sidebar.image('./images/logo.jpg', output_format='jpg')

    if USE_MULTIPROCESSING:
        if state.API_STARTED and st.sidebar.button('\U0001F525 Shutdown API'):
            terminate_api()

    # ABOUT
    st.sidebar.header('About')
    st.sidebar.info('APINESS is automatically converting an Excel data file into an API!\n\n' + \
        '(c) 2021. Oxford Economics Ltd. All rights reserved.')
    st.sidebar.markdown('---')

    # Display Readme.md
    if st.sidebar.checkbox('Readme', False):
        st.markdown('---')
        '''
        ### Readme :smile:
        '''
        with open('./README.md', 'r', encoding='utf-8') as f:
            readme_lines = f.readlines()
            readme_buffer = []
            images = [
                './images/fastapi_wrapper_demo.gif',
                './images/fastapi_wrapper_st_demo.gif',
                './images/fastapi_wrapper_installation.gif',
                './images/json_data.png',
                './images/html_table.png',
                './images/pbi_report_m_lang.png',
                './images/pbi_report.png',
                './images/apiness.png',
                './images/fastapi_testimonial.png'
            ]
            for line in readme_lines:
                readme_buffer.append(line)
                for image in images:
                    if image in line:
                        st.markdown(' '.join(readme_buffer[:-1]))
                        st.image(image)
                        readme_buffer.clear()
            st.markdown(' '.join(readme_buffer))


    # # TESTS
    # if st.sidebar.checkbox('Run Tests', False):
    #     st.markdown('---')
    #     st.title('Test Suite')
    #     '''
    #     ### Data Load Test
    #     '''
    #     suite = unittest.TestLoader().loadTestsFromModule(TestFixtures)
    #     result = unittest.TextTestRunner(verbosity=2).run(suite)
    #     if result.wasSuccessful():
    #         st.info(f'Test PASSED :-)')
    #         st.balloons()
    #     else:
    #         st.error(f'Test FAILED :-(')

    # # Style
    # st.sidebar.markdown('---')
    # if st.sidebar.checkbox('Configure Style'):
    #     BlockContainerStyler().block_container_styler()

if __name__ == '__main__':
    main()
    sidebar()
