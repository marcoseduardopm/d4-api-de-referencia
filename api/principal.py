# -*- coding: utf-8 -*-
"""`principal` — a aplicação FastAPI do projeto de referência.

Três rotas e um roteador prometido:
  GET  /health   verifica as dependências e reporta uma a uma (D4-E3 slide 7);
  POST /decidir  recebe o caso do domínio e chama o adaptador (slide 6);
  GET  /docs     documentação que nasce sozinha, a partir dos modelos;
  /tools         o roteador que a D5 preenche — chega ligado e vazio.

A rota de saúde não pode responder bem com o banco fora do ar: uma rota que
só devolve a palavra certa não é diagnóstico, é mais um sintoma. Por isso as
sondas estão em funções separadas — o teste do B04 derruba o banco de
propósito, e aqui ele é capturado e traduzido em estado.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import psycopg
import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from exemplo import objetos
from exemplo.config import ambiente
from .adaptador_baseline import decidir
from .ferramentas import roteador


# ── as regras de rota, num lugar só ──────────────────────────────────────────
# A rota de saúde, as sondas e o `verifica_stack.py` leem ESTAS funções. Uma
# segunda implementação da mesma regra em outro arquivo é o defeito que o
# B01c corrigiu: verificador e rota de saúde passavam a discordar.


def rota_automacao() -> str:
    """A URL da automação. Vazia conta como o serviço do Compose — mas quem
    decide o que vazio significa, em cada perfil, é o verifica_stack: no
    perfil leve vazio é a rota do fluxo em Python, e não uma URL quebrada."""
    return ambiente("AUTOMACAO_URL", "http://automacao:5678")


def automacao_configurada() -> bool:
    """Falso quando AUTOMACAO_URL ficou vazia de propósito (perfil leve)."""
    return bool(os.environ.get("AUTOMACAO_URL", "").strip())


def rota_rastros() -> str:
    """Qual das duas rotas de observabilidade (docs/08 D-08) está em uso:
    "hospedada", "local" ou "nenhuma" — nenhuma é falha, as outras duas não.

    A rota é DECLARADA em RASTROS_DESTINO, e não deduzida de quais variáveis
    foram preenchidas. Quem abre a conexão é o `exemplo.rastros`, e ele lê
    essa mesma variável (D4-E4 slide 10): deduzir aqui e declarar lá deixaria
    esta rota afirmando um destino enquanto o rastro vai para o outro — e
    esta é a disciplina que ensina o aluno a saber onde o dado dele está.
    RASTROS_DESTINO diz QUAL; RASTROS_URL e as LANGFUSE_* dizem ONDE, do
    mesmo jeito que MODELO_ORIGEM e MODELO_URL se dividem.
    """
    destino = ambiente("RASTROS_DESTINO")
    if destino == "hospedado":
        return "hospedada"
    return "local" if destino == "local" else "nenhuma"


# ── sondas — cada dependência em uma função que SOBE exceção se estiver fora ─


def _sonda_banco() -> None:
    with psycopg.connect(os.environ["BANCO_URL"], connect_timeout=3) as conexao:
        conexao.execute("SELECT 1")


def _sonda_objetos() -> None:
    objetos.cliente().head_bucket(Bucket=objetos.bucket())


def _sonda_automacao() -> None:
    if not automacao_configurada():
        # AUTOMACAO_URL vazia: o fluxo é feito em Python — uma das DUAS rotas
        # previstas (D4-E4). Escolha documentada, não serviço caído. No perfil
        # completo o Compose sempre fixa a URL, então vazio só ocorre no leve.
        return
    resposta = httpx.get(f"{rota_automacao()}/healthz", timeout=3.0)
    resposta.raise_for_status()


def _sonda_rastros() -> None:
    """A rota de rastros aceita as DUAS rotas do D-08, sem preferir nenhuma."""
    rota = rota_rastros()
    if rota == "hospedada":
        # Rota hospedada (o padrão): a presença da configuração já conta —
        # bater na nuvem a cada /health gastaria cota à toa.
        return
    if rota == "nenhuma":
        raise RuntimeError(
            "nenhuma rota de rastros configurada — RASTROS_DESTINO está "
            "vazia; use 'local' ou 'hospedado'"
        )
    resposta = httpx.get(ambiente("RASTROS_URL"), timeout=3.0)
    resposta.raise_for_status()


DEPENDENCIAS = {
    "banco": _sonda_banco,
    "objetos": _sonda_objetos,
    "automacao": _sonda_automacao,
    "rastros": _sonda_rastros,
}


# ── preparação idempotente na subida ─────────────────────────────────────────


def _preparar_banco() -> None:
    """Extensão de vetores e a tabela de documentos — se já existem, não toca.

    A tabela é a do D4-E2 slide 36, campo por campo — o projeto e o slide
    ensinam a MESMA tabela. O `caminho` é a ponte entre o armazenamento de
    objetos e o banco: o conteúdo mora lá, a tabela guarda o endereço. O
    índice vetorial NÃO é criado aqui: criá-lo é o trabalho do laboratório 03,
    onde o aluno reencontra a armadilha dos 256 MB (D4-E2 slide 36, nota do
    professor).
    """
    with psycopg.connect(os.environ["BANCO_URL"], autocommit=True) as conexao:
        conexao.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS documentos (
                id        bigserial PRIMARY KEY,
                caminho   text NOT NULL,          -- a chave no armazenamento
                trecho    text NOT NULL,
                criado_em timestamptz DEFAULT now(),
                vetor     vector(384)              -- dimensão fixa, do seu modelo
            )
            """
        )


