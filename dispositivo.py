# importa socket para comunicação udp entre dispositivos
import socket
# importa threading para executar tarefas em paralelo (ex: envio de heartbeat e recebimento de mensagens)
import threading
# importa time para controlar intervalos e medir inatividade
import time
# importa base64 para codificar arquivos em texto ao transferir
import base64
# importa hashlib para calcular hash dos arquivos e garantir integridade
import hashlib
# importa json para serializar e desserializar mensagens
import json
# importa os para manipulação de arquivos e caminhos
import os
# importa tipos para anotações de variáveis e funções
from typing import Dict, List, Optional
# importa datetime para registrar logs com data e hora
from datetime import datetime

# tamanho do bloco para transferência de arquivos (1KB)
CHUNK_SIZE = 1024

# classe que representa um dispositivo p2p na rede
class Dispositivo:
    # método construtor, inicializa variáveis, socket e threads
    def __init__(self, nome: str, porta: int):
        # armazena o nome do dispositivo, usado nas mensagens
        self.nome = nome
        # armazena a porta udp usada para comunicação
        self.porta = porta
        # cria socket udp, habilita reuso de endereço e broadcast
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # define endereço de broadcast para enviar mensagens a todos na rede local
        self.broadcast_address = '255.255.255.255'
        # vincula o socket a todas as interfaces na porta especificada
        self.socket.bind(('0.0.0.0', porta))
        # dicionário para armazenar dispositivos ativos (nome -> (ip, porta, timestamp))
        self.dispositivos_ativos: Dict[str, tuple] = {}
        # dicionário para ids de mensagens recebidas, evita processar duplicatas
        self.mensagens_recebidas: Dict[str, set] = {}
        # dicionário para controle de arquivos recebidos (id -> dados do arquivo)
        self.arquivos_recebidos: Dict[str, dict] = {}
        # dicionário para controle de ACKs recebidos (id -> timestamp)
        self.acks_recebidos: Dict[str, float] = {}
        # estado atual de envio de arquivo
        self.estado_envio_arquivo: Optional[dict] = None
        # abre arquivo de log para registrar eventos importantes
        self.log_file = open(f"logs_{nome}.txt", "w")
        # registra no log a inicialização do dispositivo
        self._log(f"Dispositivo {nome} inicializado na porta {porta}")
        self._log(f"Usando endereço de broadcast: {self.broadcast_address}")
        # flag para controlar execução das threads
        self.running = True
        # cria threads para heartbeat, recebimento e limpeza de inativos
        self.thread_heartbeat = threading.Thread(target=self._enviar_heartbeat)
        self.thread_receiver = threading.Thread(target=self._receber_mensagens)
        self.thread_cleanup = threading.Thread(target=self._limpar_inativos)
        # inicia as threads
        self.thread_heartbeat.start()
        self.thread_receiver.start()
        self.thread_cleanup.start()

    # registra mensagem no log com timestamp, pode exibir na tela se mostrar_tela for True
    def _log(self, mensagem: str, mostrar_tela: bool = True):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        log_entry = f"[{timestamp}] {mensagem}\n"
        if mostrar_tela:
            print(log_entry.strip())
        self.log_file.write(log_entry)
        self.log_file.flush()

    # envia heartbeat para todos os dispositivos da rede a cada 5 segundos
    def _enviar_heartbeat(self):
        while self.running:
            # monta a mensagem heartbeat com o nome do dispositivo
            mensagem = f"HEARTBEAT {self.nome}"
            try:
                # envia heartbeat para todas as portas do intervalo 5000-5010
                for porta in range(5000, 5010):
                    self.socket.sendto(mensagem.encode(), (self.broadcast_address, porta))
                    # registra no log o envio do heartbeat
                    self._log(f"HEARTBEAT enviado para {self.broadcast_address}:{porta}", mostrar_tela=False)
            except Exception as e:
                self._log(f"ERRO ao enviar HEARTBEAT: {e}")
            # espera 5 segundos antes de enviar o próximo heartbeat
            time.sleep(5)

    # remove dispositivos inativos da lista se não receber heartbeat em 10 segundos
    def _limpar_inativos(self):
        while self.running:
            agora = time.time()
            # percorre todos os dispositivos ativos
            for nome in list(self.dispositivos_ativos.keys()):
                ip, porta, ultimo_heartbeat = self.dispositivos_ativos[nome]
                # verifica se o dispositivo está inativo há mais de 10 segundos
                if agora - ultimo_heartbeat > 10:
                    self._log(f"Dispositivo {nome} removido por inatividade")
                    del self.dispositivos_ativos[nome]
            # espera 1 segundo antes de verificar novamente
            time.sleep(1)

    # recebe e processa mensagens udp enquanto o dispositivo estiver rodando
    def _receber_mensagens(self):
        while self.running:
            try:
                # recebe dados e endereço de origem
                dados, endereco = self.socket.recvfrom(65536)
                mensagem = dados.decode()
                self._log(f"RECEBIDO de {endereco}: {mensagem}", mostrar_tela=False)
                partes = mensagem.split()
                if not partes:
                    continue
                tipo_mensagem = partes[0]
                # verifica o tipo da mensagem e chama o método correspondente
                if tipo_mensagem == "HEARTBEAT":
                    self._processar_heartbeat(partes, endereco)
                elif tipo_mensagem == "TALK":
                    self._processar_talk(partes, endereco)
                elif tipo_mensagem == "FILE":
                    self._processar_file(partes, endereco)
                elif tipo_mensagem == "CHUNK":
                    self._processar_chunk(partes, endereco)
                elif tipo_mensagem == "END":
                    self._processar_end(partes, endereco)
                elif tipo_mensagem == "ACK":
                    self._processar_ack(partes, endereco)
                elif tipo_mensagem == "NACK":
                    self._processar_nack(partes, endereco)
            except Exception as e:
                self._log(f"ERRO ao receber mensagem: {e}")

    # processa heartbeat recebido, atualiza ou adiciona dispositivo na lista
    def _processar_heartbeat(self, partes: List[str], endereco):
        if len(partes) < 2:
            return
        nome_dispositivo = partes[1]
        ip, porta = endereco
        # ignora heartbeats do próprio dispositivo
        if nome_dispositivo == self.nome:
            return
        # se for novo dispositivo, registra no log
        if nome_dispositivo not in self.dispositivos_ativos:
            self._log(f"Novo dispositivo descoberto: {nome_dispositivo} em {ip}:{porta}")
        else:
            ip_antigo, porta_antiga, _ = self.dispositivos_ativos[nome_dispositivo]
            if ip != ip_antigo or porta != porta_antiga:
                self._log(f"Dispositivo {nome_dispositivo} mudou de endereço: {ip_antigo}:{porta_antiga} -> {ip}:{porta}")
        # atualiza timestamp do último heartbeat
        self.dispositivos_ativos[nome_dispositivo] = (ip, porta, time.time())

    # processa mensagem TALK, exibe mensagem recebida e envia ACK
    def _processar_talk(self, partes: List[str], endereco):
        if len(partes) < 3:
            return
        id_msg = partes[1]
        mensagem = " ".join(partes[2:])
        # evita processar mensagens duplicadas
        if id_msg not in self.mensagens_recebidas.get("TALK", set()):
            print(f"\nMensagem recebida: {mensagem}")
            self._log(f"Mensagem recebida de {endereco[0]}: {mensagem}", mostrar_tela=False)
            self.mensagens_recebidas.setdefault("TALK", set()).add(id_msg)
        # envia ACK para confirmar recebimento
        resposta = f"ACK {id_msg}"
        self.socket.sendto(resposta.encode(), endereco)

    # envia mensagem TALK para outro dispositivo, aguarda ACK e retransmite se necessário
    def enviar_mensagem(self, nome_destino: str, mensagem: str):
        if nome_destino not in self.dispositivos_ativos:
            print(f"Erro: Dispositivo {nome_destino} não encontrado")
            return
        ip, porta, _ = self.dispositivos_ativos[nome_destino]
        id_msg = f"{self.nome}_{int(time.time())}"
        mensagem_completa = f"TALK {id_msg} {mensagem}"
        self._log(f"ENVIANDO TALK para {ip}:{porta} (ID: {id_msg}): {mensagem}", mostrar_tela=False)
        max_tentativas = 3
        tentativa = 0
        while tentativa < max_tentativas:
            self.socket.sendto(mensagem_completa.encode(), (ip, porta))
            try:
                self.socket.settimeout(2)
                while True:
                    dados, _ = self.socket.recvfrom(1024)
                    resposta = dados.decode().split()
                    if len(resposta) >= 2 and resposta[0] == "ACK" and resposta[1] == id_msg:
                        self._log(f"ACK recebido para mensagem {id_msg}", mostrar_tela=False)
                        return
            except socket.timeout:
                tentativa += 1
                if tentativa < max_tentativas:
                    self._log(f"Tentativa {tentativa + 1} de enviar mensagem {id_msg}...", mostrar_tela=False)
                else:
                    self._log(f"Falha ao enviar mensagem {id_msg} após {max_tentativas} tentativas", mostrar_tela=False)
            finally:
                self.socket.settimeout(None)

    # lista dispositivos ativos, filtrando por último heartbeat menor que 10 segundos
    def listar_dispositivos(self):
        agora = time.time()
        dispositivos_ativos = {}
        for nome, (ip, porta, ultimo_heartbeat) in self.dispositivos_ativos.items():
            if agora - ultimo_heartbeat < 10:
                dispositivos_ativos[nome] = (ip, porta, ultimo_heartbeat)
        return dispositivos_ativos

    # envia arquivo para outro dispositivo, bloco a bloco, com confirmação e verificação de integridade
    def enviar_arquivo(self, nome_destino: str, caminho_arquivo: str) -> bool:
        """
        Envia um arquivo para outro dispositivo, garantindo confiabilidade via ACKs.
        O processo é dividido em 3 fases:
        1. Envio do FILE com metadados e espera do ACK
        2. Envio dos blocos do arquivo, cada um com seu ACK
        3. Envio do END com hash e espera do ACK final
        
        Args:
            nome_destino: Nome do dispositivo que receberá o arquivo
            caminho_arquivo: Caminho completo do arquivo a ser enviado
            
        Returns:
            bool: True se o arquivo foi enviado com sucesso, False caso contrário
        """
        # verifica se o dispositivo destino está ativo
        if nome_destino not in self.dispositivos_ativos:
            print(f"\nErro: Dispositivo {nome_destino} não encontrado")
            return False
            
        # verifica se o arquivo existe
        if not os.path.isfile(caminho_arquivo):
            print(f"\nErro: Arquivo '{caminho_arquivo}' não encontrado")
            return False

        # obtém informações do arquivo e do destino
        ip, porta, _ = self.dispositivos_ativos[nome_destino]  # extrai endereço do destino
        nome_arquivo = os.path.basename(caminho_arquivo)  # pega apenas o nome do arquivo
        tamanho_total = os.path.getsize(caminho_arquivo)  # obtém tamanho em bytes
        total_blocos = (tamanho_total + CHUNK_SIZE - 1) // CHUNK_SIZE  # calcula número de blocos
        
        # gera um identificador único para esta transferência
        # usa nome do arquivo + timestamp para evitar colisões
        id_arquivo = f"{nome_arquivo}_{int(time.time())}"
        
        # prepara estado de envio para controle de retransmissão e ACKs
        self.estado_envio_arquivo = {
            'id': id_arquivo,  # identificador único da transferência
            'arquivo': caminho_arquivo,  # caminho completo do arquivo
            'destino': (ip, porta),  # endereço do destinatário
            'total_blocos': total_blocos,  # número total de blocos
            'blocos_confirmados': set(),  # conjunto de blocos já confirmados
            'blocos_pendentes': set(range(total_blocos)),  # conjunto de blocos ainda não enviados
            'ack_final': False  # flag indicando se recebeu ACK do END
        }

        # FASE 1: Envio do FILE com metadados
        msg_file = f"FILE {id_arquivo} {nome_arquivo} {tamanho_total}"
        try:
            self.socket.sendto(msg_file.encode(), (ip, porta))
            self._log(f"Iniciando envio do arquivo {nome_arquivo} para {nome_destino}")
        except Exception as e:
            print(f"Erro ao enviar FILE: {e}")
            return False

        # aguarda confirmação do FILE antes de enviar blocos
        for _ in range(30):  # tenta por 3 segundos (30 * 0.1)
            if id_arquivo in self.acks_recebidos:
                break
            time.sleep(0.1)
        else:
            print("Timeout esperando ACK do FILE, abortando envio.")
            return False

        # FASE 2: Envio dos blocos do arquivo
        try:
            with open(caminho_arquivo, 'rb') as arquivo:
                for seq in range(total_blocos):
                    # lê o próximo bloco
                    dados = arquivo.read(CHUNK_SIZE)
                    if not dados:
                        break
                        
                    # codifica em base64 para envio seguro via texto
                    dados_b64 = base64.b64encode(dados).decode()
                    msg_chunk = f"CHUNK {id_arquivo} {seq} {dados_b64}"

                    # envia bloco e aguarda ACK
                    for tentativa in range(3):  # tenta enviar cada bloco até 3 vezes
                        self.socket.sendto(msg_chunk.encode(), (ip, porta))
                        print(f"Enviado bloco {seq+1}/{total_blocos}")
                        
                        # espera ACK deste bloco
                        for _ in range(20):  # espera 2 segundos (20 * 0.1)
                            if (id_arquivo, seq) in self.acks_recebidos:
                                self.estado_envio_arquivo['blocos_confirmados'].add(seq)
                                break
                            time.sleep(0.1)
                        else:
                            print(f"Sem ACK do bloco {seq}, retransmitindo...")
                            continue
                        break
                    else:
                        print(f"Falha ao enviar bloco {seq}, abortando envio.")
                        return False

        except Exception as e:
            print(f"Erro ao ler/enviar arquivo: {e}")
            return False

        # FASE 3: Envio do END com hash
        hash_arquivo = self._calcular_hash_arquivo(caminho_arquivo)
        msg_end = f"END {id_arquivo} {hash_arquivo}"
        self.socket.sendto(msg_end.encode(), (ip, porta))

        # espera ACK do END
        for _ in range(30):  # tenta por 3 segundos (30 * 0.1)
            if (id_arquivo, 'END') in self.acks_recebidos:
                print("Arquivo enviado e confirmado com sucesso!")
                self.estado_envio_arquivo = None  # limpa estado de envio
                return True
            time.sleep(0.1)
            
        print("Timeout esperando ACK do END, possível falha de integridade.")
        return False

    def _calcular_hash_arquivo(self, caminho: str) -> str:
        """
        Calcula o hash SHA-256 de um arquivo para verificação de integridade.
        Lê o arquivo em blocos de 4KB para economizar memória.
        
        Args:
            caminho: Caminho do arquivo a ser calculado o hash
            
        Returns:
            str: Hash SHA-256 do arquivo em hexadecimal
        """
        sha = hashlib.sha256()  # cria objeto para cálculo do hash
        try:
            with open(caminho, 'rb') as f:
                while True:
                    bloco = f.read(4096)  # lê em blocos de 4KB
                    if not bloco:
                        break
                    sha.update(bloco)  # atualiza hash com o bloco lido
            return sha.hexdigest()  # retorna hash em hexadecimal
        except Exception as e:
            print(f"Erro ao calcular hash: {e}")
            return ""

    # processa mensagem FILE, inicializa estrutura para receber arquivo
    def _processar_file(self, partes: List[str], endereco):
        """
        Processa mensagem FILE recebida, inicializa estrutura para receber arquivo.
        
        Args:
            partes: Lista com partes da mensagem [FILE, id, nome, tamanho]
            endereco: Endereço (ip, porta) do remetente
        """
        if len(partes) < 4:
            return
            
        id_arquivo = partes[1]
        nome_arquivo = partes[2]
        tamanho_total = int(partes[3])
        total_blocos = (tamanho_total + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        print(f"\nSolicitação de recebimento de arquivo: {nome_arquivo} ({tamanho_total} bytes)")
        
        # envia ACK para confirmar recebimento do FILE
        ack_msg = f"ACK {id_arquivo}"
        try:
            self.socket.sendto(ack_msg.encode(), endereco)
        except Exception as e:
            print(f"Erro ao enviar ACK de FILE: {e}")
            return
            
        # inicializa estrutura para receber o arquivo
        self.arquivos_recebidos[id_arquivo] = {
            'nome': nome_arquivo,
            'tamanho': tamanho_total,
            'blocos_recebidos': {},
            'dados': {},
            'total_blocos': total_blocos
        }

    # processa mensagem CHUNK, armazena bloco recebido e envia ACK
    def _processar_chunk(self, partes: List[str], endereco):
        """
        Processa mensagem CHUNK recebida, armazena bloco e envia ACK.
        
        Args:
            partes: Lista com partes da mensagem [CHUNK, id, seq, dados_b64]
            endereco: Endereço (ip, porta) do remetente
        """
        if len(partes) < 4:
            return
            
        id_arquivo = partes[1]
        seq = int(partes[2])
        dados_b64 = partes[3]
        
        if id_arquivo not in self.arquivos_recebidos:
            return
            
        estado = self.arquivos_recebidos[id_arquivo]
        total = estado['total_blocos']
        
        if seq >= total:
            return  # ignora blocos extras
            
        try:
            dados = base64.b64decode(dados_b64)
        except Exception:
            print(f"Erro ao processar bloco {seq}: Incorrect padding")
            return
            
        if seq not in estado['blocos_recebidos']:
            estado['blocos_recebidos'][seq] = True
            estado['dados'][seq] = dados
            print(f"Recebido bloco {seq+1}/{total}")
            
        # envia ACK para o bloco recebido
        ack_msg = f"ACK {id_arquivo} {seq}"
        try:
            self.socket.sendto(ack_msg.encode(), endereco)
        except Exception as e:
            print(f"Erro ao enviar ACK de CHUNK: {e}")

    # processa mensagem END, verifica integridade e responde com ACK ou NACK
    def _processar_end(self, partes: List[str], endereco):
        """
        Processa mensagem END recebida, verifica integridade e responde com ACK ou NACK.
        
        Args:
            partes: Lista com partes da mensagem [END, id, hash]
            endereco: Endereço (ip, porta) do remetente
        """
        if len(partes) < 3:
            print("Mensagem END inválida: número insuficiente de partes")
            return
            
        id_arquivo = partes[1]
        hash_recebido = partes[2]
        
        if id_arquivo not in self.arquivos_recebidos:
            print(f"Arquivo com id {id_arquivo} não encontrado para verificação de hash.")
            return
            
        estado = self.arquivos_recebidos[id_arquivo]
        nome_arquivo = estado['nome']
        
        # verifica se todos os blocos foram recebidos
        total_blocos = estado['total_blocos']
        blocos_recebidos = len(estado['dados'])
        if blocos_recebidos != total_blocos:
            print(f"Erro: Arquivo incompleto. Recebidos {blocos_recebidos} de {total_blocos} blocos.")
            nack_msg = f"NACK {id_arquivo} END blocos_incompletos"
            try:
                self.socket.sendto(nack_msg.encode(), endereco)
            except Exception as e:
                print(f"Erro ao enviar NACK: {e}")
            return
        
        # salva arquivo temporário para verificação de hash
        temp_filename = f"temp_{id_arquivo}.bin"
        if not self._salvar_arquivo_recebido(id_arquivo, temp_filename):
            print("Erro ao salvar arquivo temporário para verificação de hash")
            return
            
        # calcula hash do arquivo recebido
        hash_calculado = self._calcular_hash_arquivo(temp_filename)
        
        if hash_calculado == hash_recebido:
            print(f"Arquivo recebido com sucesso e verificado! Hash: {hash_calculado}")
            # salva com nome original
            if self._salvar_arquivo_recebido(id_arquivo, nome_arquivo):
                print(f"Arquivo salvo como {nome_arquivo}")
                ack_msg = f"ACK {id_arquivo} END"
                try:
                    self.socket.sendto(ack_msg.encode(), endereco)
                    print("ACK do END enviado com sucesso")
                except Exception as e:
                    print(f"Erro ao enviar ACK do END: {e}")
            else:
                print(f"Erro ao salvar arquivo final {nome_arquivo}")
                nack_msg = f"NACK {id_arquivo} END erro_salvamento"
                try:
                    self.socket.sendto(nack_msg.encode(), endereco)
                except Exception as e:
                    print(f"Erro ao enviar NACK: {e}")
        else:
            print(f"Arquivo corrompido! Hash esperado: {hash_recebido}, hash calculado: {hash_calculado}")
            nack_msg = f"NACK {id_arquivo} END hash_invalido"
            try:
                self.socket.sendto(nack_msg.encode(), endereco)
            except Exception as e:
                print(f"Erro ao enviar NACK: {e}")
            
        # remove arquivo temporário
        try:
            os.remove(temp_filename)
        except Exception:
            pass

    def _salvar_arquivo_recebido(self, id_arquivo: str, nome_destino: str) -> bool:
        """
        Salva o arquivo recebido em disco a partir dos blocos armazenados.
        Os blocos são salvos em ordem para garantir a integridade do arquivo.
        
        Args:
            id_arquivo: ID da transferência
            nome_destino: Nome do arquivo de destino
            
        Returns:
            bool: True se o arquivo foi salvo com sucesso, False caso contrário
        """
        if id_arquivo not in self.arquivos_recebidos:
            print(f"Arquivo com id {id_arquivo} não encontrado.")
            return False
            
        estado = self.arquivos_recebidos[id_arquivo]
        dados = estado['dados']
        
        if not dados:
            print(f"Nenhum bloco recebido para o arquivo {id_arquivo}.")
            return False
            
        try:
            with open(nome_destino, 'wb') as f:
                # escreve os blocos em ordem
                for seq in sorted(dados.keys()):
                    f.write(dados[seq])
            print(f"Arquivo salvo como {nome_destino}")
            return True
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return False

    # processa mensagem ACK, atualiza estado de envio
    def _processar_ack(self, partes: List[str], endereco):
        """
        Processa mensagem ACK recebida, atualiza estado de envio.
        
        Args:
            partes: Lista com partes da mensagem [ACK, id, seq?]
            endereco: Endereço (ip, porta) do remetente
        """
        if len(partes) < 2:
            return
            
        id_arquivo = partes[1]
        
        # ACK do FILE
        if len(partes) == 2:
            self.acks_recebidos[id_arquivo] = time.time()
            print(f"ACK do FILE recebido para {id_arquivo}")
            
        # ACK de bloco ou END
        elif len(partes) == 3:
            try:
                # Tenta converter para número (ACK de bloco)
                seq = int(partes[2])
                self.acks_recebidos[(id_arquivo, seq)] = time.time()
                print(f"ACK do bloco {seq} recebido para {id_arquivo}")
            except ValueError:
                # Se não for número, verifica se é END
                if partes[2] == 'END':
                    self.acks_recebidos[(id_arquivo, 'END')] = time.time()
                    print(f"ACK do END recebido para {id_arquivo}")

    # processa mensagem NACK, trata falhas de integridade
    def _processar_nack(self, partes: List[str], endereco):
        """
        Processa mensagem NACK recebida, trata falhas de integridade.
        
        Args:
            partes: Lista com partes da mensagem [NACK, id, motivo]
            endereco: Endereço (ip, porta) do remetente
        """
        if len(partes) < 3:
            return
            
        id_arquivo = partes[1]
        motivo = partes[2]
        
        print(f"Recebido NACK para {id_arquivo}: {motivo}")
        
        if self.estado_envio_arquivo and self.estado_envio_arquivo['id'] == id_arquivo:
            print("Transferência de arquivo falhou por integridade!")
            self.estado_envio_arquivo = None

    # encerra o dispositivo, finaliza threads, fecha socket e log
    def encerrar(self):
        self._log("Encerrando dispositivo...")
        self.running = False
        try:
            self.thread_heartbeat.join(timeout=1)
            self.thread_receiver.join(timeout=1)
            self.thread_cleanup.join(timeout=1)
        except Exception as e:
            self._log(f"Erro ao aguardar threads: {e}")
        try:
            self.socket.close()
        except Exception as e:
            self._log(f"Erro ao fechar socket: {e}")
        try:
            self.log_file.close()
        except Exception as e:
            print(f"Erro ao fechar arquivo de log: {e}") 