# -*- coding: utf-8 -*-
"""O servidor de publicação — as duas linhas que quebram (D4-E4 slide 19).

Este arquivo é o que o provedor executa. Ele não é a aplicação (essa é a
`api/principal.py` de sempre): é o ponto de entrada que sobe a aplicação com
a PORTA que vem de fora. É o código do slide 19, linha por linha.
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.principal:app",
        # 0.0.0.0 — o endereço que aceita conexão de QUALQUER origem. É o
        # mesmo erro do primeiro sábado, agora com consequência pública: o
        # serviço vive dentro de um container (ou do ambiente do provedor) e
        # quem chama está fora dele. Um servidor preso a 127.0.0.1 escuta só
        # a interface local DO PRÓPRIO container: de fora, a conexão é
        # recusada — e o serviço "parece no ar" nos registros, o que torna o
        # sintoma cruel de depurar de longe.
        host="0.0.0.0",              # não 127.0.0.1
        # A porta vem de uma variável COM VALOR DE RESERVA, porque cada
        # provedor escolhe a sua e informa por variável de ambiente
        # (Render informa PORT, por exemplo). Porta fixada no código publica
        # um serviço que sobe, responde ao próprio processo e é inalcançável.
        # A reserva vem de um `or`, e NÃO de um segundo argumento do `get`:
        # provedor que define PORT vazia entrega cadeia vazia, o segundo
        # argumento nunca é alcançado, e `int("")` mata o processo na partida.
        # Cadeia vazia conta como ausente — a regra do `exemplo.config`.
        port=int(os.environ.get("PORT") or 8000),
    )
