import pandas as pd

HTML_WRAPPER = r"""
<!DOCTYPE html>
<html lang="en">
    <head>
    <style>
    .dataframe {
        font-family: Arial, Helvetica, sans-serif;
        font-size: 12px;
        border-collapse: collapse;
        width: 100%;
    }
    .dataframe td, .dataframe th {
        border: 1px solid #ddd;
        padding: 4px;
    }
    .dataframe tr:nth-child(even){background-color: #f2f2f2;}
    .dataframe tr:hover {background-color: #ddd;}
    .dataframe th {
        padding-top: 8px;
        padding-bottom: 8px;
        text-align: left;
        background-color: #003469;
        color: white;
    }
    </style>
    </head>
    <body>
        <div>
            @TABLE
        </div>
    </body>
</html>"""

def wrap_html(html):
    return HTML_WRAPPER.replace('@TABLE', html)

def dicts_to_html(dicts):
    return wrap_html(pd.DataFrame([row for row in dicts]).to_html())
