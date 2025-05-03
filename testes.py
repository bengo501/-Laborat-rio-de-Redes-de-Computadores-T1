import socket
import threading
import time
import random
from dispositivo import Dispositivo

class Testador:
    def __init__(self, dispositivo: Dispositivo):
        self.dispositivo = dispositivo
        self.running = True
        self.taxa_perda = 0.0  # 0 a 1
        self.taxa_duplicacao = 0.0  # 0 a 1
        self.taxa_corrupcao = 0.0  # 0 a 1
        self.atraso_medio = 0.0  # segundos

    def simular_perda_pacotes(self, taxa: float):
        """Simula perda de pacotes com a taxa especificada"""
        self.taxa_perda = taxa
        print(f"Simulando perda de pacotes com taxa de {taxa*100}%")

    def simular_duplicacao(self, taxa: float):
        """Simula duplicação de pacotes com a taxa especificada"""
        self.taxa_duplicacao = taxa
        print(f"Simulando duplicação de pacotes com taxa de {taxa*100}%")

    def simular_corrupcao(self, taxa: float):
        """Simula corrupção de pacotes com a taxa especificada"""
        self.taxa_corrupcao = taxa
        print(f"Simulando corrupção de pacotes com taxa de {taxa*100}%")

    def simular_atraso(self, atraso: float):
        """Simula atraso médio na entrega dos pacotes"""
        self.atraso_medio = atraso
        print(f"Simulando atraso médio de {atraso} segundos")

    def iniciar_teste(self):
        """Inicia o teste com as configurações atuais"""
        print("\nIniciando teste com as seguintes condições:")
        print(f"- Taxa de perda: {self.taxa_perda*100}%")
        print(f"- Taxa de duplicação: {self.taxa_duplicacao*100}%")
        print(f"- Taxa de corrupção: {self.taxa_corrupcao*100}%")
        print(f"- Atraso médio: {self.atraso_medio} segundos")

        # Enviar arquivo de teste
        self.dispositivo.enviar_arquivo("dispositivo2", "teste.txt")

    def parar(self):
        """Para o teste"""
        self.running = False

def main():
    # Criar dispositivo de teste
    dispositivo = Dispositivo("teste", 5000)
    testador = Testador(dispositivo)

    # Configurar condições de teste
    testador.simular_perda_pacotes(0.1)  # 10% de perda
    testador.simular_duplicacao(0.05)    # 5% de duplicação
    testador.simular_corrupcao(0.02)     # 2% de corrupção
    testador.simular_atraso(0.5)         # 0.5 segundos de atraso

    # Iniciar teste
    testador.iniciar_teste()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        testador.parar()
        dispositivo.encerrar()

if __name__ == '__main__':
    main() 