import socket
import threading
import sys

HOST = "localhost"
PORT = 194
buffer_size = 1024 # Tamanho da mensagem

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def receive_messages():
    while True:
        try:
            msg = s.recv(buffer_size).decode('utf8')
        except:
            s.close()
            print('Falha na conexao')
            exit()

        print(msg)

# Conecta com o servidor
while True:
    try:
        s.connect((HOST, PORT))
        break

    except:
        print("Servidor offline")
        exit()

# Multi treading
thread = threading.Thread(target=receive_messages)
thread.start()

print("")

# Processa a mensagem enviada
while True:
    msg = input()
        
    if msg[0] == '/':
        msg = "[COMANDO] " + msg[1:]

    try:
        s.send(bytes(msg, "utf8"))
    except:
        exit()

    # Apaga a ultima linha pra evitar mensagem duplicada no chat do usuario que enviou a mensagem
    sys.stdout.write("\033[F")
    sys.stdout.write("\033[K")
