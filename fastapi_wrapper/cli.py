"""
Simple command line interface that starts an API by calling `fastapi-wrapper`.
"""
import typer
from typing import List, Optional
import uvicorn

from .fastapi_wrapper import FastAPI_Wrapper

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
    data_path: str = typer.Argument(..., help="Path to the data file"),
    data_format: DataFormat = typer.Argument(DataFormat.csv, help="Format of data file"),
    database: str = typer.Option(":memory:", help="Sqlite DB name. Defaults to in-memory DB."),
    if_exists: IfExists = typer.Option(IfExists.replace, help="Defines treatment of database if it exists"),
    start_server: bool = typer.Option(True, help="Start server."),
    host: str = typer.Option("127.0.0.1", help="IP to run the API on"),
    port: int = typer.Option(8000, help="Port to run the API on"),
):
    """
    🏗️ Create APIs from CSV or XLSX data files within seconds, using fastapi.
    
    Just pass along a data file and this command will start a fastapi
    instance with auto-generated endpoints & query parameters to access the data.
    """
    typer.echo(f"🏗️ Creating > Database: {database} | From file: {data_path} | Type: {data_format} | Update mode: {if_exists}")
    app = FastAPI_Wrapper().create_database(database, data_path, data_format=data_format, if_exists=if_exists)
    if start_server == True:
        typer.echo("🦄 Starting API server (uvicorn)...")
        typer.echo(
            "💡 Check out the API docs at "
            + typer.style(f"http://{host}:{port}/docs | http://{host}:{port}/redoc", bold=True)
        )
        typer.echo("-" * 80)
        uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    typer_app()
