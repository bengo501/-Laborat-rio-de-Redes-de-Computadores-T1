import socket
import threading
import time
import uuid
import os
from typing import Dict, Set, Optional
from dataclasses import dataclass
from protocol import Message, MessageType, calculate_file_hash

@dataclass
class DeviceInfo:
    name: str
    address: tuple
    last_heartbeat: float

class Device:
    def __init__(self, name: str, port: int = 0):
        self.name = name
        self.devices: Dict[str, DeviceInfo] = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind(('', port))
        self.port = self.socket.getsockname()[1]
        
        # Para controle de transferência de arquivos
        self.pending_transfers: Dict[str, Dict] = {}
        self.received_chunks: Dict[str, Set[int]] = {}
        
        # Para controle de mensagens pendentes
        self.pending_messages: Dict[str, Dict] = {}
        
        # Inicia threads
        self.running = True
        self.receiver_thread = threading.Thread(target=self._receive_loop)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop)
        
        self.receiver_thread.start()
        self.heartbeat_thread.start()
        self.cleanup_thread.start()
    
    def _receive_loop(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                message = Message.from_json(data.decode())
                self._handle_message(message, addr)
            except Exception as e:
                print(f"Erro ao receber mensagem: {e}")
    
    def _heartbeat_loop(self):
        while self.running:
            try:
                self._send_heartbeat()
                time.sleep(5)
            except Exception as e:
                print(f"Erro ao enviar heartbeat: {e}")
    
    def _cleanup_loop(self):
        while self.running:
            try:
                current_time = time.time()
                to_remove = []
                for name, info in self.devices.items():
                    if current_time - info.last_heartbeat > 10:
                        to_remove.append(name)
                for name in to_remove:
                    del self.devices[name]
                time.sleep(1)
            except Exception as e:
                print(f"Erro na limpeza: {e}")
    
    def _send_heartbeat(self):
        message = Message.heartbeat(self.name)
        self._send_broadcast(message)
    
    def _send_broadcast(self, message: Message):
        self.socket.sendto(message.to_json().encode(), ('<broadcast>', self.port))
    
    def _send_to_device(self, device_name: str, message: Message):
        if device_name in self.devices:
            self.socket.sendto(message.to_json().encode(), self.devices[device_name].address)
            return True
        return False
    
    def _handle_message(self, message: Message, addr: tuple):
        if message.type == MessageType.HEARTBEAT:
            self._handle_heartbeat(message, addr)
        elif message.type == MessageType.TALK:
            self._handle_talk(message, addr)
        elif message.type == MessageType.FILE:
            self._handle_file(message, addr)
        elif message.type == MessageType.CHUNK:
            self._handle_chunk(message, addr)
        elif message.type == MessageType.END:
            self._handle_end(message, addr)
        elif message.type == MessageType.ACK:
            self._handle_ack(message)
        elif message.type == MessageType.NACK:
            self._handle_nack(message)
    
    def _handle_heartbeat(self, message: Message, addr: tuple):
        name = message.data["name"]
        if name != self.name:  # Ignora próprios heartbeats
            self.devices[name] = DeviceInfo(name, addr, time.time())
            # Envia ACK
            self.socket.sendto(Message.ack(message.id).to_json().encode(), addr)
    
    def _handle_talk(self, message: Message, addr: tuple):
        print(f"\nMensagem recebida de {message.data['data']}")
        # Envia ACK
        self.socket.sendto(Message.ack(message.id).to_json().encode(), addr)
    
    def _handle_file(self, message: Message, addr: tuple):
        file_info = message.data
        self.pending_transfers[message.id] = {
            "filename": file_info["filename"],
            "size": file_info["size"],
            "received_chunks": set(),
            "sender": addr
        }
        # Envia ACK
        self.socket.sendto(Message.ack(message.id).to_json().encode(), addr)
    
    def _handle_chunk(self, message: Message, addr: tuple):
        if message.id in self.pending_transfers:
            transfer = self.pending_transfers[message.id]
            seq = message.data["seq"]
            if seq not in transfer["received_chunks"]:
                transfer["received_chunks"].add(seq)
                # Processa o chunk (implementar lógica de salvamento)
                # Envia ACK
                self.socket.sendto(Message.ack(message.id).to_json().encode(), addr)
    
    def _handle_end(self, message: Message, addr: tuple):
        if message.id in self.pending_transfers:
            transfer = self.pending_transfers[message.id]
            # Verifica hash e finaliza transferência
            # Envia ACK ou NACK dependendo do resultado
            del self.pending_transfers[message.id]
    
    def _handle_ack(self, message: Message):
        if message.id in self.pending_messages:
            # Processa ACK (implementar lógica de confirmação)
            pass
    
    def _handle_nack(self, message: Message):
        if message.id in self.pending_messages:
            # Processa NACK (implementar lógica de retransmissão)
            pass
    
    def send_message(self, target_name: str, content: str) -> bool:
        message_id = str(uuid.uuid4())
        message = Message.talk(message_id, content)
        return self._send_to_device(target_name, message)
    
    def send_file(self, target_name: str, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
            
        message_id = str(uuid.uuid4())
        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        
        # Envia mensagem FILE
        file_message = Message.file(message_id, filename, filesize)
        if not self._send_to_device(target_name, file_message):
            return False
            
        # Implementar lógica de envio de chunks
        return True
    
    def list_devices(self):
        current_time = time.time()
        print("\nDispositivos ativos:")
        for name, info in self.devices.items():
            age = current_time - info.last_heartbeat
            print(f"- {name} ({info.address[0]}:{info.address[1]}) - Último heartbeat: {age:.1f}s atrás")
    
    def stop(self):
        self.running = False
        self.socket.close()
        self.receiver_thread.join()
        self.heartbeat_thread.join()
        self.cleanup_thread.join() 