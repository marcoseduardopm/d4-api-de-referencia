# -*- coding: utf-8 -*-
"""`dados` — as três funções tipadas de exemplo do projeto de referência.

Não tocam em serviço nenhum: carregam, validam e resumem registros do
domínio. Existem para que os laboratórios tenham dado real sem rede —
regra 11 da fila: nenhum laboratório depende de rede para ser corrigido.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class Registro(BaseModel):
    """Um caso do domínio, no formato mínimo que a rota `/decidir` consome."""

    id: str
    texto: str = Field(min_length=1)
    prioridade: int = Field(default=3, ge=1, le=5)


def carregar(caminho: Path) -> list[Registro]:
    """Lê um arquivo JSON (lista) ou JSONL (um objeto por linha).

    Falha com mensagem, não com rastro de pilha: arquivo vazio ou mal
    formado é condição de laboratório, não exceção.
    """
    conteudo = caminho.read_text(encoding="utf-8")
    if not conteudo.strip():
        return []
    if caminho.suffix == ".jsonl":
        linhas = [json.loads(linha) for linha in conteudo.splitlines() if linha.strip()]
    else:
        linhas = json.loads(conteudo)
    return [Registro.model_validate(item) for item in linhas]


def validar(registros: list[Registro]) -> tuple[list[Registro], list[str]]:
    """Separa o que passou do que não passou na validação.

    Devolve `(válidos, problemas)`; cada problema nomeia o índice e o motivo.
    Aqui os itens já são `Registro`, então a função existe para o laboratório
    ver ONDE a validação mora — e para trocar o modelo de entrada sem tocar
    nas rotas.
    """
    validos: list[Registro] = []
    problemas: list[str] = []
    for indice, registro in enumerate(registros):
        try:
            Registro.model_validate(registro.model_dump())
            validos.append(registro)
        except ValidationError as erro:
            problemas.append(f"[{indice}] {erro.errors()[0]['msg']}")
    return validos, problemas


def resumir(registros: list[Registro]) -> dict:
    """Conta registros por prioridade — o resumo que a aula usa de exemplo."""
    contagem: dict[int, int] = {}
    for registro in registros:
        contagem[registro.prioridade] = contagem.get(registro.prioridade, 0) + 1
    return {
        "total": len(registros),
        "por_prioridade": {str(p): c for p, c in sorted(contagem.items())},
    }
