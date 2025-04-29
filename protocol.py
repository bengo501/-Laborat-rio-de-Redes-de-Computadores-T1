import json
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
import hashlib
import base64

class MessageType(Enum):
    HEARTBEAT = "HEARTBEAT"
    TALK = "TALK"
    FILE = "FILE"
    CHUNK = "CHUNK"
    END = "END"
    ACK = "ACK"
    NACK = "NACK"

@dataclass
class Message:
    type: MessageType
    id: str
    data: Optional[Any] = None
    
    @classmethod
    def heartbeat(cls, name: str) -> 'Message':
        return cls(MessageType.HEARTBEAT, "", {"name": name})
    
    @classmethod
    def talk(cls, msg_id: str, data: str) -> 'Message':
        return cls(MessageType.TALK, msg_id, {"data": data})
    
    @classmethod
    def file(cls, msg_id: str, filename: str, size: int) -> 'Message':
        return cls(MessageType.FILE, msg_id, {
            "filename": filename,
            "size": size
        })
    
    @classmethod
    def chunk(cls, msg_id: str, seq: int, data: bytes) -> 'Message':
        return cls(MessageType.CHUNK, msg_id, {
            "seq": seq,
            "data": base64.b64encode(data).decode('utf-8')
        })
    
    @classmethod
    def end(cls, msg_id: str, file_hash: str) -> 'Message':
        return cls(MessageType.END, msg_id, {"hash": file_hash})
    
    @classmethod
    def ack(cls, msg_id: str) -> 'Message':
        return cls(MessageType.ACK, msg_id)
    
    @classmethod
    def nack(cls, msg_id: str, reason: str) -> 'Message':
        return cls(MessageType.NACK, msg_id, {"reason": reason})
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "id": self.id,
            "data": self.data
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        return cls(
            MessageType(data["type"]),
            data["id"],
            data.get("data")
        )

def calculate_file_hash(file_path: str) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() 