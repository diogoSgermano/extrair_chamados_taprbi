import logging
import os
import azure.functions as func
import pyodbc

app = func.FunctionApp()

@app.timer_trigger(schedule="0 */1 * * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False) 
def extrair_chamados(myTimer: func.TimerRequest) -> None:
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

    try:
        with pyodbc.connect(conexao_string) as conexao:
            cursor = conexao.cursor()

            for tabela in tabelas:
                # Descobre o esquema correto da tabela no banco de dados
                cursor.execute(
                    "SELECT TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?", 
                    tabela
                )
                resultado = cursor.fetchone()
                
                if resultado:
                    esquema = resultado[0]
                    # Executa usando o esquema dinâmico encontrado  
                    cursor.execute(f"SELECT TOP 0 * FROM [{esquema}].[{tabela}]")
                    colunas = [coluna[0] for coluna in cursor.description]
                    logging.info("Tabela: %s.%s | Colunas: %s", esquema, tabela, colunas)
                else:
                    logging.warning("Tabela %s não encontrada no banco.", tabela)

            cursor.close()
            
    except Exception as e:
        logging.error("Erro ao extrair metadados das tabelas: %s", str(e))