@asynccontextmanager
async def _vida(app: FastAPI):
    _preparar_banco()
    # Os cinco prefixos do bucket nascem na subida (D4-E2 slide 27).
    objetos.garantir_estrutura()
    yield


app = FastAPI(title="API do projeto", lifespan=_vida)
app.include_router(roteador)


# ── rotas ────────────────────────────────────────────────────────────────────


class Caso(BaseModel):
    # O teto de entrada (D4-E3 slide 8: "tamanho máximo de entrada, ou alguém
    # envia um livro"). 10.000 caracteres comportam a maior OS do domínio com
    # folga e recusam um texto colado por engano — uma entrada sem teto é um
    # caminho aberto para derrubar o serviço, e é a resposta esperada da
    # terceira pergunta da folha do laboratório 04. O esqueleto do laboratório
    # NÃO traz este limite de propósito: a descoberta é o conteúdo.
    texto: str = Field(max_length=10_000)
    prioridade: int = 3


@app.get("/health")
def saude() -> dict:
    """Verifica cada dependência e diz qual falhou — nunca propaga exceção."""
    estado = {"api": "ok"}
    for nome, sonda in DEPENDENCIAS.items():
        try:
            sonda()
            estado[nome] = "ok"
        except Exception:  # noqa: BLE001 — traduzir em estado é o trabalho da rota
            estado[nome] = "falhou"
    # Três estados, e não dois. Uma dependência que ficou de fora DE PROPÓSITO
    # não é "ok": dizer "ok" onde não há serviço é a mesma mentira pequena que
    # o verificador deixou de contar sobre o modelo ausente, e aqui ela é pior,
    # porque esta rota é o que o aluno abre no navegador. As duas decisões
    # vêm das mesmas funções que o verifica_stack.py consulta — quem decide o
    # que "vazio" significa é este arquivo, e só ele.
    if not automacao_configurada():
        estado["automacao"] = "não configurada — fluxo em Python"
    if rota_rastros() == "hospedada":
        estado["rastros"] = "rota hospedada, não conferida aqui"
    # `pronto` é sobre o que FALHOU, e não sobre o que está de pé: uma escolha
    # documentada não derruba a prontidão do serviço.
    pronto = not any(v == "falhou" for v in estado.values())
    return {"pronto": pronto, "detalhe": estado}


@app.post("/decidir")
def rota_decidir(caso: Caso) -> dict:
    return {"decisao": decidir(caso.texto, caso.prioridade)}
