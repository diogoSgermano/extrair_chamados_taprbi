from datetime import datetime
import json
import logging
import os
from azure.functions import FunctionApp, TimerRequest
from azure.storage.blob import BlobServiceClient
import pyodbc

app = FunctionApp()


@app.timer_trigger(
    schedule="0 */1 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False,
)
def extrair_chamados(myTimer: TimerRequest) -> None:
  # Strings de Conexão
  conexao_sql_string = (
      "DRIVER={ODBC Driver 18 for SQL Server};"
      f"SERVER={os.environ['HOST']};"
      f"DATABASE={os.environ['DATABASE']};"
      f"UID={os.environ['USER']};"
      f"PWD={os.environ['PASSWORD']};"
      "Encrypt=yes;"
      "TrustServerCertificate=no;"
  )

  storage_connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
  container_name = "bronze"
  fonte = "itsm"  

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

  # Inicializar o cliente do Blob Storage
  blob_service_client = BlobServiceClient.from_connection_string(
      storage_connection_string
  )

  # Data atual para particionamento
  agora = datetime.utcnow()
  ano = agora.strftime("%Y")
  mes = agora.strftime("%m")
  dia = agora.strftime("%d")
  timestamp = agora.strftime("%Y%m%dT%H%M%SZ")

  try:
    with pyodbc.connect(conexao_sql_string) as conexao:
      cursor = conexao.cursor()

      for tabela in tabelas:
        # Descobrir o esquema correto da tabela
        cursor.execute(
            "SELECT TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES WHERE"
            " TABLE_NAME = ?",
            tabela,
        )
        resultado = cursor.fetchone()

        if resultado:
          esquema = resultado[0]

          # Extrair todos os dados da tabela
          cursor.execute(f"SELECT * FROM [{esquema}].[{tabela}]")
          colunas = [coluna[0] for coluna in cursor.description]
          linhas = cursor.fetchall()

          # Converter linhas do banco em uma lista de dicionários (JSON)
          dados_tabela = []
          for linha in linhas:
            dados_tabela.append(dict(zip(colunas, linha)))

          # Converter para string JSON (com tratamento de datas se necessário)
          dados_json = json.dumps(
              dados_tabela, ensure_ascii=False, default=str, indent=4
          )

          # Definir o caminho (path) no Data Lake / Blob Storage conforme o enunciado
          blob_path = (
              f"{fonte}/{tabela}/ano={ano}/mes={mes}/dia={dia}/"
              f"{tabela}_{timestamp}.json"
          )

          # Enviar para o container Bronze com proteção e logs detalhados
          blob_client = blob_service_client.get_blob_client(
              container=container_name, blob=blob_path
          )
          
          try:
              blob_client.upload_blob(dados_json, overwrite=True)
              logging.info(
                  "SUCESSO: Tabela '%s' enviada. Registos: %d -> Caminho: %s",
                  tabela,
                  len(dados_tabela),
                  blob_client.url,
              )
          except Exception as upload_err:
              logging.error(
                  "ERRO AO ENVIAR A TABELA '%s' PARA O BLOB: %s",
                  tabela,
                  str(upload_err),
              )

        else:
          logging.warning("Tabela %s não encontrada no banco.", tabela)

      cursor.close()

  except Exception as e:
    logging.error(
        "Erro durante o processo geral de extração para o Data Lake: %s", str(e)
    )