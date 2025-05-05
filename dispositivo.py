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
# importa logging para gerenciar logs
import logging

# configura o logging para salvar em arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs_dispositivo.log", encoding="utf-8"),
    ]
)

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

    # registra mensagem no log com timestamp
    def _log(self, mensagem: str, mostrar_tela: bool = False):
        logging.info(mensagem)
        if mostrar_tela:
            print(mensagem)

    # envia heartbeat para todos os dispositivos da rede a cada 5 segundos
    def _enviar_heartbeat(self):
        while self.running:
            mensagem = f"HEARTBEAT {self.nome}"
            try:
                for porta in range(5000, 5010):
                    self.socket.sendto(mensagem.encode(), (self.broadcast_address, porta))
                    self._log(f"HEARTBEAT enviado para {self.broadcast_address}:{porta}", mostrar_tela=False)
            except Exception as e:
                self._log(f"ERRO ao enviar HEARTBEAT: {e}")
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
                self._log(f"DEBUG: Pacote recebido de {endereco}: {dados}", mostrar_tela=False)  # depuração
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
        self._log(f"DEBUG: Entrou em _processar_talk com partes={partes} de {endereco}")
        if len(partes) < 3:
            return
        id_msg = partes[1]
        mensagem = " ".join(partes[2:])
        if id_msg not in self.mensagens_recebidas.get("TALK", set()):
            print(f"\nMensagem recebida: {mensagem}")
            self._log(f"Mensagem recebida de {endereco[0]}: {mensagem}")
            self.mensagens_recebidas.setdefault("TALK", set()).add(id_msg)
        # envia ACK para confirmar recebimento (sempre unicast para quem enviou)
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
        self._log(f"ENVIANDO TALK para {ip}:{porta} (ID: {id_msg}): {mensagem}")
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
                        self._log(f"ACK recebido para mensagem {id_msg}")
                        return
            except socket.timeout:
                tentativa += 1
                if tentativa < max_tentativas:
                    self._log(f"Tentativa {tentativa + 1} de enviar mensagem {id_msg}...")
                else:
                    self._log(f"Falha ao enviar mensagem {id_msg} após {max_tentativas} tentativas")
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

    # envia arquivo para outro dispositivo, bloco a bloco, com confirmação de cada etapa e verificação de integridade
    def enviar_arquivo(self, nome_destino: str, caminho_arquivo: str) -> bool:
        if nome_destino not in self.dispositivos_ativos:
            print(f"\nErro: Dispositivo {nome_destino} não encontrado")
            return False
        if not os.path.isfile(caminho_arquivo):
            print(f"\nErro: Arquivo '{caminho_arquivo}' não encontrado")
            return False
        ip, porta, _ = self.dispositivos_ativos[nome_destino]
        nome_arquivo = os.path.basename(caminho_arquivo)
        tamanho_total = os.path.getsize(caminho_arquivo)
        total_blocos = (tamanho_total + CHUNK_SIZE - 1) // CHUNK_SIZE
        id_arquivo = f"{nome_arquivo}_{int(time.time())}"
        msg_file = f"FILE {id_arquivo} {nome_arquivo} {tamanho_total}"
        try:
            self.socket.sendto(msg_file.encode(), (ip, porta))
            self._log(f"Iniciando envio do arquivo {nome_arquivo} para {nome_destino}")
        except Exception as e:
            print(f"Erro ao enviar FILE: {e}")
            return False
        for _ in range(30):
            if id_arquivo in self.acks_recebidos:
                break
            time.sleep(0.1)
        else:
            print("Timeout esperando ACK do FILE, abortando envio.")
            return False
        try:
            with open(caminho_arquivo, 'rb') as arquivo:
                for seq in range(total_blocos):
                    dados = arquivo.read(CHUNK_SIZE)
                    if not dados:
                        break
                    dados_b64 = base64.b64encode(dados).decode()
                    msg_chunk = f"CHUNK {id_arquivo} {seq} {dados_b64}"
                    tentativas = 0
                    while tentativas < 3:
                        self.socket.sendto(msg_chunk.encode(), (ip, porta))
                        print(f"Enviando bloco {seq+1}/{total_blocos} do arquivo {nome_arquivo}")
                        for _ in range(20):
                            if (id_arquivo, seq) in self.acks_recebidos:
                                break
                            time.sleep(0.1)
                        else:
                            tentativas += 1
                            print(f"Timeout esperando ACK do bloco {seq}, retransmitindo...")
                            continue
                        break
                    else:
                        print(f"Falha ao enviar bloco {seq}, abortando envio.")
                        return False
        except Exception as e:
            print(f"Erro ao ler/enviar arquivo: {e}")
            return False
        hash_arquivo = self._calcular_hash_arquivo(caminho_arquivo)
        msg_end = f"END {id_arquivo} {hash_arquivo}"
        self.socket.sendto(msg_end.encode(), (ip, porta))
        for _ in range(30):
            if (id_arquivo, 'END') in self.acks_recebidos:
                print("Arquivo enviado e confirmado com sucesso!")
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
        if len(partes) < 4:
            return
        id_arquivo = partes[1]
        nome_arquivo = partes[2]
        tamanho_total = int(partes[3])
        total_blocos = (tamanho_total + CHUNK_SIZE - 1) // CHUNK_SIZE
        print(f"\nSolicitação de recebimento de arquivo: {nome_arquivo} ({tamanho_total} bytes)")
        # envia ACK para confirmar recebimento do FILE (sempre unicast para quem enviou)
        ack_msg = f"ACK {id_arquivo}"
        try:
            self.socket.sendto(ack_msg.encode(), endereco)
        except Exception as e:
            print(f"Erro ao enviar ACK de FILE: {e}")
            return
        self.arquivos_recebidos[id_arquivo] = {
            'nome': nome_arquivo,
            'tamanho': tamanho_total,
            'blocos_recebidos': {},
            'dados': {},
            'total_blocos': total_blocos
        }

    # processa mensagem CHUNK, armazena bloco recebido e envia ACK
    def _processar_chunk(self, partes: List[str], endereco):
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
            print(f"Erro ao processar bloco {seq}: Dados inválidos")
            return
        if seq not in estado['blocos_recebidos']:
            estado['blocos_recebidos'][seq] = True
            estado['dados'][seq] = dados
            print(f"Recebido bloco {seq+1}/{total}")
        # envia ACK para o bloco recebido (sempre unicast para quem enviou)
        ack_msg = f"ACK {id_arquivo} {seq}"
        try:
            self.socket.sendto(ack_msg.encode(), endereco)
        except Exception as e:
            print(f"Erro ao enviar ACK de CHUNK: {e}")

    # processa mensagem END, verifica integridade e responde com ACK ou NACK
    def _processar_end(self, partes: List[str], endereco):
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
        temp_filename = f"temp_{id_arquivo}.bin"
        if not self._salvar_arquivo_recebido(id_arquivo, temp_filename):
            print("Erro ao salvar arquivo temporário para verificação de hash")
            return
        hash_calculado = self._calcular_hash_arquivo(temp_filename)
        if hash_calculado == hash_recebido:
            print(f"Arquivo recebido com sucesso e verificado! Hash: {hash_calculado}")
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
        try:
            os.remove(temp_filename)
        except Exception:
            pass

    def _salvar_arquivo_recebido(self, id_arquivo: str, nome_destino: str) -> bool:
        """
        Salva o arquivo recebido em disco a partir dos blocos armazenados.
        Sempre salva como binário.
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
        self._log("Encerrando dispositivo...", mostrar_tela=True)
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