# How to use:
#
# [1] Ensure you have `debugpy` installed:
#
#    > pip install debugpy
#
# [2] In your main streamlit app:
#
#    import streamlit_debug
#    streamlit_debug.set(flag=True, wait_for_client=True, host='localhost', port=8765)
#
# `flag=True` will initiate a debug session. `wait_for_client=True` will wait for a debug client to attach when
# the streamlit app is run before hitting your next debug breakpoint. `wait_for_client=False` will not wait.
#
# If using VS Code, you need this config in your `.vscode/launch.json` file:
#
#     {
#         // Use IntelliSense to learn about possible attributes.
#         // Hover to view descriptions of existing attributes.
#         // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
#         "version": "0.2.0",
#         "configurations": [
#             {
#                 "name": "Python: Current File",
#                 "type": "python",
#                 "request": "launch",
#                 "program": "${file}",
#                 "console": "integratedTerminal",
#                 "env": {"DEBUG": "true"}
#             },
#             {
#                 "name": "Python: debugpy Remote Attach",
#                 "type": "python",
#                 "request": "attach",
#                 "connect": {
#                     "port": 8765,
#                     "host": "127.0.0.1",
#                 },
#                 "justMyCode": false,
#                 "redirectOutput": true,
#                 "logToFile": true,
#                 "pathMappings": [
#                     {
#                         "localRoot": "${workspaceFolder}",
#                         "remoteRoot": "."
#                     }
#                 ]
#                 // "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter",
#             },
#         ]
#     }
#
# The port numbers you use need to match - in `streamlit_debug.set()` and `launch.json`. It should NOT be the same port that
# streamlit is started on.
#
# When `flag=True` and `wait_for_client=True`, you'll must activate the "Python: debugpy Remote Attach" debug session
# from vs-code.

import streamlit as st
import logging

_DEBUG = False
def set(flag: bool=False, wait_for_client=False, host='localhost', port=8765):
    global _DEBUG
    _DEBUG = flag
    try:
        # To prevent debugpy loading again and again because of
        # Streamlit's execution model, we need to track debugging state 
        if 'debugging' not in st.session_state:
            st.session_state.debugging = None

        if _DEBUG and not st.session_state.debugging:
            # https://code.visualstudio.com/docs/python/debugging
            import debugpy
            if not debugpy.is_client_connected():
                debugpy.listen((host, port))
            if wait_for_client:
                logging.info(f'>>> Waiting for debug client attach... <<<')
                debugpy.wait_for_client() # Only include this line if you always want to manually attach the debugger
                logging.info(f'>>> ...attached! <<<')
            # debugpy.breakpoint()

            if st.session_state.debugging == None:
                logging.info(f'>>> Remote debugging activated (host={host}, port={port}) <<<')
            st.session_state.debugging = True
        
        if not _DEBUG:
            if st.session_state.debugging == None:
                logging.info(f'>>> Remote debugging in NOT active <<<')
            st.session_state.debugging = False
    except:
        # Ignore... e.g. for cloud deployments
        pass
