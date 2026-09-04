# -*- coding: utf-8 -*-
"""O adaptador da linha de base — A ÚNICA função deste projeto que é sua.

A sua linha de base foi escrita na disciplina anterior (D2) sem compromisso
de assinatura. Este adaptador é o envelope que dá a assinatura: a rota
`/decidir` chama SEMPRE o adaptador, nunca o seu código diretamente — é o que
faz quarenta e quatro linhas de base diferentes caberem no mesmo formato
(D4-E3 slide 6).

Troque o corpo de `decidir()` pela sua decisão; a assinatura fica.
"""

from __future__ import annotations


def decidir(texto: str, prioridade: int = 3) -> dict:
    """Recebe o caso do domínio, devolve a decisão.

    A versão abaixo é a linha de base de FÁBRICA do projeto de referência —
    uma regra trivial, sem modelo, para que o stack suba funcional desde o
    primeiro dia. Substitua pelo raciocínio da SUA linha de base da D2.

    Devolve um dicionário com, no mínimo, `decisao` (o que o sistema diz a
    fazer) e `fonte` (quem decidiu — o que a auditoria da D12 vai pedir).
    """
    if prioridade <= 2:
        decisao = "atender agora"
    elif prioridade == 3:
        decisao = "agendar na janela da semana"
    else:
        decisao = "aguardar próxima janela"
    return {"decisao": decisao, "fonte": "baseline (regra por prioridade)"}
