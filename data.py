import streamlit as st
import pandas as pd

@st.cache(allow_output_mutation=True)
def csv_to_df(excel_file):
    df = pd.read_csv(excel_file)
    return df

@st.cache(allow_output_mutation=True)
def excel_to_df(excel_file):
    df = pd.read_excel(excel_file)
    return df

