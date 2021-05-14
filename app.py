import os
from concurrent import futures
import time
import streamlit as st
from random import randint
import logging
import requests

import settings.settings as settings

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

from utils import SessionState
# Session State variables:
state = SessionState.get(
    API_APP = None,
    API_INFO={}, # {'db#tbl': {'api_base_url': url, 'database': db, 'table': tbl, 'host': host, 'port': port}, ...}
    API_STARTED=False,
    API_CONFIG_DB='apiness_routes_config.db',

    FILE_UPLOADER_KEY = str(randint(1000,9999)),
)

# --------------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format='(%(threadName)-10s) %(message)s',
)

# --------------------------------------------------------------------------------

# NOTE: Design point... only main() is allowed to mutate state. All supporting functions should not mutate state.
def main():
    st.title('APINESS')
    st.write('Apiness is being open... upload and convert Excel data files into API endpoints and backing SQLite databases!')

    if state.API_APP is None:
        print('>>> Creating new FastAPI_Wrapper <<<')
        
        # Need to put this import here otherwise it gets reloaded in Streamlit's reruns
        # and messes up registration of routes which are dynamically created
        from fastapi_wrapper.fastapi_wrapper import FastAPI_Wrapper

        app = FastAPI_Wrapper(init_routes_with_config_db=False, config_db=state.API_CONFIG_DB)
        state.API_APP = app
        state.API_INFO = {}
        state.API_STARTED = False

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
        st.markdown('## \U0001F3AF Customize database details and submit for processing')
        st.write('Optionally, change default names of the database and table targets, and update mode ' + 
                 'if the database already exists.\n\nClick \U0001F528 **Process** to create sqlite databases and API endpoints ' +
                 'for each data file.')
        st.caption('_Repeat_ as many times as required.')
        excel_files_dict, custom_names_info = database_info_form(excel_files)
        _, _, _, _, _, _, c7 = st.beta_columns(7) 
        if c7.button('\U0001F528 Process'):
            state.API_INFO = create_databases(
                app, excel_files_dict, custom_names_info,
                state.API_INFO, state.API_STARTED, settings.API_HOST, settings.API_PORT
            )

    # STEP 4: EXPOSE AS APIS
    if not state.API_STARTED and len(excel_files) > 0 and len(state.API_INFO.items()) > 0:
        st.markdown('## \U0001F3F3\U0000FE0F\U0000200D\U0001F308 Launch API')
        st.write('When customization is complete, select \U0001F680 **Launch** to start the API endpoints.')

        with st.beta_expander('\U0001F3D7 Set test mode and duration (optional)', expanded=False):
            c1, _, c3, _, _, _ = st.beta_columns(6)
            c1.write('\n')
            test_mode = c1.checkbox('On | Off', value=True)
            test_duration = c3.slider('Test duration (seconds)', min_value=15, max_value=600, value=15, step=15)

        status = st.empty()
        status.markdown('### Status: Pending Launch \U0001F534 | Test Mode ' + ('On \U0001F7E2' if test_mode else 'Off \U0001F534'))
        if st.checkbox('\U0001F680 Launch', value=False):

            with st.beta_expander('\U0001F4E1 API endpoint details'):
                if len(state.API_INFO.items()) > 0:
                    st.markdown('### \U0001F4E1 API endpoints')
                    print_api_info(state.API_INFO, settings.API_HOST, settings.API_PORT)
                else:
                    st.write('\U0001F4E1 API details will be shown here when \U0001F4C2 uploaded files have been \U0001F528 processed.')

            status.markdown('### Status: Live \U0001F7E2 | Test Mode ' + ('On \U0001F7E2' if test_mode else 'Off \U0001F534'))

            if test_mode:

                from utils.UvicornServer import Server
                server = Server(app=app, host=settings.API_HOST, port=settings.API_PORT)

                # server thread will shutdown when the with block exits
                with server.run_in_thread():
                    state.API_STARTED = True
                    counter = st.empty()

                    # Loop for test duration and update message every 5 secs!
                    i = 0
                    while i < test_duration/5:
                        remaining = test_duration - i*5
                        counter.info(f'You have a {test_duration} seconds to test the API. {remaining} seconds remaining.')
                        time.sleep(5)
                        i += 1

                    state.FILE_UPLOADER_KEY = str(randint(1000,9999))
                    state.API_APP = None
                    state.API_INFO = {}
                    state.API_STARTED = False

                    st.experimental_rerun()

            else: # not test_mode

                if not state.API_STARTED:
                    import subprocess
                    import threading

                    def run(job):
                        print (f"\nRunning job: {job}\n")
                        proc = subprocess.Popen(job)
                        proc.wait()
                        return proc

                    job = ['python', os.path.join('./', 'bootstrapper.py'), state.API_CONFIG_DB, settings.API_HOST, str(settings.API_PORT)]

                    # server thread will remain active as long as streamlit thread is running, or is manually shutdown
                    thread = threading.Thread(name='FastAPI-Bootstrapper', target=run, args=(job,), daemon=True)
                    thread.start()

                    state.API_STARTED = True


