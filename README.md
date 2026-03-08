# Trabalhos Práticos de Computação Móvel

Este repo serve para guardar e apresentar os trabalhos práticos da cadeira.

# 📝 Gestor de Tarefas

Este é o meu primeiro trabalho e consiste num gestor de tarefas com armazenamento local e encriptação fernet.

## Funcionalidades

- Criar, editar e apagar tarefas
- Marcar tarefas como concluidas ou por concluir
- Filtrar por `All`, `Active` e `Completed`
- Guardar dados localmente
- Encriptar dados com Fernet

## Requisitos

- Python 3.11+
- Ambiente virtual (`venv`)

## Instalacao

1. Criar e ativar ambiente virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

2. Instalar dependencias:

```bash
cd gestor-de-tarefas
pip install -r requirements.txt
```

3. Gerar chave Fernet:

```bash
python src/encryption.py
```

4. Criar ficheiro `.env` com base no exemplo:

```bash
copy .env.example .env
```

5. No ficheiro `.env`, definir:

```env
FERNET_KEY=sua_chave_aqui
```

## Executar

```bash
cd gestor-de-tarefas
python src/main.py
```

Ou com Flet:

```bash
flet run src/main.py
```

