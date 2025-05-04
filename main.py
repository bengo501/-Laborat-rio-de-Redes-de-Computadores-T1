# importa sys para acessar argumentos da linha de comando
import sys
# importa time para medir intervalos e exibir tempos
import time
# importa os para verificar existência de arquivos
import os
# importa a classe Dispositivo para criar e gerenciar o dispositivo p2p
from dispositivo import Dispositivo

# classe responsável pela interface de usuário no terminal
class Interface:
    # inicializa interface com o dispositivo e flag de execução
    def __init__(self, dispositivo: Dispositivo):
        self.dispositivo = dispositivo
        self.running = True

    # limpa a tela do terminal, compatível com windows e linux
    def limpar_tela(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    # exibe o menu principal com as opções disponíveis
    def mostrar_menu(self):
        self.limpar_tela()
        print("\n" + "="*50)
        print("SISTEMA DE COMUNICAÇÃO P2P".center(50))
        print("="*50)
        print("\nOpções disponíveis:")
        print("1. Listar dispositivos ativos")
        print("2. Enviar mensagem (use: talk <nome> <mensagem>)")
        print("3. Enviar arquivo (use: sendfile <nome> <arquivo>)")
        print("4. Sair")
        print("\n" + "="*50)

    # lista todos os dispositivos ativos na rede, mostrando nome, ip, porta e tempo desde o último heartbeat
    def listar_dispositivos(self):
        dispositivos = self.dispositivo.listar_dispositivos()
        if not dispositivos:
            print("\nNenhum dispositivo ativo encontrado na rede")
            input("\nPressione Enter para continuar...")
            return
        print("\nDispositivos ativos:")
        print("Nome | IP | Porta | Último heartbeat (s)")
        print("-" * 50)
        agora = time.time()
        for nome, (ip, porta, ultimo_heartbeat) in dispositivos.items():
            tempo_desde_heartbeat = agora - ultimo_heartbeat
            print(f"{nome} | {ip} | {porta} | {tempo_desde_heartbeat:.1f}")
        print("\n" + "-" * 50)
        input("\nPressione Enter para continuar...")

    # interface para enviar mensagem usando comando talk
    def enviar_mensagem(self):
        dispositivos = self.dispositivo.listar_dispositivos()
        if not dispositivos:
            print("\nNenhum dispositivo ativo encontrado na rede")
            input("\nPressione Enter para continuar...")
            return
        print("\nDispositivos disponíveis:")
        for nome in dispositivos.keys():
            print(f"- {nome}")
        print("\nDigite o comando no formato: talk <nome> <mensagem>")
        print("Exemplo: talk dispositivo1 Olá, como vai?")
        try:
            comando = input("\n> ")
            partes = comando.strip().split()
            # verifica se o comando está no formato correto
            if len(partes) < 3 or partes[0].lower() != "talk":
                print("\nFormato inválido! Use: talk <nome> <mensagem>")
                input("\nPressione Enter para continuar...")
                return
            nome_destino = partes[1]
            mensagem = " ".join(partes[2:])
            if nome_destino not in dispositivos:
                print(f"\nErro: Dispositivo {nome_destino} não encontrado")
                input("\nPressione Enter para continuar...")
                return
            # chama método do dispositivo para enviar mensagem
            self.dispositivo.enviar_mensagem(nome_destino, mensagem)
            print(f"\nMensagem enviada para {nome_destino}")
            print("\n" + "-" * 50)
            input("\nPressione Enter para continuar...")
        except Exception as e:
            print(f"\nErro ao enviar mensagem: {e}")
            input("\nPressione Enter para continuar...")

    # interface para enviar arquivo usando comando sendfile
    def enviar_arquivo(self):
        dispositivos = self.dispositivo.listar_dispositivos()
        if not dispositivos:
            print("\nNenhum dispositivo ativo encontrado na rede")
            input("\nPressione Enter para continuar...")
            return
        print("\nDispositivos disponíveis:")
        for nome in dispositivos.keys():
            print(f"- {nome}")
        print("\nDigite o comando no formato: sendfile <nome> <arquivo>")
        print("Exemplo: sendfile dispositivo1 documento.txt")
        print("\nO arquivo deve estar no diretório atual ou fornecer o caminho completo.")
        try:
            comando = input("\n> ")
            partes = comando.strip().split()
            # verifica se o comando está no formato correto
            if len(partes) < 3 or partes[0].lower() != "sendfile":
                print("\nFormato inválido! Use: sendfile <nome> <arquivo>")
                input("\nPressione Enter para continuar...")
                return
            nome_destino = partes[1]
            caminho_arquivo = partes[2]
            if nome_destino not in dispositivos:
                print(f"\nErro: Dispositivo {nome_destino} não encontrado")
                input("\nPressione Enter para continuar...")
                return
            if not os.path.exists(caminho_arquivo):
                print(f"\nErro: Arquivo {caminho_arquivo} não encontrado")
                input("\nPressione Enter para continuar...")
                return
            print(f"\nIniciando transferência do arquivo {caminho_arquivo} para {nome_destino}...")
            print("Aguarde enquanto o arquivo é transferido...")
            # chama método do dispositivo para enviar arquivo
            if self.dispositivo.enviar_arquivo(nome_destino, caminho_arquivo):
                print(f"\nTransferência concluída com sucesso!")
            else:
                print(f"\nErro: Falha na transferência do arquivo")
            print("\n" + "-" * 50)
            input("\nPressione Enter para continuar...")
        except Exception as e:
            print(f"\nErro ao enviar arquivo: {e}")
            input("\nPressione Enter para continuar...")

    # inicia a interface e gerencia o menu principal
    def iniciar(self):
        self.limpar_tela()
        print("\n" + "="*50)
        print("BEM-VINDO AO SISTEMA DE COMUNICAÇÃO P2P".center(50))
        print("="*50)
        input("\nPressione Enter para continuar...")
        while self.running:
            self.mostrar_menu()
            try:
                opcao = int(input("\nDigite o número da opção desejada: "))
                if opcao == 1:
                    self.listar_dispositivos()
                elif opcao == 2:
                    self.enviar_mensagem()
                elif opcao == 3:
                    self.enviar_arquivo()
                elif opcao == 4:
                    print("\nEncerrando programa...")
                    self.dispositivo.encerrar()
                    self.running = False
                else:
                    print("\nOpção inválida! Digite um número entre 1 e 4.")
                    input("\nPressione Enter para continuar...")
            except ValueError:
                print("\nOpção inválida! Digite um número.")
                input("\nPressione Enter para continuar...")
            except KeyboardInterrupt:
                print("\nEncerrando programa...")
                self.dispositivo.encerrar()
                self.running = False
            except Exception as e:
                print(f"\nErro: {e}")
                input("\nPressione Enter para continuar...")

# função principal que inicia o programa, recebe nome e porta como argumentos
def main():
    if len(sys.argv) != 3:
        print("Uso: python main.py <nome_dispositivo> <porta>")
        sys.exit(1)
    nome = sys.argv[1]
    try:
        porta = int(sys.argv[2])
    except ValueError:
        print("Erro: A porta deve ser um número inteiro")
        sys.exit(1)
    try:
        dispositivo = Dispositivo(nome, porta)
        interface = Interface(dispositivo)
        interface.iniciar()
    except KeyboardInterrupt:
        print("\nEncerrando...")
        dispositivo.encerrar()
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

# executa a função principal se o arquivo for executado diretamente
if __name__ == '__main__':
    main() 