def database_info_form(excel_files):

    # This will remove duplicate files
    excel_files_dict = {}
    for excel_file in excel_files:
        excel_files_dict[excel_file.name] = excel_file

    if len(excel_files) > len(excel_files_dict.items()):
        st.info('Duplicate file removed from customisation below!')

    custom_names_info = {}
    for _, excel_file in excel_files_dict.items():
        key = excel_file.name.lower().replace('.csv', '').replace('.xlsx', '').replace(' ', '_').replace('.', '_')

        c1, c2, c3, c4 = st.beta_columns(4)
        if len(custom_names_info.items()) == 0:
            c1.markdown('### File')
            c2.markdown('### Custom DB name')
            c3.markdown('### Custom table name')
            c4.markdown('### Update mode')

        with c1:
            st.write('\n')
            st.markdown(f'#### {excel_file.name}')
        with c2:
            db_name_key = f'db_name#{key}'
            custom_names_info[db_name_key] = st.text_input('', value=key, key=db_name_key)
        with c3:
            table_name_key = f'table_name#{key}'
            custom_names_info[table_name_key] = st.text_input('', value=key, key=table_name_key)
        with c4:
            update_mode_key = f'update_mode#{key}'
            st.write('\n')
            custom_names_info[update_mode_key] = st.radio('', ['replace', 'append', 'fail'], key=update_mode_key)

    return excel_files_dict, custom_names_info

def create_databases(app, excel_files_dict, custom_names_info, api_info, started, host, port):
    message = st.empty()

    for _, excel_file in excel_files_dict.items():
        message.info(f'Loading {excel_file.name}...')
        time.sleep(0.5)

        if excel_file.type == 'application/vnd.ms-excel':
            df = csv_to_df(excel_file)
        else: # 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            df = excel_to_df(excel_file)
        
        key = excel_file.name.lower().replace('.csv', '').replace('.xlsx', '').replace(' ', '_').replace('.', '_')

        db_name = custom_names_info[f'db_name#{key}']
        table_name = custom_names_info[f'table_name#{key}']
        update_mode = custom_names_info[f'update_mode#{key}']

        # This key allows for the same db+table combination when update_mode is 'append'
        api_info_key = f'{db_name}#{table_name}'
        if api_info_key not in api_info.keys() or (update_mode == 'append'):

            message.info(f'Working on /{db_name}/{table_name}...')
            time.sleep(0.5)

            if started is False:
                app.create_database(database=db_name, data_path=table_name, if_exists=update_mode, df=df)
            else:
                with futures.ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(app.create_database, database=db_name, data_path=table_name, if_exists=update_mode, df=df)

            message.info(f'Done /{db_name}/{table_name}.')
            time.sleep(0.5)

            api_info[api_info_key] = {
                'source_file': excel_file.name,
                'api_base_url': f'http://{host}:{port}/{db_name}/{table_name}',
                'database': db_name,
                'table': table_name,
                'host': host,
                'port': port,
            }
        else:
            port = api_info[api_info_key]['port']
            message.warning(f'Skipping {api_info_key} API creation as it exists already on port {port}!')
            time.sleep(1)

    message.empty()

    return api_info

def print_api_info(api_info, host, port):
    st.markdown(f'''
        Your API can be tested incrementally. When you're ready, download the generated data databases
        and associated API configuration database. You will then be able to run the API using the
        command line interface (CLI) application (run `fastapi-wrapper --help` for instructions).

        - Configuration Database: **{state.API_CONFIG_DB}**
          - [Download Config DB](http://{host}:{port}/download/{state.API_CONFIG_DB})
        <p/>            
    ''', unsafe_allow_html=True)
    for (_, v) in api_info.items():
        st.markdown(f'''
            #### {v['source_file']}
            - Database: **{v['database']}.db**
              - [Download SQL DB](http://{host}:{port}/download/{v['database']})
            - Configuration Database: **{v['database']}.db**
              - [Download SQL DB](http://{host}:{port}/download/{v['database']})
            - Table: **{v['table']}**
            - Endpoint: [**{v['api_base_url']}**]({v['api_base_url']}?cmd=LIMIT%203)
            <p/>            
        ''', unsafe_allow_html=True)
    st.markdown(f'''
        ### API docs
        - [**http://{host}:{port}/docs**](http://{host}:{port}/docs)
        - [**http://{host}:{port}/redoc**](http://{host}:{port}/redoc)
    ''')

def sidebar():
    st.sidebar.image('./images/logo.jpg', output_format='jpg')

    if state.API_STARTED:
        # st.sidebar.markdown(f'''
        #     The API is running. If you'd like to terminate the API click the link below and then press `CTRL-F5` to refersh the app.

        #     [Shutdown API \U0001F525 (click with care)](http://{settings.API_HOST}:{state.API_PORT}/shutdown)
        #     <p/>
        # ''', unsafe_allow_html=True)

        st.sidebar.markdown(f'''
            The API is running. If you'd like to terminate the API click the button below and then press `CTRL-F5` to refresh the app.
            <p/>
        ''', unsafe_allow_html=True)
        if st.sidebar.button('Shutdown API \U0001F525 (click with care)'):
            requests.get('http://127.0.0.1:8000/shutdown')

            state.FILE_UPLOADER_KEY = str(randint(1000,9999))
            state.API_APP = None
            state.API_INFO = {}
            state.API_STARTED = False

            st.experimental_rerun()

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
