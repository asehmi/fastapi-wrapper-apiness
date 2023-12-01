"""
Simple command line interface that starts an API by calling `fastapi-wrapper`.
"""
import typer
from typing import Optional

import uvicorn

if __package__ is None or __package__ == '':
    # uses current directory visibility
    from fastapi_wrapper import FastAPI_Wrapper, FastAPI_Wrapper_Singleton
else:
    # uses current package visibility
    from .fastapi_wrapper import FastAPI_Wrapper, FastAPI_Wrapper_Singleton

typer_app = typer.Typer()

from enum import Enum

class DataFormat(str, Enum):
    csv = "CSV"
    xlsx = "XLSX"
class IfExists(str, Enum):
    replace = "replace"
    append = "append"
    fail = "fail"

@typer_app.command()
def main(
    data_path: str = typer.Argument(None, help="Path to the data file"),
    data_format: Optional[DataFormat] = typer.Argument(DataFormat.csv, help="Format of data file"),

    config_db: Optional[str] = typer.Option("routes_config.db", help="The routes config database to be generated. Defaults to 'routes_config.db'."),
    init_routes_with_config_db: Optional[bool] = typer.Option(
        False,
        help = "Apply supplied 'config_db' to initialize API. " +
               "Assumes underlying SQLite database(s) for the API routes exist. " +
               "Requires 'config_db' argument. The server is always started."
    ),

    database: Optional[str] = typer.Option(":memory:", help="Sqlite DB name. Defaults to in-memory DB."),
    if_exists: Optional[IfExists] = typer.Option(IfExists.replace, help="Defines treatment of database if it exists"),

    start_server: Optional[bool] = typer.Option(True, help="Start server."),
    host: Optional[str] = typer.Option("127.0.0.1", help="IP to run the API on"),
    port: Optional[int] = typer.Option(8000, help="Port to run the API on"),
):
    """
    \U0001F3D7 Create APIs from CSV or XLSX data files within seconds, using fastapi.
    
    Just pass along a data file and this command will start a fastapi
    instance with auto-generated endpoints & query parameters to access the data.

    APIs can also be created from previously-generated databases and their associated API routes configuration database.
    """

    if type(config_db) != str:
        config_db = config_db.default
    if type(database) != str:
        database = database.default
    if type(host) != str:
        host = host.default
    if type(port) != int:
        port = port.default

    typer.echo("-" * 80)
    typer.echo('>>> Applicable argument values <<<')
    if init_routes_with_config_db == True:
        typer.echo(f'config_db: {config_db}')
        typer.echo(f'init_routes_with_config_db: {init_routes_with_config_db}')
        typer.echo(f'start_server: True')
        typer.echo(f'host: {host}')
        typer.echo(f'port: {port}')
    else:
        typer.echo(f'data_path: {data_path}')
        typer.echo(f'data_format: {data_format}')
        typer.echo(f'database: {database}')
        typer.echo(f'config_db: {config_db}')
        typer.echo(f'if_exists: {if_exists}')
        typer.echo(f'start_server: {start_server}')
        typer.echo(f'host: {host}')
        typer.echo(f'port: {port}')
    typer.echo("-" * 80)

    if init_routes_with_config_db == True:
        typer.echo(f"\U0001F528 Creating > Routes from file: {config_db}")
        app: FastAPI_Wrapper = FastAPI_Wrapper_Singleton(init_routes_with_config_db=False, config_db=config_db).instance
        # Force True
        start_server = True
    else:
        typer.echo(f"\U0001F528 Creating > Database: {database} | From file: {data_path} | Type: {data_format} | Update mode: {if_exists}")
        app = FastAPI_Wrapper(config_db=config_db).create_database(database, data_path, data_format=data_format, if_exists=if_exists)

    if start_server == True:
        typer.echo("\U0001F4E1 Starting API server (uvicorn)...")
        typer.echo(
            "\U0001F4A1 Check out the API docs at "
            + typer.style(f"http://{host}:{port}/docs | http://{host}:{port}/redoc", bold=True)
        )
        typer.echo("-" * 80)
        uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    typer_app()
