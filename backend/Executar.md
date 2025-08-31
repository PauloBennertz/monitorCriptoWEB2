# Backend API para o Monitor de Criptomoedas

Este diretório contém o servidor de API backend para a aplicação Crypto Monitor Pro. É construído usando FastAPI e serve os dados processados para o frontend React.

## Configuração

1.  **Navegue até o diretório raiz do projeto.**

2.  **Instale as dependências Python:**
    É recomendado criar um ambiente virtual primeiro.

    ```bash
    pip install -r backend/requirements.txt
    ```
    (Nota: O `requirements.txt` original foi modificado para incluir `fastapi` e `uvicorn` e remover pacotes de GUI desnecessários).

## Como Rodar o Servidor

1.  **A partir do diretório raiz do projeto**, execute o seguinte comando:

    ```bash
    uvicorn backend.api_server:app --reload --port 8000
    ```

2.  O servidor da API estará agora rodando em `http://localhost:8000`.

O frontend React (que deve ser iniciado separadamente com `npm run dev`) irá se conectar a esta API para buscar todos os seus dados.
