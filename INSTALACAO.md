# 🚀 Monitor de Criptomoedas - Guia de Instalação

## 📦 Executável Gerado

O arquivo `MonitorCriptomoedas.exe` foi criado com sucesso na pasta `dist/`.

### 📋 Requisitos do Sistema

- **Sistema Operacional**: Windows 10 ou superior
- **Memória RAM**: Mínimo 4GB (recomendado 8GB)
- **Espaço em Disco**: 100MB livres
- **Conexão com Internet**: Necessária para buscar dados das APIs

### 🎯 Como Usar

#### 1. **Execução Direta**
```bash
# Navegue até a pasta dist
cd dist

# Execute o programa
MonitorCriptomoedas.exe
```

#### 2. **Criar Atalho**
1. Clique com botão direito no `MonitorCriptomoedas.exe`
2. Selecione "Criar atalho"
3. Mova o atalho para a área de trabalho

#### 3. **Executar como Administrador** (se necessário)
1. Clique com botão direito no executável
2. Selecione "Executar como administrador"

### ⚙️ Configuração Inicial

1. **Primeira Execução**: O programa criará automaticamente os arquivos de configuração
2. **Configurar Alertas**: Acesse o menu "Configurações" para definir alertas
3. **Configurar Telegram** (opcional): Adicione seu token e chat ID do Telegram

### 🔧 Solução de Problemas

#### **Problema**: Programa não inicia
**Solução**:
- Verifique se o antivírus não está bloqueando
- Execute como administrador
- Verifique se há espaço suficiente em disco

#### **Problema**: Erro de conexão
**Solução**:
- Verifique sua conexão com a internet
- Verifique se as APIs da Binance e CoinGecko estão acessíveis

#### **Problema**: Sons não funcionam
**Solução**:
- Verifique se os arquivos de som estão na pasta `sons/`
- Verifique o volume do sistema

### 📁 Estrutura de Arquivos

```
MonitorCriptomoedas/
├── MonitorCriptomoedas.exe    # Executável principal
├── config.json                # Configurações do programa
├── icons/                     # Ícones da interface
├── sons/                      # Arquivos de som
└── analysis_log.txt          # Log de análises
```

### 🎵 Sons Disponíveis

- `Alerta.mp3` - Alerta padrão
- `cruzamentoAlta.wav` - Cruzamento de alta
- `cruzamentoBaixa.wav` - Cruzamento de baixa
- `sobrecomprado.wav` - RSI sobrecomprado
- `sobrevendido.wav` - RSI sobrevendido
- `precoAcima.wav` - Preço acima do limite
- `precoAbaixo.wav` - Preço abaixo do limite
- `volumeAlto.wav` - Volume alto
- `alertaCritico.wav` - Alerta crítico

### 🔄 Atualizações

Para atualizar o programa:
1. Faça backup das suas configurações (`config.json`)
2. Baixe a nova versão
3. Substitua o executável
4. Restaure suas configurações

### 📞 Suporte

Se encontrar problemas:
1. Verifique os logs em `analysis_log.txt`
2. Reinicie o programa
3. Verifique a conexão com a internet
4. Execute como administrador

### 🎯 Funcionalidades Principais

- ✅ Monitoramento em tempo real
- ✅ Alertas personalizáveis
- ✅ Notificações por som
- ✅ Integração com Telegram
- ✅ Análise técnica (RSI, MACD, Bollinger)
- ✅ Histórico de alertas
- ✅ Interface moderna e intuitiva

---

**🎉 Seu Monitor de Criptomoedas está pronto para uso!**