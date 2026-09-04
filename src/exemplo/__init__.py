# -*- coding: utf-8 -*-
"""Pacote `exemplo` — as três camadas de acesso do projeto de referência.

`dados`      carrega e valida registros do domínio (sem serviço nenhum);
`cliente_llm` camada de modelo, trocável local ↔ API por variável de ambiente;
`objetos`    acesso a armazenamento compatível com S3, trocável por variável.

A regra que os três seguem: o código não sabe onde o serviço está; quem sabe
é a configuração (D4-E2 slide 25, D4-E3 slide 25). É o que faz o mesmo
código rodar no perfil completo e no perfil leve.
"""
