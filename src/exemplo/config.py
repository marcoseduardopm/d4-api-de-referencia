# -*- coding: utf-8 -*-
"""`config` — o único lugar que lê variável de ambiente com valor padrão.

A regra: **cadeia vazia conta como ausente.** O Compose SEMPRE define as
variáveis que interpola — mesmo quando o .env as deixou vazias —, então
`os.environ.get(nome, padrao)` nunca chega ao padrão: ele devolve `""`, e a
cadeia vazia vai parar dentro de uma URL (o defeito que o B01c corrigiu:
"Request URL is missing an 'http://' or 'https://' protocol" num stack
saudável). Todo o projeto lê configuração por `ambiente()`; nenhum outro
arquivo chama `os.environ.get` com dois argumentos.
"""

from __future__ import annotations

import os


def ambiente(nome: str, padrao: str = "") -> str:
    """Devolve o valor da variável, ou o padrão também quando ela vale `""`."""
    valor = os.environ.get(nome, "")
    return valor if valor.strip() else padrao
