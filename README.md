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

## Testes em Condições Adversas

Para validar a robustez do protocolo, recomenda-se o uso das ferramentas **Wireshark** (para capturar pacotes) e **Clumsy** (para simular falhas de rede no Windows).

### Como usar o Clumsy

1. Baixe o Clumsy: https://jagt.github.io/clumsy/
2. Abra o Clumsy e selecione a interface de rede correta.
3. Marque as opções conforme o teste desejado:
   - **Drop:** Simula perda de pacotes (ex: 10%)
   - **Duplicate:** Simula duplicação de pacotes (ex: 10%)
   - **Lag:** Simula atraso (ex: 200ms)
   - **Out of order:** Simula entrega fora de ordem (ex: 10%)
   - **Tamper:** Simula corrupção de pacotes (ex: 10%)
4. Clique em Start para ativar as falhas.
5. Execute os testes normalmente no programa.
6. Desative o Clumsy após o teste.

### Exemplos de Cenários para Teste

- **Normal:** Nenhuma opção marcada (funcionamento padrão)
- **Perda de pacotes:** Drop 10%
- **Duplicação:** Duplicate 10%
- **Atraso:** Lag 200ms
- **Fora de ordem:** Out of order 10%
- **Corrupção:** Tamper 10%
- **Combinado:** Drop + Lag + Duplicate

### Usando o Wireshark

1. Abra o Wireshark e selecione a interface de rede.
2. Inicie a captura antes de rodar o programa.
3. Filtre por porta UDP usada (ex: `udp.port == 5000`).
4. Salve o arquivo `.pcapng` após o teste.

### Arquivo de Teste

Incluído no repositório: `grande_teste.txt` (arquivo de texto grande para testar transferência de arquivos).

## Limitações

- O programa utiliza broadcast UDP, então todos os dispositivos devem estar na mesma rede local
- A porta especificada deve estar disponível para uso
- Arquivos com o mesmo nome serão sobrescritos ao serem recebidos 