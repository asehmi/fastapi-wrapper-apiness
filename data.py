import streamlit as st
import pandas as pd

@st.cache_data(show_spinner=False)
def csv_to_df(excel_file):
    df = pd.read_csv(excel_file)
    return df

@st.cache_data(show_spinner=False)
def excel_to_df(excel_file):
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html
    # New in Pandas version 1.3.0.
    #   The engine xlrd now only supports old-style .xls files. When engine=None, the following logic will be used to determine the engine:
    #   If path_or_buffer is an OpenDocument format (.odf, .ods, .odt), then odf will be used.
    #   Otherwise if path_or_buffer is an xls format, xlrd will be used.
    #   Otherwise if path_or_buffer is in xlsb format, pyxlsb will be used.
    #   Otherwise openpyxl will be used.
    #
    # import openpyxl
    # df = pd.read_excel(excel_file, engine=openpyxl)
    #
    # Therefore... do not need to provide "engine" when using a "path_or_buffer"
    df = pd.read_excel(excel_file, engine='openpyxl')
    return df

