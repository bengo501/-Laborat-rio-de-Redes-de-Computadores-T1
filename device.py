import socket
import threading
import time
import uuid
import os
import hashlib
import base64
import logging
from typing import Dict, Set, Optional, Tuple, List
from dataclasses import dataclass
from protocol import Mensagem, TipoMensagem, calcular_hash_arquivo
from datetime import datetime

# configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# constantes
TAMANHO_MAX_ARQUIVO = 100 * 1024 * 1024  # 100MB
TIMEOUT_THREAD = 5  # segundos
TENTATIVAS_RETRANSMISSAO = 3
INTERVALO_RETRANSMISSAO = 1.0  # segundos

# informações sobre um dispositivo na rede
@dataclass
class InfoDispositivo:
    nome: str
    endereco: Tuple[str, int]
    ultimo_heartbeat: float

class Dispositivo:
    def __init__(self, nome: str, porta: int = 0):
        """inicializa um dispositivo com o nome especificado"""
        self.nome = nome
        self.dispositivos: Dict[str, InfoDispositivo] = {}
        self.transferencias_pendentes: Dict[str, Dict] = {}
        self.mensagens_pendentes: Dict[str, Dict] = {}
        
        # configura socket udp com broadcast
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind(('', porta))
        self.porta = self.socket.getsockname()[1]
        
        # locks para sincronização
        self.lock_dispositivos = threading.Lock()
        self.lock_transferencias = threading.Lock()
        self.lock_mensagens = threading.Lock()
        
        # inicia threads
        self.executando = True
        self.thread_receptor = threading.Thread(target=self._loop_receptor, daemon=True)
        self.thread_heartbeat = threading.Thread(target=self._loop_heartbeat, daemon=True)
        self.thread_limpeza = threading.Thread(target=self._loop_limpeza, daemon=True)
        self.thread_retransmissao = threading.Thread(target=self._loop_retransmissao, daemon=True)
        
        self.thread_receptor.start()
        self.thread_heartbeat.start()
        self.thread_limpeza.start()
        self.thread_retransmissao.start()
        
        logger.info(f"dispositivo {nome} iniciado na porta {self.porta}")

    def _loop_receptor(self) -> None:
        """loop principal de recebimento de mensagens"""
        while self.executando:
            try:
                dados, endereco = self.socket.recvfrom(65535)
                mensagem = Mensagem.de_json(dados.decode())
                self._processar_mensagem(mensagem, endereco)
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"erro ao receber mensagem: {e}")
    
    def _loop_heartbeat(self) -> None:
        """loop de envio periódico de heartbeats"""
        while self.executando:
            try:
                self._enviar_heartbeat()
                time.sleep(5)
            except Exception as e:
                logger.error(f"erro ao enviar heartbeat: {e}")

    def _loop_limpeza(self) -> None:
        """loop de limpeza de dispositivos inativos"""
        while self.executando:
            try:
                tempo_atual = time.time()
                with self.lock_dispositivos:
                    para_remover = [
                        nome for nome, info in self.dispositivos.items()
                        if tempo_atual - info.ultimo_heartbeat > 10
                    ]
                    for nome in para_remover:
                        del self.dispositivos[nome]
                        logger.info(f"dispositivo {nome} removido por inatividade")
                time.sleep(1)
            except Exception as e:
                logger.error(f"erro na limpeza: {e}")

    def _loop_retransmissao(self) -> None:
        """loop de retransmissão de mensagens não confirmadas"""
        while self.executando:
            try:
                tempo_atual = time.time()
                with self.lock_mensagens:
                    para_retransmitir = []
                    for msg_id, info in list(self.mensagens_pendentes.items()):
                        if tempo_atual - info["timestamp"] > INTERVALO_RETRANSMISSAO:
                            if info["tentativas"] >= TENTATIVAS_RETRANSMISSAO:
                                del self.mensagens_pendentes[msg_id]
                                logger.warning(f"mensagem {msg_id} falhou após {TENTATIVAS_RETRANSMISSAO} tentativas")
                            else:
                                para_retransmitir.append(info)
                                info["timestamp"] = tempo_atual
                                info["tentativas"] += 1
                    
                    for info in para_retransmitir:
                        self.socket.sendto(info["mensagem"].para_json().encode(), info["endereco"])
                
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"erro na retransmissão: {e}")

    def _enviar_heartbeat(self) -> None:
        """envia mensagem de presença para a rede"""
        mensagem = Mensagem.heartbeat(self.nome)
        self._enviar_broadcast(mensagem)

    def _enviar_broadcast(self, mensagem: Mensagem) -> None:
        """envia mensagem para todos os dispositivos"""
        self.socket.sendto(mensagem.para_json().encode(), ('<broadcast>', self.porta))

    def _enviar_para_dispositivo(self, nome_dispositivo: str, mensagem: Mensagem, tentar_novamente: bool = True) -> bool:
        """envia mensagem para um dispositivo específico"""
        with self.lock_dispositivos:
            if nome_dispositivo in self.dispositivos:
                if tentar_novamente:
                    with self.lock_mensagens:
                        self.mensagens_pendentes[mensagem.id] = {
                            "mensagem": mensagem,
                            "endereco": self.dispositivos[nome_dispositivo].endereco,
                            "timestamp": time.time(),
                            "tentativas": 0
                        }
                self.socket.sendto(mensagem.para_json().encode(), self.dispositivos[nome_dispositivo].endereco)
            return True
        return False
    
    def _processar_mensagem(self, mensagem: Mensagem, endereco: Tuple[str, int]) -> None:
        """processa uma mensagem recebida"""
        try:
            if mensagem.tipo == TipoMensagem.HEARTBEAT:
                self._processar_heartbeat(mensagem, endereco)
            elif mensagem.tipo == TipoMensagem.TALK:
                self._processar_talk(mensagem, endereco)
            elif mensagem.tipo == TipoMensagem.FILE:
                self._processar_file(mensagem, endereco)
            elif mensagem.tipo == TipoMensagem.CHUNK:
                self._processar_chunk(mensagem, endereco)
            elif mensagem.tipo == TipoMensagem.END:
                self._processar_end(mensagem, endereco)
            elif mensagem.tipo == TipoMensagem.ACK:
                self._processar_ack(mensagem)
            elif mensagem.tipo == TipoMensagem.NACK:
                self._processar_nack(mensagem)
        except Exception as e:
            logger.error(f"erro ao processar mensagem {mensagem.tipo}: {e}")

    def _processar_heartbeat(self, mensagem: Mensagem, endereco: Tuple[str, int]) -> None:
        """processa mensagem de presença"""
        nome = mensagem.dados["nome"]
        if nome != self.nome:
            with self.lock_dispositivos:
                self.dispositivos[nome] = InfoDispositivo(nome, endereco, time.time())
            self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)

    def _processar_talk(self, mensagem: Mensagem, endereco: Tuple[str, int]) -> None:
        """processa mensagem de texto"""
        print(f"\nmensagem recebida: {mensagem.dados['texto']}")
        self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)

    def _processar_file(self, mensagem: Mensagem, endereco: Tuple[str, int]) -> None:
        """processa início de transferência de arquivo"""
        info_arquivo = mensagem.dados
        if info_arquivo["tamanho"] > TAMANHO_MAX_ARQUIVO:
            self.socket.sendto(Mensagem.nack(mensagem.id, "arquivo muito grande").para_json().encode(), endereco)
            return
        
        with self.lock_transferencias:
            self.transferencias_pendentes[mensagem.id] = {
                "nome_arquivo": os.path.basename(info_arquivo["nome_arquivo"]),
                "tamanho": info_arquivo["tamanho"],
                "chunks_recebidos": set(),
                "chunks": {},
                "remetente": endereco
            }
        self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)

    def _processar_chunk(self, mensagem: Mensagem, endereco: Tuple[str, int]) -> None:
        """processa bloco de dados do arquivo"""
        with self.lock_transferencias:
            if mensagem.id not in self.transferencias_pendentes:
                return
            
            transferencia = self.transferencias_pendentes[mensagem.id]
            sequencia = mensagem.dados["sequencia"]
            
            if sequencia not in transferencia["chunks_recebidos"]:
                try:
                    dados_chunk = base64.b64decode(mensagem.dados["dados"])
                    transferencia["chunks_recebidos"].add(sequencia)
                    transferencia["chunks"][sequencia] = dados_chunk
                    
                    chunks_esperados = (transferencia["tamanho"] + 4095) // 4096
                    if len(transferencia["chunks_recebidos"]) == chunks_esperados:
                        self._finalizar_transferencia(mensagem.id)
                    
                    self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)
                except Exception as e:
                    logger.error(f"erro ao processar chunk: {e}")
                    self.socket.sendto(Mensagem.nack(mensagem.id, str(e)).para_json().encode(), endereco)

    def _finalizar_transferencia(self, transferencia_id: str) -> None:
        """finaliza uma transferência de arquivo"""
        with self.lock_transferencias:
            if transferencia_id not in self.transferencias_pendentes:
                return
            
            transferencia = self.transferencias_pendentes[transferencia_id]
            chunks = [transferencia["chunks"][i] for i in sorted(transferencia["chunks"].keys())]
            dados_arquivo = b"".join(chunks)
            
            hash_arquivo = hashlib.sha256(dados_arquivo).hexdigest()
            
            try:
                nome_arquivo = f"recebido_{transferencia['nome_arquivo']}"
                with open(nome_arquivo, "wb") as f:
                    f.write(dados_arquivo)
                logger.info(f"arquivo recebido: {nome_arquivo}")
            except Exception as e:
                logger.error(f"erro ao salvar arquivo: {e}")
            
            del self.transferencias_pendentes[transferencia_id]

    def _processar_end(self, mensagem: Mensagem, endereco: Tuple[str, int]) -> None:
        """processa fim de transferência"""
        with self.lock_transferencias:
            if mensagem.id not in self.transferencias_pendentes:
                return
            
            transferencia = self.transferencias_pendentes[mensagem.id]
            hash_recebido = mensagem.dados["hash"]
            
            chunks = [transferencia["chunks"][i] for i in sorted(transferencia["chunks"].keys())]
            hash_arquivo = hashlib.sha256(b"".join(chunks)).hexdigest()
            
            if hash_recebido == hash_arquivo:
                self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)
                logger.info(f"transferência {mensagem.id} concluída com sucesso")
            else:
                self.socket.sendto(Mensagem.nack(mensagem.id, "hash inválido").para_json().encode(), endereco)
                logger.warning(f"transferência {mensagem.id} falhou: hash inválido")

    def _processar_ack(self, mensagem: Mensagem) -> None:
        """processa confirmação de recebimento"""
        with self.lock_mensagens:
            if mensagem.id in self.mensagens_pendentes:
                del self.mensagens_pendentes[mensagem.id]

    def _processar_nack(self, mensagem: Mensagem) -> None:
        """processa negação de recebimento"""
        with self.lock_mensagens:
            if mensagem.id in self.mensagens_pendentes:
                logger.warning(f"recebido nack para mensagem {mensagem.id}: {mensagem.dados['motivo']}")
                del self.mensagens_pendentes[mensagem.id]

    def enviar_mensagem(self, nome_destino: str, texto: str) -> bool:
        """envia uma mensagem de texto para outro dispositivo"""
        msg_id = str(uuid.uuid4())
        mensagem = Mensagem.talk(msg_id, texto)
        return self._enviar_para_dispositivo(nome_destino, mensagem)

    def enviar_arquivo(self, nome_destino: str, caminho_arquivo: str) -> bool:
        """envia um arquivo para outro dispositivo"""
        if not os.path.exists(caminho_arquivo):
            logger.error(f"arquivo não encontrado: {caminho_arquivo}")
            return False
        
        tamanho = os.path.getsize(caminho_arquivo)
        if tamanho > TAMANHO_MAX_ARQUIVO:
            logger.error(f"arquivo muito grande: {tamanho} bytes")
            return False
        
        msg_id = str(uuid.uuid4())
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        # envia mensagem de início
        mensagem = Mensagem.file(msg_id, nome_arquivo, tamanho)
        if not self._enviar_para_dispositivo(nome_destino, mensagem):
            return False
        
        # envia chunks
        try:
            with open(caminho_arquivo, "rb") as f:
                sequencia = 0
                while True:
                    dados = f.read(4096)
                    if not dados:
                        break
                    
                    mensagem = Mensagem.chunk(msg_id, sequencia, dados)
                    self._enviar_para_dispositivo(nome_destino, mensagem)
                    sequencia += 1
                    
                    progresso = min(100, int((f.tell() / tamanho) * 100))
                    print(f"enviando arquivo: {progresso}%", end="\r")
            
            print("\narquivo enviado, aguardando confirmação...")
            
            # envia mensagem de fim
            hash_arquivo = calcular_hash_arquivo(caminho_arquivo)
            mensagem = Mensagem.end(msg_id, hash_arquivo)
            return self._enviar_para_dispositivo(nome_destino, mensagem)
        
        except Exception as e:
            logger.error(f"erro ao enviar arquivo: {e}")
            return False

    def listar_dispositivos(self) -> None:
        """lista dispositivos ativos"""
        with self.lock_dispositivos:
            if not self.dispositivos:
                print("nenhum dispositivo ativo encontrado")
                return
            
            print("\ndispositivos ativos:")
            for nome, info in self.dispositivos.items():
                tempo_desde_heartbeat = (datetime.now().timestamp() - info.ultimo_heartbeat)
                print(f"- {nome} ({info.endereco[0]}:{info.endereco[1]}) - último heartbeat: {tempo_desde_heartbeat:.1f}s atrás")

    def parar(self) -> None:
        """encerra o dispositivo e suas threads"""
        self.executando = False
        self.socket.close()
        
        # aguarda threads terminarem
        for thread in [self.thread_receptor, self.thread_heartbeat, self.thread_limpeza, self.thread_retransmissao]:
            thread.join(TIMEOUT_THREAD)
        
        logger.info("dispositivo encerrado") 