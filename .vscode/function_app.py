
import logging
import os

import azure.functions as func
import pyodbc

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def verificar_colunas(myTimer: func.TimerRequest) -> None:
    conexao_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.environ['HOST']};"
        f"DATABASE={os.environ['DATABASE']};"
        f"UID={os.environ['USER']};"
        f"PWD={os.environ['PASSWORD']};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    tabelas = [
        "analista",
        "categoria",
        "chamado",
        "chamado_sla",
        "chamado_status_historico",
        "cliente_organizacao",
        "csat_avaliacao",
        "fila",
        "sla",
        "solicitante",
    ]

    with pyodbc.connect(conexao_string) as conexao:
        cursor = conexao.cursor()

        for tabela in tabelas:
            cursor.execute(f"SELECT TOP 0 * FROM dbo.[{tabela}]")

            colunas = [coluna[0] for coluna in cursor.description]

            logging.info("Tabela: %s | Colunas: %s", tabela, colunas)

        cursor.close()
    