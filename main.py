import sys
import cmd
import threading
from device import Device

class DeviceCLI(cmd.Cmd):
    intro = 'Bem-vindo ao protocolo de comunicação. Digite help ou ? para listar os comandos.\n'
    prompt = '(device) '

    def __init__(self, device: Device):
        super().__init__()
        self.device = device

    def do_devices(self, arg):
        """Lista todos os dispositivos ativos na rede."""
        self.device.list_devices()

    def do_talk(self, arg):
        """Envia uma mensagem para um dispositivo específico.
        Uso: talk <nome> <mensagem>"""
        try:
            name, message = arg.split(' ', 1)
            if self.device.send_message(name, message):
                print(f"Mensagem enviada para {name}")
            else:
                print(f"Dispositivo {name} não encontrado")
        except ValueError:
            print("Uso: talk <nome> <mensagem>")

    def do_sendfile(self, arg):
        """Envia um arquivo para um dispositivo específico.
        Uso: sendfile <nome> <nome-arquivo>"""
        try:
            name, filepath = arg.split(' ', 1)
            if self.device.send_file(name, filepath):
                print(f"Iniciando envio do arquivo para {name}")
            else:
                print(f"Erro ao enviar arquivo para {name}")
        except ValueError:
            print("Uso: sendfile <nome> <nome-arquivo>")

    def do_quit(self, arg):
        """Encerra o programa."""
        self.device.stop()
        return True

    def do_EOF(self, arg):
        """Encerra o programa (Ctrl+D)."""
        print()
        return self.do_quit(arg)

def main():
    if len(sys.argv) != 2:
        print("Uso: python main.py <nome_do_dispositivo>")
        sys.exit(1)

    device_name = sys.argv[1]
    device = Device(device_name)
    
    try:
        DeviceCLI(device).cmdloop()
    except KeyboardInterrupt:
        device.stop()

if __name__ == '__main__':
    main() 