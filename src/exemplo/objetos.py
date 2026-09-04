# -*- coding: utf-8 -*-
"""`objetos` — acesso a armazenamento compatível com S3.

O endereço do serviço vem de variável de ambiente (D4-E2 slide 25): trocar
`OBJETOS_URL` faz o MESMO código falar com o MinIO em container ou com o
serviço gerenciado do perfil leve. Nenhuma linha aqui conhece os dois.

Os cinco prefixos do bucket (D4-E2 slide 27) são criados na subida, vazios,
com um arquivo de marcação cada — reorganizar bucket depois é copiar objeto
por objeto, por isso a estrutura existe desde o primeiro dia.
"""

from __future__ import annotations

import os

import boto3

from exemplo.config import ambiente

PREFIXOS = ("brutos", "processados", "indices", "modelos", "avaliacao")
MARCADOR = "LEIA-ME.txt"
TEXTO_MARCA = (
    "Prefixo {prefixo} — criado na subida do stack (D4-E2 slide 27).\n"
    "brutos/ o que foi coletado, nunca alterado\n"
    "processados/ o resultado de cada etapa do fluxo\n"
    "indices/ vetores e estruturas de busca\n"
    "modelos/ pesos e adaptadores treinados\n"
    "avaliacao/ conjuntos de teste e resultados de medição\n"
)


def bucket() -> str:
    return ambiente("OBJETOS_BUCKET", "projeto")


def cliente():
    """O cliente S3 — endereço e credenciais vêm do ambiente, sempre."""
    return boto3.client(
        "s3",
        endpoint_url=os.environ["OBJETOS_URL"],
        aws_access_key_id=os.environ["OBJETOS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["OBJETOS_SECRET_KEY"],
    )


def garantir_estrutura(cli=None) -> list[str]:
    """Garante bucket e os cinco prefixos com arquivo de marcação cada.

    Idempotente: rodar duas vezes não duplica nada. Chamada na subida da API
    e pelo `verifica_stack.py`; aceita um cliente pronto para os testes.
    """
    cli = cli or cliente()
    nome = bucket()
    buckets_existentes = {b["Name"] for b in cli.list_buckets().get("Buckets", [])}
    if nome not in buckets_existentes:
        cli.create_bucket(Bucket=nome)
    criados: list[str] = []
    for prefixo in PREFIXOS:
        chave = f"{prefixo}/{MARCADOR}"
        existentes = cli.list_objects_v2(Bucket=nome, Prefix=chave).get("KeyCount", 0)
        if existentes == 0:
            cli.put_object(Bucket=nome, Key=chave, Body=TEXTO_MARCA.format(prefixo=prefixo))
            criados.append(prefixo)
    return criados


def enviar(caminho_local, chave: str, cli=None) -> str:
    """Sobe um arquivo para `chave` dentro do bucket do projeto."""
    cli = cli or cliente()
    cli.upload_file(str(caminho_local), bucket(), chave)
    return chave


def listar(prefixo: str = "", cli=None) -> list[str]:
    """Lista as chaves sob um prefixo (por exemplo, `brutos/`)."""
    cli = cli or cliente()
    resposta = cli.list_objects_v2(Bucket=bucket(), Prefix=prefixo)
    return [item["Key"] for item in resposta.get("Contents", [])]
