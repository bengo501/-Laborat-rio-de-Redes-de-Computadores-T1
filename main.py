import sys
import time
import os
from dispositivo import Dispositivo

class Interface:
    def __init__(self, dispositivo: Dispositivo):
        self.dispositivo = dispositivo
        self.running = True

    def mostrar_menu(self):
        """Mostra o menu principal"""
        print("\n" + "="*50)
        print("SISTEMA DE COMUNICAÇÃO P2P".center(50))
        print("="*50)
        print("\nOpções disponíveis:")
        print("1. Listar dispositivos ativos")
        print("2. Enviar mensagem")
        print("3. Enviar arquivo")
        print("4. Sair")
        print("\n" + "="*50)

    def listar_dispositivos(self):
        """Lista todos os dispositivos ativos na rede"""
        dispositivos = self.dispositivo.listar_dispositivos()
        
        if not dispositivos:
            print("\nNenhum dispositivo ativo encontrado na rede")
            return
            
        print("\nDispositivos ativos:")
        print("Nome | IP | Porta | Último heartbeat (s)")
        print("-" * 50)
        
        agora = time.time()
        for nome, (ip, porta, ultimo_heartbeat) in dispositivos.items():
            tempo_desde_heartbeat = agora - ultimo_heartbeat
            print(f"{nome} | {ip} | {porta} | {tempo_desde_heartbeat:.1f}")

    def enviar_mensagem(self):
        """Interface para enviar mensagem"""
        dispositivos = self.dispositivo.listar_dispositivos()
        
        if not dispositivos:
            print("\nNenhum dispositivo ativo encontrado na rede")
            return
            
        print("\nDispositivos disponíveis:")
        for i, nome in enumerate(dispositivos.keys(), 1):
            print(f"{i}. {nome}")
            
        try:
            opcao = int(input("\nSelecione o número do dispositivo: "))
            if opcao < 1 or opcao > len(dispositivos):
                print("Opção inválida!")
                return
                
            nome_destino = list(dispositivos.keys())[opcao-1]
            mensagem = input("Digite a mensagem: ")
            
            self.dispositivo.enviar_mensagem(nome_destino, mensagem)
            print(f"\nMensagem enviada para {nome_destino}")
            
        except ValueError:
            print("Opção inválida! Digite um número.")
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")

    def enviar_arquivo(self):
        """Interface para enviar arquivo"""
        dispositivos = self.dispositivo.listar_dispositivos()
        
        if not dispositivos:
            print("\nNenhum dispositivo ativo encontrado na rede")
            return
            
        print("\nDispositivos disponíveis:")
        for i, nome in enumerate(dispositivos.keys(), 1):
            print(f"{i}. {nome}")
            
        try:
            opcao = int(input("\nSelecione o número do dispositivo: "))
            if opcao < 1 or opcao > len(dispositivos):
                print("Opção inválida!")
                return
                
            nome_destino = list(dispositivos.keys())[opcao-1]
            caminho_arquivo = input("Digite o caminho do arquivo: ")
            
            if not os.path.exists(caminho_arquivo):
                print(f"Erro: Arquivo {caminho_arquivo} não encontrado")
                return
                
            self.dispositivo.enviar_arquivo(nome_destino, caminho_arquivo)
            print(f"\nArquivo enviado para {nome_destino}")
            
        except ValueError:
            print("Opção inválida! Digite um número.")
        except Exception as e:
            print(f"Erro ao enviar arquivo: {e}")

    def iniciar(self):
        """Inicia a interface"""
        print("\n" + "="*50)
        print("BEM-VINDO AO SISTEMA DE COMUNICAÇÃO P2P".center(50))
        print("="*50)
        
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
                    
            except ValueError:
                print("\nOpção inválida! Digite um número.")
            except KeyboardInterrupt:
                print("\nEncerrando programa...")
                self.dispositivo.encerrar()
                self.running = False
            except Exception as e:
                print(f"\nErro: {e}")

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

if __name__ == '__main__':
    main() 