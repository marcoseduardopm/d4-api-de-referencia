# Dockerfile de publicação — solução comentada.
#
# É a construção em dois estágios do laboratório 01 (slide 27 do D4-E1), com
# DUAS diferenças: entra o servidor.py, e o comando final é ELE (e não o
# uvicorn direto) — é o servidor.py que lê a PORTA do ambiente do provedor.
#
# O `--prefix=/instalado` do primeiro estágio e o destino `/usr/local` do
# segundo andam juntos, e é aí que mora o erro fácil: o pip instala as
# bibliotecas em /instalado/lib E os programas de linha de comando (o uvicorn,
# por exemplo) em /instalado/bin. Copiar só o site-packages produz uma imagem
# que constrói sem nenhum aviso e morre na subida com
# "exec: uvicorn: executable file not found in $PATH". O `mkdir -p` existe
# porque, com requirements.txt vazio, o pip não cria a pasta de destino — e o
# COPY do segundo estágio não tem o que copiar.
FROM python:3.12 AS construcao
WORKDIR /app
COPY requirements.txt .
RUN mkdir -p /instalado && pip install --no-cache-dir --prefix=/instalado -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=construcao /instalado /usr/local
COPY src/ ./src/
COPY api/ ./api/
COPY servidor.py .
# PYTHONPATH é o que deixa o `api.principal` do servidor.py ser encontrado
# sem instalar o pacote; PYTHONUNBUFFERED é o que faz os registros aparecerem
# na tela do provedor assim que acontecem — e o registro de saída é o único
# instrumento de diagnóstico de quem publica (slide 17).
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "servidor.py"]
