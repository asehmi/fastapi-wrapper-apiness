"""
Contains the main `FastAPI_Wrapper` class, which wraps `FastAPI`.
"""
from typing import Union, Dict, Type
from pathlib import Path
import inspect
import logging

import fastapi
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, FileResponse
import pandas as pd
import sqlite3
import numpy as np
import pydantic
import json
import os
from datetime import datetime

from .html_helper import dicts_to_html

try:
    import ptvsd
    ptvsd.enable_attach(address=('localhost', 6789))
    # ptvsd.wait_for_attach() # Only include this line if you always want to manually attach the debugger
except:
    # Ignore... for Heroku deployments!
    pass

def create_query_param(name: str, type_: Type, default) -> pydantic.fields.ModelField:
    """Create a query parameter just like fastapi does."""
    param = inspect.Parameter(
        name=name,
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
        default=default,
        annotation=type_,
    )
    field = fastapi.dependencies.utils.get_param_field(
        param=param, param_name=name, default_field_info=fastapi.params.Query
    )
    return field


def dtype_to_type(dtype) -> Type:
    """Convert numpy/pandas dtype to normal Python type."""
    if dtype == np.object:
        return str
    else:
        return type(np.zeros(1, dtype).item())

def as_int_or_float(val):
    """Infers Python int vs. float from string representation."""
    if type(val) == str:
        ret_val = float(val) if '.' in val else int(val)
        return ret_val
    return val

DB_CONNECTIONS: Dict = {} # key = db, value = connection
def connection_for_db(db) -> sqlite3.Connection:
    """Gets connection for a DB. Uses cached connection if there is one."""

    # Make database return dicts instead of tuples.
    # From: https://stackoverflow.com/questions/3300464/how-can-i-get-dict-from-sqlite-query
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    # If appending then we expect there to be an existing connection, or it's the first time
    global DB_CONNECTIONS
    con = DB_CONNECTIONS.get(db, None)
    if con is None:
        con = sqlite3.connect(db, check_same_thread=False)
        con.row_factory = dict_factory
        DB_CONNECTIONS[db] = con

    return con

def resolve_db(database) -> str:
    """Makes a proper DB file name, unless in-memory DB."""
    db = ':memory:'
    if (database is not None) and (database != ':memory:'):
        database = database.lower()
        db = database if database.endswith('.db') else f'{database}.db'

    return db, db.replace('.db', '').replace(':', '')

def delete_table(db, table_name):
    """
    Deletes the database table with all data read from the CSV. 
        
    The CSV file is not deleted of course. The API endpoints are also not affected,
    so you can use `update_database` to read in new data.
    """
    global DB_CONNECTIONS
    con = DB_CONNECTIONS.get(db, None)
    if con is not None:
        logging.info(f"Deleting old database {table_name}...")
        con.execute(f"DROP TABLE IF EXISTS {table_name}")

def close_database(db):
    """Shuts down the database with all its data."""
    global DB_CONNECTIONS
    con = DB_CONNECTIONS.get(db, None)
    if con is not None:
        logging.info(f"Closing database {db}...")
        # Closing will delete the connection. An in-memory DB will lose all data permanently.
        # See https://stackoverflow.com/questions/48732439/deleting-a-database-file-in-memory
        con.close()
        DB_CONNECTIONS.pop(db, None)

def query_database(database, sql_query):
    """Executes a SQL query on the database and returns rows as list of dicts."""
    logging.info(f"Querying database: {sql_query}")
    db, _ = resolve_db(database)
    con = connection_for_db(db)
    try:
        cur = con.execute(sql_query)
        dicts = cur.fetchall()
        return dicts
    except Exception as ex:
        raise Exception(
            f'Database {db} exception.' +
            f'Ensure the DB table exists.\n{str(ex)}'
        )

