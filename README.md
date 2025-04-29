# Protocolo de Comunicação Customizado sobre UDP

Este projeto implementa um protocolo de comunicação customizado sobre UDP para descoberta automática de dispositivos e transferência de arquivos em uma rede local.

## Funcionalidades

- Descoberta automática de dispositivos na rede
- Envio de mensagens entre dispositivos
- Transferência de arquivos com verificação de integridade
- Interface de linha de comando interativa

## Requisitos

- Python 3.8 ou superior
- Dependências listadas em requirements.txt

## Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Uso

Para iniciar um dispositivo:
```bash
python main.py <nome_do_dispositivo>
```

### Comandos disponíveis

- `devices`: Lista todos os dispositivos ativos na rede
- `talk <nome> <mensagem>`: Envia uma mensagem para um dispositivo específico
- `sendfile <nome> <nome-arquivo>`: Envia um arquivo para um dispositivo específico 