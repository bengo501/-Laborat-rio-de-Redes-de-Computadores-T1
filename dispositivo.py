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
    def __init__(self, nome: str, porta: int):
        """
        Inicializa um dispositivo na rede
        :param nome: Nome do dispositivo
        :param porta: Porta para comunicação UDP
        """
        self.nome = nome
        self.porta = porta
        
        # Criar socket UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Usar endereço de broadcast padrão
        self.broadcast_address = '255.255.255.255'
        
        # Bind em todas as interfaces
        self.socket.bind(('0.0.0.0', porta))
        
        # Dicionário para armazenar dispositivos ativos
        self.dispositivos_ativos: Dict[str, tuple] = {}
        
        # Dicionário para controle de mensagens recebidas
        self.mensagens_recebidas: Dict[str, set] = {}
        
        # Dicionário para controle de transferência de arquivos
        self.arquivos_recebidos: Dict[str, dict] = {}
        
        # Configurar logs
        self.log_file = open(f"logs_{nome}.txt", "w")
        self._log(f"Dispositivo {nome} inicializado na porta {porta}")
        self._log(f"Usando endereço de broadcast: {self.broadcast_address}")
        
        # Iniciar threads de controle
        self.running = True
        self.thread_heartbeat = threading.Thread(target=self._enviar_heartbeat)
        self.thread_receiver = threading.Thread(target=self._receber_mensagens)
        self.thread_cleanup = threading.Thread(target=self._limpar_inativos)
        
        self.thread_heartbeat.start()
        self.thread_receiver.start()
        self.thread_cleanup.start()

    def _log(self, mensagem: str):
        """Registra uma mensagem no log com timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        log_entry = f"[{timestamp}] {mensagem}\n"
        print(log_entry.strip())
        self.log_file.write(log_entry)
        self.log_file.flush()

    def _enviar_heartbeat(self):
        """Thread para enviar heartbeats periódicos"""
        while self.running:
            mensagem = f"HEARTBEAT {self.nome}"
            try:
                # Enviar para todas as portas possíveis
                for porta in range(5000, 5010):
                    self.socket.sendto(mensagem.encode(), (self.broadcast_address, porta))
                    self._log(f"HEARTBEAT enviado para {self.broadcast_address}:{porta}")
            except Exception as e:
                self._log(f"ERRO ao enviar HEARTBEAT: {e}")
            time.sleep(5)

    def _limpar_inativos(self):
        """Thread para remover dispositivos inativos"""
        while self.running:
            agora = time.time()
            for nome in list(self.dispositivos_ativos.keys()):
                ip, porta, ultimo_heartbeat = self.dispositivos_ativos[nome]
                if agora - ultimo_heartbeat > 10:
                    self._log(f"Dispositivo {nome} removido por inatividade")
                    del self.dispositivos_ativos[nome]
            time.sleep(1)

    def _receber_mensagens(self):
        """Thread principal para receber e processar mensagens"""
        while self.running:
            try:
                dados, endereco = self.socket.recvfrom(65536)
                mensagem = dados.decode()
                self._log(f"RECEBIDO de {endereco}: {mensagem}")
                
                partes = mensagem.split()
                
                if not partes:
                    continue
                
                tipo_mensagem = partes[0]
                
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

    def _processar_heartbeat(self, partes: List[str], endereco):
        """Processa mensagens do tipo HEARTBEAT"""
        if len(partes) < 2:
            return
        
        nome_dispositivo = partes[1]
        ip, porta = endereco
        
        # Ignorar heartbeats do próprio dispositivo
        if nome_dispositivo == self.nome:
            return
            
        # Verificar se é um novo dispositivo ou atualização
        if nome_dispositivo not in self.dispositivos_ativos:
            self._log(f"Novo dispositivo descoberto: {nome_dispositivo} em {ip}:{porta}")
        else:
            ip_antigo, porta_antiga, _ = self.dispositivos_ativos[nome_dispositivo]
            if ip != ip_antigo or porta != porta_antiga:
                self._log(f"Dispositivo {nome_dispositivo} mudou de endereço: {ip_antigo}:{porta_antiga} -> {ip}:{porta}")
        
        self.dispositivos_ativos[nome_dispositivo] = (ip, porta, time.time())

    def _processar_talk(self, partes: List[str], endereco):
        """Processa mensagens do tipo TALK"""
        if len(partes) < 3:
            return
        
        id_msg = partes[1]
        mensagem = " ".join(partes[2:])
        
        # Evitar mensagens duplicadas
        if id_msg not in self.mensagens_recebidas.get("TALK", set()):
            self._log(f"\nMensagem recebida de {endereco[0]}: {mensagem}")
            self.mensagens_recebidas.setdefault("TALK", set()).add(id_msg)
        
        # Enviar ACK
        resposta = f"ACK {id_msg}"
        self.socket.sendto(resposta.encode(), endereco)

    def enviar_mensagem(self, nome_destino: str, mensagem: str):
        """
        Envia uma mensagem para um dispositivo específico
        :param nome_destino: Nome do dispositivo destino
        :param mensagem: Conteúdo da mensagem
        """
        if nome_destino not in self.dispositivos_ativos:
            self._log(f"ERRO: Dispositivo {nome_destino} não encontrado")
            return
        
        ip, porta, _ = self.dispositivos_ativos[nome_destino]
        id_msg = f"{self.nome}_{int(time.time())}"
        mensagem_completa = f"TALK {id_msg} {mensagem}"
        
        self._log(f"ENVIANDO TALK para {ip}:{porta} (ID: {id_msg}): {mensagem}")
        
        # Tentar enviar até receber ACK
        max_tentativas = 3
        tentativa = 0
        while tentativa < max_tentativas:
            self.socket.sendto(mensagem_completa.encode(), (ip, porta))
            # Aguardar ACK
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

    def listar_dispositivos(self):
        """Lista todos os dispositivos ativos na rede"""
        agora = time.time()
        dispositivos_ativos = {}
        
        # Filtrar dispositivos ativos (último heartbeat < 10 segundos)
        for nome, (ip, porta, ultimo_heartbeat) in self.dispositivos_ativos.items():
            if agora - ultimo_heartbeat < 10:
                dispositivos_ativos[nome] = (ip, porta, ultimo_heartbeat)
        
        return dispositivos_ativos

    def enviar_arquivo(self, nome_destino: str, caminho_arquivo: str):
        """
        Envia um arquivo para um dispositivo específico
        :param nome_destino: Nome do dispositivo destino
        :param caminho_arquivo: Caminho do arquivo a ser enviado
        """
        if nome_destino not in self.dispositivos_ativos:
            self._log(f"ERRO: Dispositivo {nome_destino} não encontrado")
            return
        
        if not os.path.exists(caminho_arquivo):
            self._log(f"ERRO: Arquivo {caminho_arquivo} não encontrado")
            return
        
        ip, porta, _ = self.dispositivos_ativos[nome_destino]
        id_msg = f"{self.nome}_{int(time.time())}"
        tamanho = os.path.getsize(caminho_arquivo)
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        # Enviar mensagem FILE
        mensagem = f"FILE {id_msg} {nome_arquivo} {tamanho}"
        self._log(f"ENVIANDO FILE para {ip}:{porta} (ID: {id_msg}): {nome_arquivo} ({tamanho} bytes)")
        self.socket.sendto(mensagem.encode(), (ip, porta))
        
        # Aguardar ACK do FILE
        try:
            self.socket.settimeout(5)
            dados, _ = self.socket.recvfrom(1024)
            resposta = dados.decode().split()
            if not (len(resposta) >= 2 and resposta[0] == "ACK" and resposta[1] == id_msg):
                self._log(f"ERRO: Falha ao iniciar transferência do arquivo {id_msg}")
                return
        except socket.timeout:
            self._log(f"ERRO: Timeout ao aguardar confirmação do arquivo {id_msg}")
            return
        finally:
            self.socket.settimeout(None)
        
        # Calcular hash do arquivo
        hash_arquivo = hashlib.sha256()
        
        # Enviar arquivo em chunks
        with open(caminho_arquivo, 'rb') as f:
            seq = 0
            while True:
                chunk = f.read(8192)  # 8KB por chunk
                if not chunk:
                    break
                
                hash_arquivo.update(chunk)
                chunk_b64 = base64.b64encode(chunk).decode()
                mensagem = f"CHUNK {id_msg} {seq} {chunk_b64}"
                
                # Tentar enviar chunk até receber ACK
                max_tentativas = 3
                tentativa = 0
                while tentativa < max_tentativas:
                    self.socket.sendto(mensagem.encode(), (ip, porta))
                    try:
                        self.socket.settimeout(2)
                        dados, _ = self.socket.recvfrom(1024)
                        resposta = dados.decode().split()
                        if len(resposta) >= 2 and resposta[0] == "ACK" and resposta[1] == id_msg:
                            break
                    except socket.timeout:
                        tentativa += 1
                    finally:
                        self.socket.settimeout(None)
                
                if tentativa == max_tentativas:
                    self._log(f"ERRO: Falha ao enviar chunk {seq} do arquivo {id_msg}")
                    return
                
                seq += 1
                progresso = (f.tell() / tamanho) * 100
                self._log(f"Progresso do arquivo {id_msg}: {progresso:.1f}%")
        
        # Enviar mensagem END com hash
        hash_final = hash_arquivo.hexdigest()
        mensagem = f"END {id_msg} {hash_final}"
        self._log(f"ENVIANDO END para {ip}:{porta} (ID: {id_msg}): hash={hash_final}")
        self.socket.sendto(mensagem.encode(), (ip, porta))
        
        # Aguardar confirmação final
        try:
            self.socket.settimeout(5)
            dados, _ = self.socket.recvfrom(1024)
            resposta = dados.decode().split()
            if len(resposta) >= 2 and resposta[0] == "ACK" and resposta[1] == id_msg:
                self._log(f"Arquivo {id_msg} enviado com sucesso!")
            else:
                self._log(f"ERRO: Falha na validação do arquivo {id_msg}")
        except socket.timeout:
            self._log(f"ERRO: Timeout ao aguardar confirmação final do arquivo {id_msg}")
        finally:
            self.socket.settimeout(None)

    def _processar_file(self, partes: List[str], endereco):
        """Processa mensagens do tipo FILE"""
        if len(partes) < 4:
            return
        
        id_msg = partes[1]
        nome_arquivo = partes[2]
        tamanho = int(partes[3])
        
        # Inicializar estrutura para receber arquivo
        self.arquivos_recebidos[id_msg] = {
            'nome': nome_arquivo,
            'tamanho': tamanho,
            'chunks': {},
            'hash': None,
            'completo': False
        }
        
        # Enviar ACK
        resposta = f"ACK {id_msg}"
        self.socket.sendto(resposta.encode(), endereco)

    def _processar_chunk(self, partes: List[str], endereco):
        """Processa mensagens do tipo CHUNK"""
        if len(partes) < 4:
            return
        
        id_msg = partes[1]
        seq = int(partes[2])
        dados_b64 = partes[3]
        
        if id_msg in self.arquivos_recebidos:
            # Decodificar e armazenar chunk
            try:
                dados = base64.b64decode(dados_b64)
                self.arquivos_recebidos[id_msg]['chunks'][seq] = dados
                
                # Enviar ACK
                resposta = f"ACK {id_msg}"
                self.socket.sendto(resposta.encode(), endereco)
            except:
                # Enviar NACK em caso de erro
                resposta = f"NACK {id_msg} erro_decodificacao"
                self.socket.sendto(resposta.encode(), endereco)

    def _processar_end(self, partes: List[str], endereco):
        """Processa mensagens do tipo END"""
        if len(partes) < 3:
            return
        
        id_msg = partes[1]
        hash_esperado = partes[2]
        
        if id_msg not in self.arquivos_recebidos:
            return
        
        arquivo = self.arquivos_recebidos[id_msg]
        
        # Ordenar e concatenar chunks
        chunks_ordenados = [arquivo['chunks'][i] for i in sorted(arquivo['chunks'].keys())]
        dados_completos = b''.join(chunks_ordenados)
        
        # Calcular hash
        hash_calculado = hashlib.sha256(dados_completos).hexdigest()
        
        if hash_calculado == hash_esperado:
            # Hash válido, salvar arquivo
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

    def _processar_ack(self, partes: List[str], endereco):
        """Processa mensagens do tipo ACK"""
        # Implementação específica de ACK será feita nos métodos que aguardam ACK
        pass

    def _processar_nack(self, partes: List[str], endereco):
        """Processa mensagens do tipo NACK"""
        if len(partes) < 3:
            return
        
        id_msg = partes[1]
        motivo = partes[2]
        self._log(f"\nErro na transmissão (ID: {id_msg}): {motivo}")

    def encerrar(self):
        """Encerra o dispositivo de forma segura"""
        self._log("Encerrando dispositivo...")
        self.running = False
        
        # Aguardar threads terminarem
        try:
            self.thread_heartbeat.join(timeout=1)
            self.thread_receiver.join(timeout=1)
            self.thread_cleanup.join(timeout=1)
        except Exception as e:
            self._log(f"Erro ao aguardar threads: {e}")
        
        # Fechar socket
        try:
            self.socket.close()
        except Exception as e:
            self._log(f"Erro ao fechar socket: {e}")
        
        # Fechar arquivo de log por último
        try:
            self.log_file.close()
        except Exception as e:
            print(f"Erro ao fechar arquivo de log: {e}") 