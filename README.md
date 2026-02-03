🚀 Crypto Monitor Pro
O Crypto Monitor Pro é uma ferramenta completa para monitoramento de criptomoedas em tempo real e análise histórica (backtesting). Ele combina um painel web moderno com uma ferramenta desktop robusta para testar estratégias.
📋 Funcionalidades
Monitoramento Web em Tempo Real: Acompanhe preços, RSI, MACD e tendências de várias moedas simultaneamente.
Alertas Inteligentes: Configure avisos para condições específicas (ex: RSI Sobrevendido, Cruzamento de Médias).
Backtester Desktop Pro: Uma ferramenta dedicada para simular estratégias (SMA, HMA, VWAP) em dados passados e calcular a rentabilidade (ROI).
Análise de Hit Rate: Verifique a taxa de acerto dos seus indicadores.
🛠️ Tecnologias
Frontend: React, TypeScript, Vite
Backend: Python, FastAPI
Interface Desktop: Python (Tkinter/TTKBootstrap)
⚙️ Instalação Passo a Passo
Siga estes passos se você nunca rodou o projeto antes.
1. Pré-requisitos
Certifique-se de ter instalado no seu computador:
Python (versão 3.8 ou superior): Baixar Python (Na instalação, marque a opção "Add Python to PATH").
Node.js: Baixar Node.js (Necessário para o site).
Git: Baixar Git.
2. Baixando o Projeto
Abra o seu terminal (CMD, PowerShell ou Terminal) e digite:

Bash


git clone https://github.com/PauloBennertz/MonitorCriptoWEB2.git
cd MonitorCriptoWEB2


3. Configurando o Backend (Python)
É recomendável criar um ambiente virtual para não misturar as bibliotecas.
No Windows:

Bash


python -m venv venv
venv\Scripts\activate


No Linux/Mac:

Bash


python3 -m venv venv
source venv/bin/activate


(Se aparecer (venv) no começo da linha do terminal, deu certo!)
Agora, instale as bibliotecas necessárias:

Bash


pip install -r requirements.txt


⚠️ Importante: Como adicionamos novas funções recentemente, execute também este comando para garantir que tudo funcione:

Bash


pip install matplotlib pandas_ta


4. Configurando o Frontend (Site)
Ainda na pasta do projeto, instale as dependências do site:

Bash


npm install


▶️ Como Executar
O sistema possui duas partes principais. Você precisará de dois terminais abertos para rodar o sistema web completo.
1. Iniciar o Servidor (API)
Este passo liga o "cérebro" do sistema. No primeiro terminal (com o ambiente virtual ativado), execute:

Bash


uvicorn backend.api_server:app --reload


Se tudo der certo, você verá mensagens dizendo que o servidor iniciou em http://127.0.0.1:8000.
Deixe esse terminal aberto.
2. Iniciar o Painel Web
No segundo terminal, execute:

Bash


npm run dev


O terminal mostrará um link (geralmente http://localhost:5173).
Abra esse link no seu navegador para ver o painel de monitoramento.
3. Iniciar o Backtester Desktop (Ferramenta de Análise)
Se você quiser usar a ferramenta de simulação histórica (que calcula lucro, prejuízo e taxa de acerto) sem abrir o navegador, você pode rodar a interface dedicada.
Em um terminal (com o venv ativado), execute:

Bash


python -m backend.gui_backtester


Isso abrirá uma janela onde você pode:
Escolher a moeda (ex: BTCUSDT).
Definir datas e capital inicial.
Escolher a estratégia (SMA, HMA, VWAP).
Ver gráficos detalhados de performance.
❓ Resolução de Problemas Comuns
Erro "module not found": Certifique-se de que ativou o ambiente virtual (venv\Scripts\activate) antes de rodar os comandos Python.
O gráfico não aparece: Verifique se instalou o matplotlib conforme indicado no passo 3.
Erro de Permissão no Windows: Se o PowerShell bloquear a ativação do venv, abra-o como Administrador e rode: Set-ExecutionPolicy RemoteSigned.
🤝 Contribuição
Faça um Fork do projeto
Crie uma Branch (git checkout -b feature/NovaFeature)
Commit suas mudanças (git commit -m 'Adiciona nova feature')
Push para a Branch (git push origin feature/NovaFeature)
Abra um Pull Request