class GenericEndpoint():

    get_endpoint = None

    def __init__(self, prefix: str = '') -> None:

        # Add an endpoint for the CSV file with one query parameter for each column.
        # We hack into fastapi a bit here to inject the query parameters at runtime
        # based on the column names/types.

        # First, define a generic endpoint method, which queries the database.
        # 
        # TABLE IS A PATH PARAM & DATABASE PATH IS EXTRACTED FROM REQUEST OBJ
        # The routes are created for generic /database/{table} paths
        def generic_get(table: str, request: Request, **query_kwargs):
            path = request.url.path.split('/')
            database = path[1]
            table = table.lower()

            to_html = False
            forbidden_sql = ["insert", "delete", "update", "create", "replace", "drop", "rename", "alter"]
            where_clauses = []
            sql_cols = []
            sql_cmds = []

            for name, val in query_kwargs.items():
                name = name.lower()
                if val is not None:
                    if name.endswith("_gt"):
                        where_clauses.append(f"{name[:-3]}>{as_int_or_float(val)}")
                    elif name.endswith("_gte"):
                        where_clauses.append(f"{name[:-4]}>={as_int_or_float(val)}")
                    elif name.endswith("_lt"):
                        where_clauses.append(f"{name[:-3]}<{as_int_or_float(val)}")
                    elif name.endswith("_lte"):
                        where_clauses.append(f"{name[:-4]}<={as_int_or_float(val)}")
                    elif name.endswith("_in"):
                        where_clauses.append(f"{name[:-3]} LIKE \"%{val}%\"")
                        # where_clauses.append(f"instr({name[:-3]}, '{val}') > 0")
                    elif name.endswith("_ina"):
                        where_clauses.append(f"{name[:-4]} LIKE \"{val}%\"")
                    elif name.endswith("_inz"):
                        where_clauses.append(f"{name[:-4]} LIKE \"%{val}\"")
                    elif name == "tohtml":
                        to_html = True
                    elif name == "cols":
                        if any(x in val.lower() for x in forbidden_sql):
                            raise Exception(f"SQL columns contains a forbidden command!\n{val}\nForbidden commands: {forbidden_sql}")
                        else:
                            sql_cols.append(f"{val}")
                    elif name == "cmd":
                        if any(x in val.lower() for x in forbidden_sql):
                            raise Exception(f"SQL command is forbidden!\n{val}\nForbidden commands: {forbidden_sql}")
                        else:
                            sql_cmds.append(f"{val}")
                    elif name == "where":
                        if any(x in val.lower() for x in forbidden_sql):
                            raise Exception(f"SQL query contains a forbidden command!\n{val}\nForbidden commands: {forbidden_sql}")
                        else:
                            where_clauses.append(f"({val})")
                    else:
                        if isinstance(val, str):
                            val = f"'{val}'"
                        where_clauses.append(f"{name}={val}")

            where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            cols = ", ".join(sql_cols) if sql_cols else None
            cmd = " ".join(sql_cmds) if sql_cmds else ""

            sql_query_count = f"SELECT COUNT(*) FROM {table} {where}".strip()
            count_dicts = query_database(database, sql_query_count)
            count = count_dicts[0]['COUNT(*)']

            sql_select = f"SELECT {cols}" if cols else "SELECT *"
            sql_from = f"FROM {table} {where} {cmd}"
            sql_query = f"{sql_select} {sql_from}".strip()
            dicts = query_database(database, sql_query)

            results = {
                'metadata': {
                    'database': database,
                    'table': table,
                    'sql_query': sql_query,
                    'full_count': count,
                    'results_count': len(dicts),
                },
                'data': dicts
            }

            if to_html:
                html_content = dicts_to_html(dicts)
                results = HTMLResponse(content=html_content, status_code=200)

            return results

        ### end def generic_get() ###

        setattr(self.__class__, f'{prefix}_generic_get', generic_get)

        self.get_endpoint = getattr(self.__class__, f'{prefix}_generic_get')


