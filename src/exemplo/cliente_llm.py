# -*- coding: utf-8 -*-
"""`cliente_llm` — a camada de modelo, trocável por uma variável de ambiente.

A troca entre as três origens é configuração, não código (D4-E3 slide 25):

    MODELO_ORIGEM=local    → fala com MODELO_URL (compatível com OpenAI)
    MODELO_ORIGEM=api      → fala com a API do Gemini usando GEMINI_API_KEY
    MODELO_ORIGEM=gravado  → lê a resposta de um arquivo, sem rede (D4-E3
                             slide 27, nota do professor; a gravação é apontada
                             por RESPOSTAS_GRAVADAS e a escolha da gravação, por
                             GRAVACAO_USAR)

O código que chama `chamar()` não sabe de onde a resposta veio. Limites de
taxa (HTTP 429) são tratados com espera exponencial AQUI, e não descobertos
em aula (docs/04 §6).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from pydantic import BaseModel

from exemplo.config import ambiente

from exemplo.config import ambiente


class Resposta(BaseModel):
    """O que `chamar()` devolve — igual venha de onde vier."""

    texto: str
    modelo: str
    origem: str  # "local" ou "api"
    latencia_ms: int


TENTATIVAS = 3
ESPERA_INICIAL_S = 2.0


def _postar(url: str, corpo: dict, cabecalhos: dict) -> dict:
    """POST HTTP que devolve o JSON da resposta.

    Função separada (em vez de httpx chamado direto nos clientes) para que os
    testes substituam a rede sem tocar no resto — e para que o tratamento de
    sobrecarga exista num lugar só.

    A espera crescente cobre 429 E 503: o limite de taxa é a sobrecarga
    anunciada, mas o provedor também devolve 503 "Service Unavailable" sob
    rajada de chamadas na camada gratuita (medido em 03/09/2026, no
    laboratório 05) — para quem chama, os dois significam a mesma coisa:
    espere e tente de novo.
    """
    for tentativa in range(TENTATIVAS):
        resposta = httpx.post(url, json=corpo, headers=cabecalhos, timeout=60.0)
        if resposta.status_code in (429, 503):
            espera = ESPERA_INICIAL_S * (2**tentativa)
            time.sleep(espera)
            continue
        resposta.raise_for_status()
        return resposta.json()
    raise RuntimeError(
        f"sobrecarga no serviço (HTTP 429/503) após {TENTATIVAS} tentativas — "
        "espere um momento e rode de novo; 40 pessoas chamando ao mesmo tempo "
        "esbarram na cota gratuita"
    )


class ClienteLocal:
    """Modelo aberto servido localmente (Ollama, rota compatível com a da OpenAI)."""

    origem = "local"

    def __init__(self) -> None:
        self.url = os.environ["MODELO_URL"]
        self.modelo = ambiente("MODELO_NOME")

    def chamar(self, prompt: str) -> Resposta:
        inicio = time.monotonic()
        json_resp = _postar(
            f"{self.url}/chat/completions",
            {
                "model": self.modelo,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            {},
        )
        return Resposta(
            texto=json_resp["choices"][0]["message"]["content"],
            modelo=self.modelo,
            origem=self.origem,
            latencia_ms=int((time.monotonic() - inicio) * 1000),
        )


class ClienteAPI:
    """Modelo via API (Gemini Flash), a rota da camada gratuita."""

    origem = "api"

    def __init__(self) -> None:
        chave = ambiente("GEMINI_API_KEY")
        if not chave:
            raise RuntimeError(
                "MODELO_ORIGEM=api mas GEMINI_API_KEY está vazia — preencha a "
                "chave no .env (crie a sua em aistudio.google.com/apikey)"
            )
        self.chave = chave
        self.modelo = ambiente("GEMINI_MODEL", "gemini-flash-latest")

    def chamar(self, prompt: str) -> Resposta:
        inicio = time.monotonic()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.modelo}:generateContent"
        )
        json_resp = _postar(
            url,
            {"contents": [{"parts": [{"text": prompt}]}]},
            {"x-goog-api-key": self.chave},
        )
        return Resposta(
            texto=json_resp["candidates"][0]["content"]["parts"][0]["text"],
            modelo=self.modelo,
            origem=self.origem,
            latencia_ms=int((time.monotonic() - inicio) * 1000),
        )


class ClienteGravado:
    """A TERCEIRA origem: a resposta vem de um arquivo, sem rede (D4-E3
    slide 27, nota do professor — a rota de quem não baixou o modelo, e do
    laboratório executado sem rede).

    Existe DENTRO deste arquivo, e não como um segundo caminho no código que
    mede, por uma regra da fila: quem fala com o modelo usa uma implementação
    só. Quem chama `chamar()` não consegue dizer, pelo tipo, se a resposta veio
    de um serviço ou de uma gravação — e é isso que o requisito pede.

    O ponto delicado é a latência: uma resposta lida de arquivo volta em
    microssegundos, e um p95 de 0,4 ms não é medição — é lixo com aparência de
    dado. Por isso a Resposta carrega a latência MEDIDA NA MÁQUINA QUE PRODUZIU
    A GRAVAÇÃO, e o campo `origem` diz "gravado", para que ninguém confunda o
    número com o da própria máquina. O laboratório 05 e a folha dele repetem
    este aviso.
    """

    origem = "gravado"

    def __init__(self) -> None:
        caminho = ambiente("RESPOSTAS_GRAVADAS")
        if not caminho:
            raise RuntimeError(
                "MODELO_ORIGEM=gravado mas RESPOSTAS_GRAVADAS está vazia — "
                "aponte a variável para o respostas-gravadas.json do "
                "laboratório 05 (caminho completo, entre aspas se tiver espaço)"
            )
        self.caminho = Path(caminho)
        if not self.caminho.exists():
            raise RuntimeError(
                f"RESPOSTAS_GRAVADAS aponta para {self.caminho}, que não "
                "existe — confira o caminho (o arquivo vem no pacote do "
                "laboratório 05)"
            )
        self.gravacoes = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.usar = ambiente("GRAVACAO_USAR", "local")
        if self.usar not in self.gravacoes:
            raise RuntimeError(
                f"GRAVACAO_USAR={self.usar} mas o arquivo só tem as gravações: "
                + ", ".join(sorted(self.gravacoes))
            )

    def chamar(self, prompt: str) -> Resposta:
        registro = self.gravacoes[self.usar].get(prompt)
        if registro is None:
            raise RuntimeError(
                "a gravação não tem esta pergunta — o medir.py só reconhece "
                "as vinte perguntas do pacote (perguntas/perguntas.csv), e é "
                "por elas que a gravação é indexada"
            )
        return Resposta(
            texto=registro["texto"],
            modelo=registro["modelo"],
            origem=self.origem,
            latencia_ms=int(registro["latencia_ms"]),
        )


def cliente() -> ClienteLocal | ClienteAPI | ClienteGravado:
    """Escolhe o cliente pela variável — o único ponto que sabe da troca."""
    # `or`, e não segundo argumento: com MODELO_ORIGEM vazia o segundo
    # argumento não vale, a origem virava cadeia vazia e caía no `return`
    # final — a API, que gasta cota — dizendo que a chave está faltando.
    origem = os.environ.get("MODELO_ORIGEM") or "local"
    if origem == "local":
        return ClienteLocal()
    if origem == "gravado":
        return ClienteGravado()
    return ClienteAPI()


def chamar(prompt: str) -> Resposta:
    """Atalho para o resto do código: `cliente().chamar(prompt)`."""
    return cliente().chamar(prompt)
