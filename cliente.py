import socket
import threading

HOST = "localhost"
PORT = 6666
buffer_size = 1024 #tamanho da mensagem

def receiveMessages(s):
    while True:
        try:
            msg = s.recv(buffer_size).decode('utf-8')
            print(msg)
        except:
            print("FALHA NA CONEXAO")
            s.close()
            break

def sendMessages(s, nickname):
    while True:
        try:
            msg = input()
            s.send(f'{nickname}: {msg}'.encode('utf-8'))
            #s.send(bytes(msg, "utf-8"))
        except:
            print("Errinho")
            return

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.connect((HOST, PORT))
except:
    print("ERRO AO TENTAR SE CONECTAR")
    print("HOST: " + str(HOST))
    print("PORT: " + str(PORT))
    exit()

nickname = input('Nickname: ')
nome_real = input('Nome real: ')
print("Conectado")

thread1 = threading.Thread(target=receiveMessages, args=[s])
thread2 = threading.Thread(target=sendMessages, args=[s, nickname])

thread1.start()
thread2.start()