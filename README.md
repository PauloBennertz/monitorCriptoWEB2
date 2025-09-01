# 🚀 Crypto Monitor Pro

Monitor de criptomoedas em tempo real com sistema de alertas configurável, construído com React e FastAPI.

## 📋 Descrição
Esta aplicação web fornece uma visão geral do mercado de criptomoedas, permitindo aos usuários monitorar métricas chave em tempo real e configurar alertas personalizados para várias condições de mercado.

## 🛠️ Tecnologias
- **Frontend**: React, TypeScript, Vite
- **Backend**: Python, FastAPI
- **APIs de Dados**: CoinGecko, Binance
- **Gerenciamento de Pacotes**: npm (frontend), pip (backend)

## 🚀 Instalação e Execução

### Pré-requisitos
- Node.js e npm
- Python 3.8+ e pip

### Passos
1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/PauloBennertz/MonitorCriptomoedas3.1.git
    cd MonitorCriptomoedas3.1
    ```

2.  **Instale as dependências do Backend:**
    Recomenda-se o uso de um ambiente virtual.
    ```bash
    pip install -r backend/requirements.txt
    ```

3.  **Instale as dependências do Frontend:**
    ```bash
    npm install
    ```

4.  **Execute o Servidor da API (Backend):**
    A partir do diretório raiz do projeto, execute:
    ```bash
    uvicorn backend.api_server:app --reload --port 8000
    ```
    O servidor da API estará disponível em `http://localhost:8000`.

5.  **Execute a Aplicação (Frontend):**
    Em um novo terminal, a partir do diretório raiz do projeto, execute:
    ```bash
    npm run dev
    ```
    A aplicação web estará acessível em `http://localhost:5173`.

## 📁 Estrutura do Projeto (Simplificada)
```
/
├── backend/                # Código da API em Python/FastAPI
│   ├── api_server.py       # Ponto de entrada e rotas da API
│   ├── monitoring_service.py # Lógica de busca e análise de dados
│   └── ...
├── src/                    # Código do frontend em React/TypeScript (a ser criado)
│   ├── components/         # Componentes React reutilizáveis (a ser criado)
│   ├── index.css           # Estilos globais
│   └── index.tsx           # Ponto de entrada da aplicação React
├── package.json            # Dependências e scripts do frontend
└── README.md               # Este arquivo
```

## 🎯 Funcionalidades
- **Monitoramento em Tempo Real**: Veja preços, capitalização de mercado, volume e indicadores técnicos atualizados automaticamente.
- **Alertas Configuráveis**: Configure alertas para condições como RSI, cruzamentos de médias móveis, sinais de MACD e mais.
- **Interface Intuitiva**: Um painel de controle claro e fácil de usar para visualizar os dados.
- **Adicionar/Remover Moedas**: Personalize sua lista de moedas monitoradas.

## 🤝 Contribuição
1.  Fork o projeto
2.  Crie uma branch (`git checkout -b feature/AmazingFeature`)
3.  Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4.  Push para a branch (`git push origin feature/AmazingFeature`)
5.  Abra um Pull Request
