# Protocolo de Comunicação P2P

Este projeto implementa um protocolo de comunicação customizado encapsulado em pacotes UDP para busca automática de dispositivos em uma topologia de rede.

## Funcionalidades

- Descoberta automática de dispositivos na rede através de mensagens HEARTBEAT
- Envio de mensagens de texto entre dispositivos
- Transferência confiável de arquivos com verificação de integridade
- Interface de linha de comando interativa

## Requisitos

- Python 3.6 ou superior
- Não são necessárias bibliotecas externas além da biblioteca padrão do Python

## Como usar

1. Inicie o programa em cada dispositivo que deseja participar da rede:

```bash
python main.py <nome_dispositivo> <porta>
```

Por exemplo:
```bash
python main.py dispositivo1 5000
```

2. Comandos disponíveis:

- `devices`: Lista todos os dispositivos ativos na rede
- `talk <nome_dispositivo> <mensagem>`: Envia uma mensagem para um dispositivo específico
- `sendfile <nome_dispositivo> <caminho_arquivo>`: Envia um arquivo para um dispositivo específico
- `quit`: Sai do programa

## Detalhes do Protocolo

O protocolo implementa os seguintes tipos de mensagens:

1. HEARTBEAT
   - Enviado a cada 5 segundos
   - Formato: `HEARTBEAT <nome>`

2. TALK
   - Para envio de mensagens de texto
   - Formato: `TALK <id> <dados>`
   - Requer confirmação (ACK)

3. FILE
   - Inicia transferência de arquivo
   - Formato: `FILE <id> <nome-arquivo> <tamanho>`
   - Requer confirmação (ACK)

4. CHUNK
   - Transfere parte de um arquivo
   - Formato: `CHUNK <id> <seq> <dados>`
   - Requer confirmação (ACK)

5. END
   - Finaliza transferência de arquivo
   - Formato: `END <id> <hash>`
   - Requer confirmação (ACK/NACK)

## Mecanismos de Confiabilidade

- Confirmação de recebimento (ACK) para todas as mensagens
- Retransmissão automática em caso de perda de pacotes
- Detecção e eliminação de mensagens duplicadas
- Ordenação correta de chunks de arquivo
- Verificação de integridade por hash SHA-256
- Transferência de arquivos em blocos para suportar arquivos grandes

## Limitações

- O programa utiliza broadcast UDP, então todos os dispositivos devem estar na mesma rede local
- A porta especificada deve estar disponível para uso
- Arquivos com o mesmo nome serão sobrescritos ao serem recebidos 