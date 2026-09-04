# -*- coding: utf-8 -*-
"""`rastros` — observabilidade com UMA implementação e o destino na configuração.

`iniciar(destino=...)` e `trecho(...)` são os dois nomes do D4-E4 slide 10.
O `destino` é uma palavra, não um endereço:

    RASTROS_DESTINO=hospedado  → a camada gratuita hospedada (LANGFUSE_HOST
                                 mais as duas chaves, todas do ambiente)
    RASTROS_DESTINO=local      → o coletor em container (RASTROS_URL)

Os dois falam a MESMA norma aberta de telemetria (OTLP por HTTP) — foi assim
que uma implementação só cobriu os dois lados, sem o segundo caminho que o
requisito 11 proíbe. Confirmado por execução contra os dois destinos em
03/09/2026 (relatório R05, provas 2 e 3).

Leitura de configuração: sempre por `ambiente()` — cadeia vazia conta como
ausente (docs do projeto; o `os.environ.get` com padrão não chega ao padrão
quando o Compose entrega a variável vazia).
"""

from __future__ import annotations

import base64
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from exemplo.config import ambiente

_provedor: TracerProvider | None = None
_tracer = None


def _endereco(destino: str) -> tuple[str, dict]:
    """(rota OTLP, cabeçalhos) para o destino pedido — nada além disso.

    Erro nomeado com instrução: falta de configuração é o problema mais
    comum, e a mensagem tem de dizer qual variável, não um rastro de pilha.
    """
    if destino == "hospedado":
        host = ambiente("LANGFUSE_HOST")
        publica = ambiente("LANGFUSE_PUBLIC_KEY")
        secreta = ambiente("LANGFUSE_SECRET_KEY")
        if not (host and publica and secreta):
            raise RuntimeError(
                "RASTROS_DESTINO=hospedado mas falta configuração — preencha "
                "LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY "
                "no .env do perfil leve"
            )
        par = base64.b64encode(f"{publica}:{secreta}".encode()).decode()
        return f"{host.rstrip('/')}/api/public/otel/v1/traces", {
            "Authorization": f"Basic {par}"
        }
    if destino == "local":
        url = ambiente("RASTROS_URL")
        if not url:
            raise RuntimeError(
                "RASTROS_DESTINO=local mas RASTROS_URL está vazia — no stack "
                "do Compose é http://rastros:6006; da máquina, "
                "http://localhost:6006"
            )
        return f"{url.rstrip('/')}/v1/traces", {}
    raise RuntimeError(
        f"destino de rastros desconhecido: {destino!r} — use 'local' ou "
        "'hospedado' (a escolha é por sensibilidade do dado, D4-E4 slide 9)"
    )


def _exportador(destino: str):
    endereco, cabecalhos = _endereco(destino)
    # `endpoint=` é o nome do parâmetro da biblioteca, e por isso fica.
    return OTLPSpanExporter(endpoint=endereco, headers=cabecalhos)


def iniciar(destino: str, exportador=None) -> None:
    """Liga a instrumentação ao destino. Chamar de novo reinicia sem erro.

    O `exportador` é só para os testes (que não têm rede nem serviço de pé,
    como TODOS os testes do projeto) — produza-o com _exportador(destino).
    """
    global _provedor, _tracer
    _provedor = TracerProvider(
        resource=Resource.create({"service.name": ambiente("RASTROS_SERVICO", "projeto")})
    )
    _provedor.add_span_processor(BatchSpanProcessor(exportador or _exportador(destino)))
    _tracer = _provedor.get_tracer("exemplo.rastros")


def fechar() -> None:
    """Despacha o que estiver em fila — chame antes de o programa acabar."""
    if _provedor is not None:
        _provedor.force_flush()


class _Trecho:
    """O `t` do slide 10: os campos de um passo (slide 8) viram atributos."""

    def __init__(self, span) -> None:
        self._span = span
        self._aberto = True

    def registrar(self, **campos) -> None:
        if not self._aberto:
            raise RuntimeError("trecho fechado — registrar depois do `with` não registra")
        for nome, valor in campos.items():
            self._span.set_attribute(nome, valor)


@contextmanager
def trecho(nome: str, **atributos):
    """Abre um trecho (D4-E4 slide 7): cada passo com início e fim.

    Os atributos do construtor são fixos (como `prompt_versao` no slide);
    os que dependem da chamada chegam pelo `t.registrar(...)`.
    """
    with _tracer.start_as_current_span(nome) as span:
        t = _Trecho(span)
        for nome_atr, valor in atributos.items():
            span.set_attribute(nome_atr, valor)
        yield t
        t._aberto = False
