# -*- coding: utf-8 -*-
"""O roteador de ferramentas — chega LIGADO e VAZIO, de propósito.

É linha do Contrato de Saída (plano §3): a disciplina seguinte (D5) acrescenta
aqui `POST /tools/<nome>` para cada ferramenta do agente. O roteador já está
incluído na aplicação em `principal.py`, então a D5 só acrescenta rotas — nada
de ligar roteador novo nem mexer na aplicação.

Se você chegou até aqui querendo apagar este arquivo: ele é o ponto de
extensão prometido às disciplinas seguintes; apagá-lo quebra o contrato.
"""

from fastapi import APIRouter

roteador = APIRouter(prefix="/tools", tags=["ferramentas"])

# Nenhuma rota por enquanto — é o estado correto deste arquivo na D4.
# A D5 acrescenta a primeira:  @roteador.post("/<nome>")
