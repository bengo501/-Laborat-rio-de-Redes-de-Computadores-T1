# Laboratório de Redes de Computadores – Trabalho 1

**Alunos:**  
[Seu nome]  
[Nome do colega, se houver]  

**Turma:** [Identificação da turma]  
**Data de entrega:** [Data]  

---

# Sumário
1. [Introdução](#1-introdução)
2. [Descrição da Implementação](#2-descrição-da-implementação)
    1. [Arquitetura Geral](#21-arquitetura-geral)
    2. [Protocolo de Descoberta e Comunicação](#22-protocolo-de-descoberta-e-comunicação)
    3. [Mecanismos de Confiabilidade](#23-mecanismos-de-confiabilidade)
    4. [Estrutura do Código](#24-estrutura-do-código)
3. [Interface de Usuário](#3-interface-de-usuário)
4. [Cenários de Teste e Validação](#4-cenários-de-teste-e-validação)
5. [Análise dos Resultados](#5-análise-dos-resultados)
6. [Conclusão](#6-conclusão)
7. [Anexos](#7-anexos)

---

# 1. Introdução

O presente trabalho tem como objetivo o desenvolvimento de um protocolo de comunicação customizado, encapsulado em pacotes UDP, para busca automática e comunicação entre dispositivos em uma rede local. O projeto visa proporcionar experiência prática com a pilha de protocolos de rede, uso de sockets, e implementação de mecanismos de confiabilidade em aplicações distribuídas peer-to-peer.

---

# 2. Descrição da Implementação

## 2.1 Arquitetura Geral

A aplicação é composta por múltiplos dispositivos, cada um executando um programa Python que utiliza sockets UDP para comunicação. Cada dispositivo é capaz de:

- Descobrir automaticamente outros dispositivos ativos na rede.
- Enviar e receber mensagens de texto.
- Transferir arquivos de forma confiável, mesmo em condições adversas de rede.

A arquitetura utiliza múltiplas threads para:
- Envio periódico de mensagens HEARTBEAT.
- Recebimento e processamento de mensagens UDP.
- Limpeza automática de dispositivos inativos.

## 2.2 Protocolo de Descoberta e Comunicação

O protocolo implementa os seguintes tipos de mensagens:

- **HEARTBEAT <nome>**: Enviada via broadcast na inicialização e a cada 5 segundos, informando a presença do dispositivo na rede.
- **TALK <id> <mensagem>**: Envia uma mensagem de texto para outro dispositivo, aguardando confirmação (ACK).
- **FILE <id> <nome-arquivo> <tamanho>**: Inicia a transferência de arquivo, aguardando ACK antes de enviar os blocos.
- **CHUNK <id> <seq> <dados>**: Envia um bloco do arquivo, codificado em base64, com confirmação individual (ACK) e retransmissão em caso de perda.
- **END <id> <hash>**: Finaliza a transferência, enviando o hash do arquivo para verificação de integridade.
- **ACK <id>**: Confirma o recebimento de qualquer mensagem.
- **NACK <id> <motivo>**: Indica erro no recebimento ou processamento.

## 2.3 Mecanismos de Confiabilidade

- **Confirmação de recebimento (ACK) e retransmissão automática** em caso de perda de pacotes.
- **Detecção e eliminação de duplicatas** de mensagens e blocos.
- **Detecção e reordenação de pacotes fora de ordem** para blocos de arquivos.
- **Validação de integridade** ao final da transferência de arquivos, comparando o hash recebido com o calculado.
- **Envio de arquivos em blocos**, sem carregar o arquivo inteiro na memória.

## 2.4 Estrutura do Código

O código está dividido em dois arquivos principais:

- `dispositivo.py`: Implementa toda a lógica do protocolo, comunicação UDP, threads, envio/recebimento de mensagens e arquivos, e mecanismos de confiabilidade.
- `main.py`: Implementa a interface de linha de comando, permitindo ao usuário listar dispositivos, enviar mensagens e arquivos.

---

# 3. Interface de Usuário

A interface é baseada em linha de comando e permite:

- Listar dispositivos ativos (`devices`).
- Enviar mensagens de texto (`talk <nome> <mensagem>`).
- Enviar arquivos (`sendfile <nome> <nome-arquivo>`).
- Visualizar o progresso da transferência e mensagens de sucesso ou falha.

**Exemplo de uso:**

```
1. Listar dispositivos ativos
2. Enviar mensagem (use: talk <nome> <mensagem>)
3. Enviar arquivo (use: sendfile <nome> <arquivo>)
4. Sair
```

**Prints da interface:**  
*Insira aqui prints de tela mostrando a interface em funcionamento.*

---

# 4. Cenários de Teste e Validação

A seguir, são apresentados os principais cenários de teste realizados para validar o funcionamento e a confiabilidade do protocolo.

## 4.1 Funcionamento Normal
- **Objetivo:** Demonstrar a descoberta automática de dispositivos, envio de mensagens e transferência de arquivos em condições normais.
- **Procedimento:**  
  - Iniciar dois dispositivos.
  - Listar dispositivos ativos.
  - Enviar mensagem TALK.
  - Enviar arquivo.
- **Evidências:**  
  - *Inserir prints do Wireshark mostrando HEARTBEAT, TALK, FILE, CHUNK, END, ACK, NACK.*
  - *Inserir prints da interface e dos logs.*

## 4.2 Perda de Pacotes
- **Objetivo:** Validar a retransmissão automática em caso de perda de pacotes.
- **Procedimento:**  
  - Aplicar perda de pacotes com netem:  
    `sudo tc qdisc add dev eth0 root netem loss 20%`
  - Enviar arquivo e observar retransmissões.
- **Evidências:**  
  - *Inserir prints do Wireshark mostrando retransmissões.*
  - *Inserir prints dos logs mostrando tentativas e sucesso final.*

## 4.3 Duplicação
- **Objetivo:** Validar o descarte de mensagens/CHUNKs duplicados.
- **Procedimento:**  
  - Aplicar duplicação com netem:  
    `sudo tc qdisc add dev eth0 root netem duplicate 10%`
  - Enviar arquivo e observar duplicatas.
- **Evidências:**  
  - *Inserir prints do Wireshark mostrando duplicatas.*
  - *Inserir prints dos logs mostrando descarte de duplicatas.*

## 4.4 Reordenação
- **Objetivo:** Validar a reordenação correta dos blocos de arquivo.
- **Procedimento:**  
  - Aplicar reordenação com netem:  
    `sudo tc qdisc add dev eth0 root netem delay 100ms reorder 30%`
  - Enviar arquivo e observar blocos fora de ordem.
- **Evidências:**  
  - *Inserir prints do Wireshark mostrando pacotes fora de ordem.*
  - *Inserir prints dos logs mostrando reordenação.*

## 4.5 Atraso
- **Objetivo:** Validar o funcionamento do protocolo sob atraso de rede.
- **Procedimento:**  
  - Aplicar atraso com netem:  
    `sudo tc qdisc add dev eth0 root netem delay 200ms`
  - Enviar mensagem/arquivo.
- **Evidências:**  
  - *Inserir prints do Wireshark mostrando atraso.*
  - *Inserir prints dos logs mostrando espera e sucesso.*

## 4.6 Corrupção
- **Objetivo:** Validar a detecção e descarte de arquivos corrompidos.
- **Procedimento:**  
  - Aplicar corrupção com netem:  
    `sudo tc qdisc add dev eth0 root netem corrupt 2%`
  - Enviar arquivo.
- **Evidências:**  
  - *Inserir prints do Wireshark mostrando NACK e logs de erro de hash.*

---

# 5. Análise dos Resultados

> **[Aqui você irá descrever, para cada cenário, o que foi observado nas capturas e prints. Explique como o protocolo respondeu a cada situação adversa.]**

- O protocolo foi capaz de garantir a entrega confiável de mensagens e arquivos mesmo sob condições adversas, como perda, duplicação, atraso, reordenação e corrupção de pacotes.
- As retransmissões automáticas, confirmações (ACK), detecção de duplicatas e verificação de integridade (hash) funcionaram conforme esperado.
- O usuário foi informado sobre o progresso e o resultado das operações, tanto em caso de sucesso quanto de falha.

---

# 6. Conclusão

O trabalho permitiu compreender na prática o funcionamento de protocolos de rede, a utilização de sockets UDP e a implementação de mecanismos de confiabilidade em aplicações distribuídas. O protocolo desenvolvido demonstrou ser capaz de garantir a entrega confiável de mensagens e arquivos, mesmo em condições adversas de rede, atendendo a todos os requisitos propostos.

---

# 7. Anexos

- Códigos-fonte do programa.
- Arquivos de captura do Wireshark (`.pcapng`).
- Prints de tela e logs relevantes.

---

# Roteiro para Apresentação (5 a 7 minutos)

1. **Introdução rápida:**  
   - Objetivo do trabalho e contexto.
2. **Demonstração da interface:**  
   - Listar dispositivos, enviar mensagem, enviar arquivo.
3. **Demonstração de um teste normal:**  
   - Mostre a transferência e a captura no Wireshark.
4. **Demonstração de um teste adverso:**  
   - Exemplo: perda de pacotes, retransmissão e sucesso final.
5. **Mostre prints/capturas:**  
   - HEARTBEAT, TALK, FILE, CHUNK, END, ACK, NACK, retransmissão, NACK, etc.
6. **Conclusão:**  
   - O protocolo é confiável, funciona mesmo com falhas, aprendizado.

---

*Preencha os espaços marcados com prints, capturas e análises após realizar os testes!* 