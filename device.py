import socket
import threading
import time
import uuid
import os
import hashlib
import base64
from typing import Dict, Set, Optional, Tuple, List
from dataclasses import dataclass
from protocol import Mensagem, TipoMensagem, calcular_hash_arquivo
from datetime import datetime

# Informações sobre um dispositivo na rede
@dataclass
class InfoDispositivo:
    nome: str
    endereco: tuple
    ultimo_heartbeat: float

class Dispositivo:
    def __init__(self, nome: str, porta: int = 0):
        """Inicializa um dispositivo com o nome especificado"""
        self.nome = nome
        self.dispositivos: Dict[str, InfoDispositivo] = {}  # Lista de dispositivos conhecidos
        
        # Configura socket UDP com broadcast
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind(('', porta))
        self.porta = self.socket.getsockname()[1]
        
        # Controle de transferências e mensagens
        self.transferencias_pendentes: Dict[str, Dict] = {}  # Transferências em andamento
        self.mensagens_pendentes: Dict[str, Dict] = {}       # Mensagens aguardando ACK
        
        # Inicia threads de execução
        self.executando = True
        self.thread_receptor = threading.Thread(target=self._loop_receptor)
        self.thread_heartbeat = threading.Thread(target=self._loop_heartbeat)
        self.thread_limpeza = threading.Thread(target=self._loop_limpeza)
        self.thread_retransmissao = threading.Thread(target=self._loop_retransmissao)
        
        self.thread_receptor.start()
        self.thread_heartbeat.start()
        self.thread_limpeza.start()
        self.thread_retransmissao.start()
    
    def _loop_receptor(self):
        """Loop principal de recebimento de mensagens"""
        while self.executando:
            try:
                dados, endereco = self.socket.recvfrom(65535)
                mensagem = Mensagem.de_json(dados.decode())
                self._processar_mensagem(mensagem, endereco)
            except Exception as e:
                print(f"Erro ao receber mensagem: {e}")
    
    def _loop_heartbeat(self):
        """Loop de envio periódico de heartbeats"""
        while self.executando:
            try:
                self._enviar_heartbeat()
                time.sleep(5)  # Envia a cada 5 segundos
            except Exception as e:
                print(f"Erro ao enviar heartbeat: {e}")
    
    def _loop_limpeza(self):
        """Loop de limpeza de dispositivos inativos"""
        while self.executando:
            try:
                tempo_atual = time.time()
                # Remove dispositivos sem heartbeat há mais de 10 segundos
                para_remover = []
                for nome, info in self.dispositivos.items():
                    if tempo_atual - info.ultimo_heartbeat > 10:
                        para_remover.append(nome)
                for nome in para_remover:
                    del self.dispositivos[nome]
                time.sleep(1)
            except Exception as e:
                print(f"Erro na limpeza: {e}")
    
    def _loop_retransmissao(self):
        """Loop de retransmissão de mensagens não confirmadas"""
        while self.executando:
            try:
                tempo_atual = time.time()
                para_retransmitir = []
                
                # Verifica mensagens pendentes
                for msg_id, info in list(self.mensagens_pendentes.items()):
                    if tempo_atual - info["timestamp"] > 1.0:  # 1 segundo sem ACK
                        para_retransmitir.append(info)
                        info["timestamp"] = tempo_atual
                        info["tentativas"] += 1
                        
                        if info["tentativas"] >= 3:  # Máximo de 3 tentativas
                            del self.mensagens_pendentes[msg_id]
                            print(f"Mensagem {msg_id} falhou após 3 tentativas")
                
                # Retransmite mensagens
                for info in para_retransmitir:
                    self.socket.sendto(info["mensagem"].para_json().encode(), info["endereco"])
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Erro na retransmissão: {e}")
    
    def _enviar_heartbeat(self):
        """Envia mensagem de presença para a rede"""
        mensagem = Mensagem.heartbeat(self.nome)
        self._enviar_broadcast(mensagem)
    
    def _enviar_broadcast(self, mensagem: Mensagem):
        """Envia mensagem para todos os dispositivos"""
        self.socket.sendto(mensagem.para_json().encode(), ('<broadcast>', self.porta))
    
    def _enviar_para_dispositivo(self, nome_dispositivo: str, mensagem: Mensagem, tentar_novamente: bool = True) -> bool:
        """Envia mensagem para um dispositivo específico"""
        if nome_dispositivo in self.dispositivos:
            if tentar_novamente:
                self.mensagens_pendentes[mensagem.id] = {
                    "mensagem": mensagem,
                    "endereco": self.dispositivos[nome_dispositivo].endereco,
                    "timestamp": time.time(),
                    "tentativas": 0
                }
            self.socket.sendto(mensagem.para_json().encode(), self.dispositivos[nome_dispositivo].endereco)
            return True
        return False
    
    def _processar_mensagem(self, mensagem: Mensagem, endereco: tuple):
        """Processa uma mensagem recebida"""
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
    
    def _processar_heartbeat(self, mensagem: Mensagem, endereco: tuple):
        """Processa mensagem de presença"""
        nome = mensagem.dados["nome"]
        if nome != self.nome:  # Ignora próprios heartbeats
            self.dispositivos[nome] = InfoDispositivo(nome, endereco, time.time())
            # Envia ACK
            self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)
    
    def _processar_talk(self, mensagem: Mensagem, endereco: tuple):
        """Processa mensagem de texto"""
        print(f"\nMensagem recebida: {mensagem.dados['texto']}")
        # Envia ACK
        self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)
    
    def _processar_file(self, mensagem: Mensagem, endereco: tuple):
        """Processa início de transferência de arquivo"""
        info_arquivo = mensagem.dados
        self.transferencias_pendentes[mensagem.id] = {
            "nome_arquivo": info_arquivo["nome_arquivo"],
            "tamanho": info_arquivo["tamanho"],
            "chunks_recebidos": set(),
            "chunks": {},
            "remetente": endereco
        }
        # Envia ACK
        self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)
    
    def _processar_chunk(self, mensagem: Mensagem, endereco: tuple):
        """Processa bloco de dados do arquivo"""
        if mensagem.id in self.transferencias_pendentes:
            transferencia = self.transferencias_pendentes[mensagem.id]
            sequencia = mensagem.dados["sequencia"]
            
            if sequencia not in transferencia["chunks_recebidos"]:
                try:
                    dados_chunk = base64.b64decode(mensagem.dados["dados"])
                    transferencia["chunks_recebidos"].add(sequencia)
                    transferencia["chunks"][sequencia] = dados_chunk
                    
                    # Verifica se todos os chunks foram recebidos
                    chunks_esperados = (transferencia["tamanho"] + 4095) // 4096
                    if len(transferencia["chunks_recebidos"]) == chunks_esperados:
                        self._finalizar_transferencia(mensagem.id)
                    
                    # Envia ACK
                    self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)
                except Exception as e:
                    print(f"Erro ao processar chunk: {e}")
                    self.socket.sendto(Mensagem.nack(mensagem.id, str(e)).para_json().encode(), endereco)
    
    def _finalizar_transferencia(self, transferencia_id: str):
        """Finaliza uma transferência de arquivo"""
        if transferencia_id in self.transferencias_pendentes:
            transferencia = self.transferencias_pendentes[transferencia_id]
            
            # Reordena os chunks
            chunks = [transferencia["chunks"][i] for i in sorted(transferencia["chunks"].keys())]
            dados_arquivo = b"".join(chunks)
            
            # Calcula hash
            hash_arquivo = hashlib.sha256(dados_arquivo).hexdigest()
            
            # Salva o arquivo
            try:
                with open(transferencia["nome_arquivo"], "wb") as f:
                    f.write(dados_arquivo)
                print(f"Arquivo recebido: {transferencia['nome_arquivo']}")
            except Exception as e:
                print(f"Erro ao salvar arquivo: {e}")
            
            del self.transferencias_pendentes[transferencia_id]
    
    def _processar_end(self, mensagem: Mensagem, endereco: tuple):
        """Processa fim de transferência"""
        if mensagem.id in self.transferencias_pendentes:
            transferencia = self.transferencias_pendentes[mensagem.id]
            hash_recebido = mensagem.dados["hash"]
            
            # Calcula hash do arquivo recebido
            hash_arquivo = hashlib.sha256(b"".join(transferencia["chunks"][i] for i in sorted(transferencia["chunks"].keys()))).hexdigest()
            
            if hash_recebido == hash_arquivo:
                self.socket.sendto(Mensagem.ack(mensagem.id).para_json().encode(), endereco)
                print(f"Transferência {mensagem.id} concluída com sucesso")
            else:
                self.socket.sendto(Mensagem.nack(mensagem.id, "Hash inválido").para_json().encode(), endereco)
                print(f"Transferência {mensagem.id} falhou: hash inválido")
    
    def _processar_ack(self, mensagem: Mensagem):
        """Processa confirmação de recebimento"""
        if mensagem.id in self.mensagens_pendentes:
            del self.mensagens_pendentes[mensagem.id]
    
    def _processar_nack(self, mensagem: Mensagem):
        """Processa negação de recebimento"""
        if mensagem.id in self.mensagens_pendentes:
            print(f"Recebido NACK para mensagem {mensagem.id}: {mensagem.dados['motivo']}")
            del self.mensagens_pendentes[mensagem.id]
    
    def enviar_mensagem(self, nome_destino: str, texto: str) -> bool:
        """Envia uma mensagem de texto para outro dispositivo"""
        msg_id = str(uuid.uuid4())
        mensagem = Mensagem.talk(msg_id, texto)
        return self._enviar_para_dispositivo(nome_destino, mensagem)
    
    def enviar_arquivo(self, nome_destino: str, caminho_arquivo: str) -> bool:
        """Inicia transferência de arquivo para outro dispositivo"""
        if not os.path.exists(caminho_arquivo):
            print(f"Arquivo não encontrado: {caminho_arquivo}")
            return False
            
        msg_id = str(uuid.uuid4())
        tamanho = os.path.getsize(caminho_arquivo)
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        # Envia mensagem FILE
        mensagem_file = Mensagem.file(msg_id, nome_arquivo, tamanho)
        if not self._enviar_para_dispositivo(nome_destino, mensagem_file):
            return False
        
        # Inicia transferência em chunks
        try:
            tamanho_chunk = 4096  # 4KB por chunk
            total_chunks = (tamanho + tamanho_chunk - 1) // tamanho_chunk
            
            with open(caminho_arquivo, "rb") as f:
                for sequencia in range(total_chunks):
                    dados_chunk = f.read(tamanho_chunk)
                    mensagem_chunk = Mensagem.chunk(msg_id, sequencia, dados_chunk)
                    self._enviar_para_dispositivo(nome_destino, mensagem_chunk)
                    
                    # Mostra progresso simples
                    progresso = (sequencia + 1) / total_chunks * 100
                    print(f"\rEnviando arquivo: {progresso:.1f}%", end="")
                print()  # Nova linha após progresso
            
            # Envia mensagem END com hash
            hash_arquivo = calcular_hash_arquivo(caminho_arquivo)
            mensagem_end = Mensagem.end(msg_id, hash_arquivo)
            self._enviar_para_dispositivo(nome_destino, mensagem_end)
            
            return True
        except Exception as e:
            print(f"Erro ao enviar arquivo: {e}")
            return False
    
    def listar_dispositivos(self):
        """Lista todos os dispositivos ativos na rede"""
        tempo_atual = time.time()
        print("\nDispositivos ativos:")
        if not self.dispositivos:
            print("Nenhum dispositivo ativo encontrado")
            return
            
        for nome, info in self.dispositivos.items():
            idade = tempo_atual - info.ultimo_heartbeat
            print(f"- {nome}")
            print(f"  Endereço: {info.endereco[0]}:{info.endereco[1]}")
            print(f"  Último heartbeat: {idade:.1f}s atrás")
            print()
    
    def parar(self):
        """Encerra o dispositivo e suas threads"""
        self.executando = False
        self.socket.close()
        self.thread_receptor.join()
        self.thread_heartbeat.join()
        self.thread_limpeza.join()
        self.thread_retransmissao.join() 