class FastAPI_Wrapper(FastAPI):

    get_endpoint = None
    openapi = None

    def __init__(self) -> None:
        """
        Initializes a FastAPI instance that serves data from a CSV file.
        """
        print('Initializing FastAPI_Wrapper...')
        
        super().__init__()

        def custom_openapi():
            from fastapi.openapi.utils import get_openapi
            from .__init__ import __version__ as version

            print('Running custom_openapi...')
            
            if self.openapi_schema:
                return self.openapi_schema
            openapi_schema = get_openapi(
                title="FastAPI Wrapper for CSV & Excel Files",
                version=version,
                description="Custom API enpoints available for each converted file is listed below.",
                routes=self.routes,
            )
            openapi_schema["info"]["x-logo"] = {
                "url": "https://www.oxfordeconomics.com/static/img/logo.png"
            }
            self.openapi_schema = openapi_schema
            return self.openapi_schema

        self.openapi = custom_openapi

        # Add shutdown event (would only be of any use in a multi-process, not multi-thread situation)
        def shutdown():
            logging.info(f'>>> Graceful shutdown of API <<<')
        self.on_event('shutdown')(shutdown)

        # ----- FIXED ROUTES -----

        # /download/{db}
        # 
        # Add download database method as GET endpoint to fastapi
        # db is a path param
        def download(db: str,
                     responses={ 200: { 'description': 'Download SQL database file.',
                                        'content' : {'application/octet-stream' : {'example' : 'No example available.'}}
                     }}
        ):
            db = db if db.endswith('.db') else f'{db}.db'
            file_path = os.path.join('./', db)
            if os.path.exists(file_path):
                suffix = str(datetime.now())[:-10].replace(' ', '_').replace(':','_')
                db_suffix = db.replace('.db', f'_{suffix}.db')
                return FileResponse(file_path, media_type='application/octet-stream', filename=db_suffix)
            return {'error' : f'{db} file not found!'}

        route_path = '/download/{db}'
        route_name = 'download'
        self.get(route_path, name=route_name, tags=[route_name])(download)

        # /createdb?database=db&data_path=dp&data_format=<CSV | XLSX>&if_exists=<fail | replace | append>
        #
        # Add createdb method as GET endpoint to fastapi
        # NOTE: Not very useful for physical DBs except when run locally!
        def createdb(**query_kwargs):
            print(query_kwargs)

            database = query_kwargs.get('database', None) or ':memory:'

            data_path = query_kwargs.get('data_path', None)
            if data_path is None:
                return Response(f"You must provide a data_path value", status_code=418) # I'm a teapot!

            data_format = query_kwargs.get('data_format', None) or 'CSV'
            if data_format.upper() not in ['CSV', 'XLSX']:
                return Response(f"data_format parameter must be one of ['CSV', 'XLSX']", status_code=418) # I'm a teapot!

            if_exists = query_kwargs.get('if_exists', None) or 'replace'
            if if_exists not in ['fail', 'replace', 'append']:
                return Response(f"if_exists parameter must be one of ['fail', 'replace', 'append']", status_code=418) # I'm a teapot!

            try:
                self.create_database(database, data_path, data_format=data_format, if_exists=if_exists)
            except Exception as ex:
                return Response(f'Failed: {str(ex.msg)}', status_code=418)

            table_name=Path(data_path).stem.lower().replace(' ', '_').replace('.', '_')

            route_name = f'/{database}/{table_name}'
            query_params = self._get_query_params(route_name)
            query_params = [model_field.name for model_field in query_params]

            return Response(json.dumps({'status:': 'success', 'endpoint': route_name, 'params': query_params}), status_code=200)

        route_path = '/createdb'
        route_name = 'createdb'
        self.get(route_path, name=route_name, tags=[route_name])(createdb)
        self._clear_query_params(route_path)
        self._add_query_param(route_path, 'database', str)
        self._add_query_param(route_path, 'data_path', str)
        self._add_query_param(route_path, 'data_format', str)
        self._add_query_param(route_path, 'if_exists', str)


    def create_database(self, database: str, data_path: Union[str, Path], data_format='CSV', if_exists='replace', df=None) -> None:
        """
        Create DB

        Args:
            database (str): Required. If None or ":memory:", then an in-memory DB will be created.
            data_path (Union[str, Path]): Required. The path to the CSV file, can also be a URL
            data_format (str): 'CSV' | 'XLSX'
            if_exists : {'fail', 'replace', 'append'}, default 'fail': controls how
            the database table is treated if it already exists
            df (pd.DataFrame): Optionally, a populated dataframe will be used instead of a data file
        """
        db, db_name = resolve_db(database)

        df_db = self.update_database(db, data_path, data_format=data_format, if_exists=if_exists, df=df)

        # Add the method as GET endpoint to fastapi.
        # {database-table_name} represents a *unique* root and path param details will be extracted from the request object
        table_name=Path(data_path).stem.lower().replace(' ', '_').replace('.', '_')
        
        # route path with table path param
        route_path = f'/{db_name}' + '/{table}'
        route_name = f'{db_name}_{table_name}'.lower()
        route_tags = [db_name.lower()]

        self.get(route_path, name=route_name, tags=route_tags, operation_id=route_name, include_in_schema=True)(GenericEndpoint(prefix=route_name).get_endpoint)
    
        # Remove all auto-generated query parameters (=one for `kwargs`).
        self._clear_query_params(route_path)

        # Add new query parameters based on column names and data types.
        # Column names are lowercased and spaces replaced with '_'
        for col, dtype in zip(df_db.columns, df_db.dtypes):
            type_ = dtype_to_type(dtype)
            col = col.lower().replace(' ', '_')
            self._add_query_param(route_path, col, type_)
            if type_ in (int, float):
                self._add_query_param(route_path, col + "_gt", type_)
                self._add_query_param(route_path, col + "_gte", type_)
                self._add_query_param(route_path, col + "_lt", type_)
                self._add_query_param(route_path, col + "_lte", type_)
            elif type_ == str:
                self._add_query_param(route_path, col + "_in", type_)
                self._add_query_param(route_path, col + "_ina", type_)
                self._add_query_param(route_path, col + "_inz", type_)

        self._add_query_param(route_path, "where", str)
        self._add_query_param(route_path, "cols", str)
        self._add_query_param(route_path, "cmd", str)
        self._add_query_param(route_path, "tohtml", str)

        return self


    def update_database(self, database: str, data_path: Union[str, Path], data_format='CSV', if_exists='replace', df=None):
        """
        Updates the database with the current data from the CSV file.
        
        Note that this only affects the database, not the endpoints. If the column names
        and/or data types in the CSV change (and you want that to update in the 
        endpoints as well), you need to create a new FastAPI_CSV object.

        Args:
            database (str): Required. If None or ":memory:", then an in-memory DB will be created.
            data_path (Union[str, Path]): Required. The path to the CSV file, can also be a URL
            data_format (str): 'CSV' | 'XLSX'
            if_exists : {'fail', 'replace', 'append'}, default 'fail': controls how
            the database table is treated if it already exists
            df (pd.DataFrame): Optionally, a populated dataframe will be used instead of a data file
        """

        db, _ = resolve_db(database)

        # Details of file to be read into DF. A sqlite3 database will be created from it.
        table_name=Path(data_path).stem.lower().replace(' ', '_').replace('.', '_')
        invalid_chars = set(table_name).intersection(set(',;:()[]+-*/<>=~!@#%^&|`?$'))
        is_valid_name = len(invalid_chars) == 0

        if not is_valid_name:
            raise Exception(f'Invalid character(s) {invalid_chars} in data_path ({data_path}). Cannot create a valid table name.')

        df_db = None

        if df is None:
            # Download excel file from data path (e.g. GitHub, Google Sheets, filesystem), read it
            # with pandas and write to database.
            if data_format == 'CSV':
                df_db = pd.read_csv(data_path)
            elif data_format == 'XLSX':
                df_db = pd.read_excel(data_path)
            else:
                raise Exception(f'Data format not supported: {data_format}')
        else:
            assert(isinstance(df, pd.DataFrame))
            df_db = df

        normalized_columns = [col.lower().replace(' ', '_').replace('.', '_').replace(':', '_').replace('unnamed', 'x') for col in df_db.columns]
        df_db.columns = normalized_columns

        if (if_exists != 'append'):
            # delete table
            delete_table(db, table_name)

        con = connection_for_db(db)

        # Create the DB
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_sql.html
        df_db.to_sql(table_name, con=con, index_label='id', chunksize=100000, if_exists=if_exists)

        logging.info("Database successfully updated")
        logging.info(f'Columns: {list(df_db.columns)}')

        return df_db

    def _find_route(self, route_path_or_name):
        """Find a route (stored in the FastAPI instance) by its path (e.g. '/index')."""
        for route in self.router.routes:
            if route.path == route_path_or_name or route.name == route_path_or_name:
                return route

    def _clear_query_params(self, route_path):
        """Remove all query parameters of a route."""
        route = self._find_route(route_path)
        # logging.info("Before:", route.dependant.query_params)
        route.dependant.query_params = []
        # logging.info("After:", route.dependant.query_params)

    def _add_query_param(self, route_path, name, type_, default=None):
        """Add a new query parameter to a route."""
        route = self._find_route(route_path)
        # logging.info("Before:", route.dependant.query_params)
        query_param = create_query_param(name, type_, default)
        route.dependant.query_params.append(query_param)
        # logging.info("After:", route.dependant.query_params)

    def _get_query_params(self, route_path) -> list:
        """Gets all dependent query params for a route."""
        route = self._find_route(route_path)
        return route.dependant.query_params

