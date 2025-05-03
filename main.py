# imports necessários para o programa principal
import sys  # para argumentos da linha de comando
import os  # para manipulação de arquivos
from device import Dispositivo  # importa classe do dispositivo

def main():
    """função principal do programa"""
    # verifica argumentos da linha de comando
    if len(sys.argv) < 2:
        print("uso: python main.py <nome_dispositivo> [porta]")
        return
    
    # obtém nome e porta do dispositivo
    nome = sys.argv[1]
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    print(f"\niniciando dispositivo {nome} na porta {porta}")
    
    # cria e inicia o dispositivo
    dispositivo = Dispositivo(nome, porta)
    
    try:
        while True:
            # menu de opções
            print("\n=== menu principal ===")
            print("1. listar dispositivos ativos")
            print("2. enviar mensagem")
            print("3. enviar arquivo")
            print("4. sair")
            
            # processa opção escolhida
            opcao = input("\nescolha uma opção: ")
            
            if opcao == "1":
                # lista dispositivos ativos
                dispositivo.listar_dispositivos()
            
            elif opcao == "2":
                # envia mensagem para outro dispositivo
                nome_destino = input("nome do dispositivo destino: ")
                mensagem = input("mensagem: ")
                dispositivo.enviar_mensagem(nome_destino, mensagem)
            
            elif opcao == "3":
                # envia arquivo para outro dispositivo
                nome_destino = input("nome do dispositivo destino: ")
                caminho_arquivo = input("caminho do arquivo: ")
                dispositivo.enviar_arquivo(nome_destino, caminho_arquivo)
            
            elif opcao == "4":
                # encerra o programa
                print("\nencerrando dispositivo...")
                break
            
            else:
                print("\nopção inválida!")
    
    except KeyboardInterrupt:
        # tratamento de interrupção do teclado
        print("\nencerrando dispositivo...")
    
    finally:
        # garante que o dispositivo será encerrado
        dispositivo.parar()

# executa o programa
if __name__ == "__main__":
    main() 