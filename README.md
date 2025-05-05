# Laboratório de Redes de Computadores - Trabalho 1

## Descrição
Este trabalho implementa um protocolo de comunicação P2P (peer-to-peer) baseado em UDP para descoberta de dispositivos e transferência confiável de mensagens e arquivos. O protocolo suporta:

- Descoberta automática de dispositivos na rede local via broadcast
- Comunicação confiável entre pares
- Transferência de arquivos com verificação de integridade
- Tratamento de perdas, duplicações e reordenação de pacotes
- Logs detalhados para análise e depuração

## Requisitos
- Python 3.6 ou superior
- Sistema operacional Windows, Linux ou macOS
- Acesso à rede local
- Permissões para abrir portas UDP (5000-5010)

## Instalação
1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/Laboratorio-Redes-T1.git
cd Laboratorio-Redes-T1
```

2. Certifique-se de ter o Python instalado:
```bash
python --version
```

## Como Executar
1. Abra dois ou mais terminais
2. Em cada terminal, execute o programa com um nome e porta diferentes:
```bash
# Terminal 1
python main.py dispositivo1 5000

# Terminal 2
python main.py dispositivo2 5001
```

## Funcionalidades

### Descoberta de Dispositivos
- Os dispositivos enviam HEARTBEATs a cada 5 segundos via broadcast
- Dispositivos inativos são removidos após 10 segundos sem heartbeat
- Lista de dispositivos ativos é atualizada automaticamente

### Envio de Mensagens
- Comando: `talk <nome> <mensagem>`
- Exemplo: `talk dispositivo2 Olá, como vai?`
- Confirmação de recebimento via ACK
- Retransmissão automática em caso de falha

### Transferência de Arquivos
- Comando: `sendfile <nome> <arquivo>`
- Exemplo: `sendfile dispositivo2 documento.txt`
- Transferência em blocos de 1KB
- Verificação de integridade via hash SHA-256
- Confirmação de cada bloco via ACK
- Retransmissão automática em caso de falha

## Logs e Depuração
- Logs detalhados são salvos em arquivos:
  - `logs_dispositivo.log`: Logs do dispositivo
  - `logs_interface.log`: Logs da interface
- Mensagens importantes são exibidas no terminal
- Logs incluem timestamps e níveis de severidade

## Testes e Simulação de Falhas
Para testar o protocolo em condições adversas:

1. Use o Wireshark para capturar pacotes:
   - Filtro: `udp port 5000-5010`
   - Observe HEARTBEATs (broadcast) e mensagens unicast

2. Use o Clumsy para simular falhas:
   - Download: [Clumsy](https://jagt.github.io/clumsy/)
   - Configure para:
     - Perda de pacotes (10-20%)
     - Duplicação (5-10%)
     - Atraso (100-200ms)
     - Reordenação (5-10%)

## Protocolo

### Mensagens
1. **HEARTBEAT** (broadcast)
   - Formato: `HEARTBEAT <nome>`
   - Enviado a cada 5 segundos
   - Usado para descoberta de dispositivos

2. **TALK** (unicast)
   - Formato: `TALK <id> <mensagem>`
   - Requer ACK de confirmação
   - ID único para evitar duplicatas

3. **FILE** (unicast)
   - Formato: `FILE <id> <nome> <tamanho>`
   - Inicia transferência de arquivo
   - Requer ACK de confirmação

4. **CHUNK** (unicast)
   - Formato: `CHUNK <id> <seq> <dados_base64>`
   - Transfere bloco do arquivo
   - Requer ACK de confirmação

5. **END** (unicast)
   - Formato: `END <id> <hash>`
   - Finaliza transferência
   - Verifica integridade via hash

6. **ACK** (unicast)
   - Formato: `ACK <id> [seq|END]`
   - Confirma recebimento

7. **NACK** (unicast)
   - Formato: `NACK <id> <motivo>`
   - Indica falha na transferência

## Solução de Problemas

### Problemas Comuns
1. **Só vejo HEARTBEAT no Wireshark**
   - Verifique se está capturando na interface correta
   - Confirme que o firewall permite tráfego UDP
   - Use filtro `udp port 5000-5010`

2. **Transferência de arquivo falha**
   - Verifique permissões de arquivo
   - Confirme espaço em disco
   - Monitore logs para identificar erro específico

3. **Dispositivos não se encontram**
   - Verifique se estão na mesma rede
   - Confirme se broadcast está funcionando
   - Verifique logs para HEARTBEATs

### Configuração do Firewall
No Windows:
1. Abra "Firewall do Windows com Segurança Avançada"
2. Crie regra de entrada para UDP 5000-5010
3. Permita tráfego de/para programas Python

## Contribuições
Contribuições são bem-vindas! Por favor, abra uma issue ou pull request.

## Licença
Este projeto está licenciado sob a MIT License - veja o arquivo LICENSE para detalhes. 