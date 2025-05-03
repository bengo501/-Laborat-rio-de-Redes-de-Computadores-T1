#  bibliotecas necessárias para comunicação, threads, tempo, codificação, hash, json e sistema
import socket
import threading
import time
import base64
import hashlib
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class Dispositivo:
    # inicializa um dispositivo com nome e porta, configurando socket e estruturas de dados
    def __init__(self, nome: str, porta: int):
        # nome do dispositivo
        self.nome = nome
        # porta udp para comunicação
        self.porta = porta
        
        # cria socket udp com opções de reuso e broadcast
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # endereço de broadcast padrão
        self.broadcast_address = '255.255.255.255'
        
        # vincula socket a todas as interfaces na porta especificada
        self.socket.bind(('0.0.0.0', porta))
        
        # dicionário para armazenar dispositivos ativos (nome -> (ip, porta, ultimo_heartbeat))
        self.dispositivos_ativos: Dict[str, tuple] = {}
        
        # dicionário para controle de mensagens recebidas (tipo -> set de ids)
        self.mensagens_recebidas: Dict[str, set] = {}
        
        # dicionário para controle de transferência de arquivos (id -> dados do arquivo)
        self.arquivos_recebidos: Dict[str, dict] = {}
        
        # configura arquivo de log
        self.log_file = open(f"logs_{nome}.txt", "w")
        self._log(f"Dispositivo {nome} inicializado na porta {porta}")
        self._log(f"Usando endereço de broadcast: {self.broadcast_address}")
        
        # flag para controle de execução das threads
        self.running = True
        
        # cria e inicia threads para heartbeat, recebimento e limpeza
        self.thread_heartbeat = threading.Thread(target=self._enviar_heartbeat)
        self.thread_receiver = threading.Thread(target=self._receber_mensagens)
        self.thread_cleanup = threading.Thread(target=self._limpar_inativos)
        
        self.thread_heartbeat.start()
        self.thread_receiver.start()
        self.thread_cleanup.start()

    # registra mensagem no log com timestamp
    def _log(self, mensagem: str, mostrar_tela: bool = True):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        log_entry = f"[{timestamp}] {mensagem}\n"
        if mostrar_tela:
            print(log_entry.strip())
        self.log_file.write(log_entry)
        self.log_file.flush()

    # thread que envia heartbeat periódico para broadcast
    def _enviar_heartbeat(self):
        while self.running:
            mensagem = f"HEARTBEAT {self.nome}"
            try:
                # envia heartbeat para todas as portas possíveis
                for porta in range(5000, 5010):
                    self.socket.sendto(mensagem.encode(), (self.broadcast_address, porta))
                    self._log(f"HEARTBEAT enviado para {self.broadcast_address}:{porta}", mostrar_tela=False)
            except Exception as e:
                self._log(f"ERRO ao enviar HEARTBEAT: {e}")
            time.sleep(5)

    # thread que remove dispositivos inativos da lista
    def _limpar_inativos(self):
        while self.running:
            agora = time.time()
            for nome in list(self.dispositivos_ativos.keys()):
                ip, porta, ultimo_heartbeat = self.dispositivos_ativos[nome]
                if agora - ultimo_heartbeat > 10:
                    self._log(f"Dispositivo {nome} removido por inatividade")
                    del self.dispositivos_ativos[nome]
            time.sleep(1)

    # thread principal que recebe e processa mensagens
    def _receber_mensagens(self):
        while self.running:
            try:
                dados, endereco = self.socket.recvfrom(65536)
                mensagem = dados.decode()
                self._log(f"RECEBIDO de {endereco}: {mensagem}", mostrar_tela=False)
                
                partes = mensagem.split()
                
                if not partes:
                    continue
                
                tipo_mensagem = partes[0]
                
                # processa mensagem de acordo com seu tipo
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

    # processa mensagem heartbeat, atualizando lista de dispositivos
    def _processar_heartbeat(self, partes: List[str], endereco):
        if len(partes) < 2:
            return
        
        nome_dispositivo = partes[1]
        ip, porta = endereco
        
        # ignora heartbeats do próprio dispositivo
        if nome_dispositivo == self.nome:
            return
            
        # verifica se é novo dispositivo ou atualização
        if nome_dispositivo not in self.dispositivos_ativos:
            self._log(f"Novo dispositivo descoberto: {nome_dispositivo} em {ip}:{porta}")
        else:
            ip_antigo, porta_antiga, _ = self.dispositivos_ativos[nome_dispositivo]
            if ip != ip_antigo or porta != porta_antiga:
                self._log(f"Dispositivo {nome_dispositivo} mudou de endereço: {ip_antigo}:{porta_antiga} -> {ip}:{porta}")
        
        self.dispositivos_ativos[nome_dispositivo] = (ip, porta, time.time())

    # processa mensagem talk, exibe conteúdo e envia ack
    def _processar_talk(self, partes: List[str], endereco):
        if len(partes) < 3:
            return
        
        id_msg = partes[1]
        mensagem = " ".join(partes[2:])
        
        # evita mensagens duplicadas
        if id_msg not in self.mensagens_recebidas.get("TALK", set()):
            print(f"\nMensagem recebida: {mensagem}")
            self._log(f"Mensagem recebida de {endereco[0]}: {mensagem}", mostrar_tela=False)
            self.mensagens_recebidas.setdefault("TALK", set()).add(id_msg)
        
        # envia ack de confirmação
        resposta = f"ACK {id_msg}"
        self.socket.sendto(resposta.encode(), endereco)

    # envia mensagem para dispositivo específico com confirmação
    def enviar_mensagem(self, nome_destino: str, mensagem: str):
        if nome_destino not in self.dispositivos_ativos:
            print(f"Erro: Dispositivo {nome_destino} não encontrado")
            return
        
        ip, porta, _ = self.dispositivos_ativos[nome_destino]
        id_msg = f"{self.nome}_{int(time.time())}"
        mensagem_completa = f"TALK {id_msg} {mensagem}"
        
        self._log(f"ENVIANDO TALK para {ip}:{porta} (ID: {id_msg}): {mensagem}", mostrar_tela=False)
        
        # tenta enviar até receber ack ou atingir máximo de tentativas
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

    # lista dispositivos ativos na rede
    def listar_dispositivos(self):
        agora = time.time()
        dispositivos_ativos = {}
        
        # filtra dispositivos ativos (último heartbeat < 10 segundos)
        for nome, (ip, porta, ultimo_heartbeat) in self.dispositivos_ativos.items():
            if agora - ultimo_heartbeat < 10:
                dispositivos_ativos[nome] = (ip, porta, ultimo_heartbeat)
        
        return dispositivos_ativos

    # envia arquivo para outro dispositivo com confirmação e verificação de integridade
    def enviar_arquivo(self, nome_destino: str, caminho_arquivo: str):
        if nome_destino not in self.dispositivos_ativos:
            print(f"\nErro: Dispositivo {nome_destino} não encontrado")
            return False

        try:
            tamanho_total = os.path.getsize(caminho_arquivo)
            nome_arquivo = os.path.basename(caminho_arquivo)
            id_transferencia = f"{self.nome}_{int(time.time())}"
            
            # envia mensagem file inicial
            mensagem_file = f"FILE {id_transferencia} {nome_arquivo} {tamanho_total}"
            self.socket.sendto(mensagem_file.encode(), self.dispositivos_ativos[nome_destino])
            
            # aguarda ack do file
            if not self._aguardar_confirmacao(nome_destino, 'ACK', id_transferencia):
                self._log(f"Erro: Falha na confirmação inicial do arquivo {nome_arquivo}", mostrar_tela=False)
                return False
            
            # envia arquivo em blocos
            tamanho_bloco = 1024
            total_blocos = (tamanho_total + tamanho_bloco - 1) // tamanho_bloco
            
            with open(caminho_arquivo, 'rb') as arquivo:
                for i in range(1, total_blocos + 1):
                    bloco = arquivo.read(tamanho_bloco)
                    if not bloco:
                        break
                        
                    # tenta enviar bloco até receber confirmação
                    max_tentativas = 3
                    tentativa = 0
                    while tentativa < max_tentativas:
                        dados_b64 = base64.b64encode(bloco).decode()
                        mensagem_chunk = f"CHUNK {id_transferencia} {i} {dados_b64}"
                        self.socket.sendto(mensagem_chunk.encode(), self.dispositivos_ativos[nome_destino])
                        
                        # calcula e mostra progresso
                        progresso = (i / total_blocos) * 100
                        self._log(f"Progresso do arquivo {nome_arquivo}: {progresso:.1f}% ({i}/{total_blocos} blocos)", mostrar_tela=False)
                        
                        # aguarda confirmação de recebimento
                        if self._aguardar_confirmacao(nome_destino, 'ACK', id_transferencia):
                            break
                            
                        tentativa += 1
                        if tentativa < max_tentativas:
                            self._log(f"Tentativa {tentativa + 1} de enviar bloco {i}...", mostrar_tela=False)
                        else:
                            self._log(f"Erro: Falha na transferência do bloco {i} após {max_tentativas} tentativas", mostrar_tela=False)
                            return False
            
            # calcula hash do arquivo
            arquivo.seek(0)
            hash_arquivo = hashlib.sha256()
            while True:
                bloco = arquivo.read(tamanho_bloco)
                if not bloco:
                    break
                hash_arquivo.update(bloco)
            
            # envia mensagem end com hash
            mensagem_end = f"END {id_transferencia} {hash_arquivo.hexdigest()}"
            self.socket.sendto(mensagem_end.encode(), self.dispositivos_ativos[nome_destino])
            
            # aguarda ack/nack do end
            try:
                self.socket.settimeout(5)
                while True:
                    dados, _ = self.socket.recvfrom(1024)
                    resposta = dados.decode().split()
                    if len(resposta) >= 2 and resposta[1] == id_transferencia:
                        if resposta[0] == "ACK":
                            self._log(f"Arquivo {nome_arquivo} enviado com sucesso para {nome_destino}", mostrar_tela=False)
                            return True
                        elif resposta[0] == "NACK":
                            self._log(f"Erro: Arquivo {nome_arquivo} rejeitado pelo destinatário: {resposta[2] if len(resposta) > 2 else 'motivo não especificado'}", mostrar_tela=False)
                            return False
            except socket.timeout:
                self._log(f"Erro: Timeout aguardando confirmação final do arquivo {nome_arquivo}", mostrar_tela=False)
                return False
            finally:
                self.socket.settimeout(None)
                
        except Exception as e:
            self._log(f"Erro ao enviar arquivo: {e}", mostrar_tela=False)
            return False

    # aguarda confirmação de recebimento de mensagem
    def _aguardar_confirmacao(self, nome_destino: str, tipo_confirmacao: str, id_msg: str, timeout: float = 5.0) -> bool:
        tempo_inicio = time.time()
        
        while time.time() - tempo_inicio < timeout:
            try:
                dados, _ = self.socket.recvfrom(1024)
                resposta = dados.decode().split()
                if len(resposta) >= 2 and resposta[0] == tipo_confirmacao and resposta[1] == id_msg:
                    return True
            except socket.timeout:
                continue
            except Exception as e:
                self._log(f"Erro ao aguardar confirmação: {e}", mostrar_tela=False)
                return False
                
        return False

    # processa mensagem file, inicializa estrutura para receber arquivo
    def _processar_file(self, partes: List[str], endereco):
        if len(partes) < 4:
            return
        
        id_msg = partes[1]
        nome_arquivo = partes[2]
        tamanho = int(partes[3])
        
        # inicializa estrutura para receber arquivo
        self.arquivos_recebidos[id_msg] = {
            'nome': nome_arquivo,
            'tamanho': tamanho,
            'chunks': {},
            'hash': None,
            'completo': False
        }
        
        # envia ack de confirmação
        resposta = f"ACK {id_msg}"
        self.socket.sendto(resposta.encode(), endereco)

    # processa mensagem chunk, armazena bloco e envia ack
    def _processar_chunk(self, partes: List[str], endereco):
        if len(partes) < 4:
            return
        
        id_msg = partes[1]
        seq = int(partes[2])
        dados_b64 = partes[3]
        
        if id_msg in self.arquivos_recebidos:
            # decodifica e armazena chunk
            try:
                dados = base64.b64decode(dados_b64)
                self.arquivos_recebidos[id_msg]['chunks'][seq] = dados
                
                # envia ack de confirmação
                resposta = f"ACK {id_msg}"
                self.socket.sendto(resposta.encode(), endereco)
            except:
                # envia nack em caso de erro
                resposta = f"NACK {id_msg} erro_decodificacao"
                self.socket.sendto(resposta.encode(), endereco)

    # processa mensagem end, verifica hash e salva arquivo
    def _processar_end(self, partes: List[str], endereco):
        if len(partes) < 3:
            return
        
        id_msg = partes[1]
        hash_esperado = partes[2]
        
        if id_msg not in self.arquivos_recebidos:
            return
        
        arquivo = self.arquivos_recebidos[id_msg]
        
        # ordena e concatena chunks
        chunks_ordenados = [arquivo['chunks'][i] for i in sorted(arquivo['chunks'].keys())]
        dados_completos = b''.join(chunks_ordenados)
        
        # calcula hash
        hash_calculado = hashlib.sha256(dados_completos).hexdigest()
        
        if hash_calculado == hash_esperado:
            # hash válido, salva arquivo
            nome_arquivo = f"recebido_{arquivo['nome']}"
            with open(nome_arquivo, 'wb') as f:
                f.write(dados_completos)
            
            self._log(f"\nArquivo {nome_arquivo} recebido com sucesso!")
            resposta = f"ACK {id_msg}"
        else:
            self._log("\nErro: Hash do arquivo não corresponde")
            resposta = f"NACK {id_msg} hash_invalido"
        
        self.socket.sendto(resposta.encode(), endereco)
        del self.arquivos_recebidos[id_msg]

    # processa mensagem ack
    def _processar_ack(self, partes: List[str], endereco):
        pass

    # processa mensagem nack, exibe motivo do erro
    def _processar_nack(self, partes: List[str], endereco):
        if len(partes) < 3:
            return
        
        id_msg = partes[1]
        motivo = partes[2]
        self._log(f"\nErro na transmissão (ID: {id_msg}): {motivo}")

    # encerra dispositivo de forma segura
    def encerrar(self):
        self._log("Encerrando dispositivo...")
        self.running = False
        
        # aguarda threads terminarem
        try:
            self.thread_heartbeat.join(timeout=1)
            self.thread_receiver.join(timeout=1)
            self.thread_cleanup.join(timeout=1)
        except Exception as e:
            self._log(f"Erro ao aguardar threads: {e}")
        
        # fecha socket
        try:
            self.socket.close()
        except Exception as e:
            self._log(f"Erro ao fechar socket: {e}")
        
        # fecha arquivo de log
        try:
            self.log_file.close()
        except Exception as e:
            print(f"Erro ao fechar arquivo de log: {e}") 