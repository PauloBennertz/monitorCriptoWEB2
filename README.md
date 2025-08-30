# 🚀 Monitor de Criptomoedas v3.1

## 📋 Descrição
Monitor de criptomoedas em tempo real com sistema de alertas automáticos.

## 🛠️ Tecnologias
- **Python 3.8+**
- **tkinter + ttkbootstrap** (Interface)
- **CoinGecko API** (Dados de criptomoedas)
- **Binance API** (Dados de mercado)
- **PyInstaller** (Executável)

## 🚀 Instalação

### Desenvolvimento
```bash
# Clone o repositório
git clone https://github.com/PauloBennertz/MonitorCriptomoedas3.1.git
cd MonitorCriptomoedas3.1

# Crie ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instale dependências
pip install -r requirements.txt
```

### Executável
1. Baixe o arquivo `MonitorCriptomoedas.exe` da seção Releases
2. Execute o arquivo
3. Configure os alertas no menu "Configurações"

## 📁 Estrutura do Projeto

```
MonitorCriptomoedas3.1/
├── main_app.py              # Aplicação principal
├── monitoring_service.py     # Serviços de monitoramento
├── notification_service.py   # Sistema de alertas
├── core_components.py       # Componentes da interface
├── api_config_window.py     # Configuração de APIs
├── build_exe.py            # Script de build
├── config.json             # Configurações
├── icons/                  # Ícones da interface
├── sons/                   # Arquivos de som
└── requirements.txt        # Dependências
```

## ⚙️ Configuração

### APIs Necessárias
- **CoinGecko**: Gratuita (sem chave)
- **Binance**: Gratuita (sem chave)

### Alertas Configuráveis
- ✅ Preço acima/abaixo de valor
- ✅ Variação percentual
- ✅ Volume de negociação
- ✅ Sons personalizados por tipo
- ✅ Notificações automáticas

## 🎯 Funcionalidades

### Monitoramento
- 📊 Preços em tempo real
- 📈 Gráficos de variação
- 💰 Dominância do Bitcoin
- 🔄 Atualização automática

### Alertas
-  Sons automáticos
- 📱 Notificações Windows
-  Alertas Telegram (opcional)
- ⚡ Consolidação de múltiplos alertas

### Interface
-  Design moderno com ttkbootstrap
- 📱 Responsiva
- ⚙️ Menu de configurações
-  Histórico de alertas

## 🔧 Desenvolvimento

### Build do Executável
```bash
python build_exe.py
```

### Testes
```bash
python main_app.py
```

##  Changelog

### v3.1
- ✅ Sistema de sons automáticos
- ✅ Menu de configurações avançado
- ✅ Consolidação de alertas
- ✅ Interface moderna com ttkbootstrap
- ✅ Build otimizado para PyInstaller

## 🤝 Contribuição
1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença
Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🆘 Suporte
Se encontrar problemas:
1. Verifique a conexão com internet
2. Execute como administrador
3. Verifique o antivírus
4. Abra uma issue no GitHub

---
**Desenvolvido com ❤️ para a comunidade crypto**
