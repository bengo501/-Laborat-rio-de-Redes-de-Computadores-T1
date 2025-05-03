# imports necessários para o protocolo
import json  # para serialização de mensagens
import hashlib  # para cálculo de hash
import base64  # para codificação de dados
from enum import Enum  # para tipos de mensagens
from typing import Dict, Any  # para tipagem
import uuid  # para gerar ids únicos

# tipos de mensagens suportados pelo protocolo
class TipoMensagem(Enum):
    """tipos de mensagens suportados pelo protocolo"""
    HEARTBEAT = "HEARTBEAT"  # mensagem de presença
    TALK = "TALK"           # mensagem de texto
    FILE = "FILE"           # início de transferência de arquivo
    CHUNK = "CHUNK"         # bloco de dados do arquivo
    END = "END"             # fim de transferência
    ACK = "ACK"             # confirmação de recebimento
    NACK = "NACK"           # negação de recebimento

# classe que representa uma mensagem do protocolo
class Mensagem:
    """classe que representa uma mensagem do protocolo"""
    
    # inicializa uma mensagem com id, tipo e dados
    def __init__(self, id: str, tipo: TipoMensagem, dados: Dict[str, Any]):
        self.id = id
        self.tipo = tipo
        self.dados = dados
    
    # converte a mensagem para formato json
    def para_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "tipo": self.tipo.value,
            "dados": self.dados
        })
    
    # cria uma mensagem a partir de uma string json
    @classmethod
    def de_json(cls, json_str: str) -> 'Mensagem':
        dados = json.loads(json_str)
        return cls(
            id=dados["id"],
            tipo=TipoMensagem(dados["tipo"]),
            dados=dados["dados"]
        )
    
    # métodos para criar cada tipo de mensagem
    @classmethod
    def heartbeat(cls, nome: str) -> 'Mensagem':
        """cria uma mensagem de presença"""
        return cls(
            id=str(uuid.uuid4()),
            tipo=TipoMensagem.HEARTBEAT,
            dados={"nome": nome}
        )
    
    @classmethod
    def talk(cls, id: str, texto: str) -> 'Mensagem':
        """cria uma mensagem de texto"""
        return cls(
            id=id,
            tipo=TipoMensagem.TALK,
            dados={"texto": texto}
        )
    
    @classmethod
    def file(cls, id: str, nome_arquivo: str, tamanho: int) -> 'Mensagem':
        """cria uma mensagem de início de transferência de arquivo"""
        return cls(
            id=id,
            tipo=TipoMensagem.FILE,
            dados={
                "nome_arquivo": nome_arquivo,
                "tamanho": tamanho
            }
        )
    
    @classmethod
    def chunk(cls, id: str, sequencia: int, dados: bytes) -> 'Mensagem':
        """cria uma mensagem com bloco de dados do arquivo"""
        return cls(
            id=id,
            tipo=TipoMensagem.CHUNK,
            dados={
                "sequencia": sequencia,
                "dados": base64.b64encode(dados).decode()
            }
        )
    
    @classmethod
    def end(cls, id: str, hash_arquivo: str) -> 'Mensagem':
        """cria uma mensagem de fim de transferência"""
        return cls(
            id=id,
            tipo=TipoMensagem.END,
            dados={"hash": hash_arquivo}
        )
    
    @classmethod
    def ack(cls, id: str) -> 'Mensagem':
        """cria uma mensagem de confirmação"""
        return cls(
            id=id,
            tipo=TipoMensagem.ACK,
            dados={}
        )
    
    @classmethod
    def nack(cls, id: str, motivo: str) -> 'Mensagem':
        """cria uma mensagem de negação"""
        return cls(
            id=id,
            tipo=TipoMensagem.NACK,
            dados={"motivo": motivo}
        )

# calcula o hash sha-256 de um arquivo
def calcular_hash_arquivo(caminho_arquivo: str) -> str:
    """calcula o hash sha-256 de um arquivo"""
    hash_sha256 = hashlib.sha256()
    with open(caminho_arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(4096), b""):
            hash_sha256.update(bloco)
    return hash_sha256.hexdigest() 