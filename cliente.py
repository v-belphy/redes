import socket
import threading
from time import sleep
import select

HOST = "localhost"
PORT = 194
buffer_size = 1024 # Tamanho da mensagem
channel = "#MAIN"

########################################################
# FLAGS
########################################################

nick_flag = False
user_flag = False
wait_flag = False

########################################################

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lock = threading.Lock()


def send(msg):
    s.send(bytes(msg, "utf-8"))


def wait_for_response():
    lock.acquire()
    ready = select.select([s],[],[],0.5)
    if ready[0]:
        reply = s.recv(buffer_size).decode("utf-8")
    else:
        reply = "OK"
    lock.release()
    return reply

####################################################################
# MESSAGE TREATMENT
####################################################################

def parse_message(msg: str) -> str:
    if msg[0] == ':':
        sender = msg[1:msg.find(' ')]
        print(f"{sender}{msg[msg[1:].find(':'):]}")
    else:
        numeric = (msg[:3] if msg[:3].isnumeric() else False)
        if numeric:
            print(f"Error {numeric}: {msg[msg.find(':'):]}")
        else:
            print("Something went wrong: parse")
            print(msg)
            exit(0)

def format_message(msg: str,command: str) -> str:
    if command == "JOIN":
        idx = msg.find(' ')+1
    return msg[:idx]+'#'+msg[idx:]

####################################################################

def receive_messages():
    while True:
        try:
            ready = select.select([s],[],[])
            if ready[0]:
                msg = s.recv(buffer_size).decode('utf-8')
        except:
            s.close()
            print('Falha na conexao:rcv')
            exit()

        parse_message(msg)

while True:
    try:
        s.connect((HOST, PORT))
        break

    except:
        print("Servidor offline")
        exit()

s.setblocking(0)

# CADASTRO
while not nick_flag:
    nickname = input("Digite seu nickname: ")
    nick_flag = True
    send(f"NICK {nickname}")
    reply = wait_for_response()
    if reply != "OK":
        parse_message(reply)
        nick_flag = False


while not user_flag:
    username = input("Digite seu username: ")
    realname = input("Digite seu nome real: ")
    print("")
    user_flag = True
    send(f"USER {username} foo :{realname}")
    reply = wait_for_response()
    if reply != "OK":
        parse_message(reply)
        user_flag = False

print("Conectado\n")

# Multi treading
thread = threading.Thread(target=receive_messages)
thread.start()

print("")


# Processa a mensagem enviada
while True:
    msg = input()
    
    if msg[0] == '/':
        msg = msg[1:]
    else:
        msg = f"PRIVMSG {channel} :{msg}" #TO DO: Achar um jeito de salvar o canal no cliente de forma a corresponder com o do servidor

    if msg == "HELP":
        print(
        "LISTA DE COMANDOS DISPONIVEIS \n"+
        "/NICK (nickname): altera seu proprio nickname \n"+
        "/USER (username,realname): especifica o nome de usuario, nome do host e nome real de um usuario \n"+
        "/QUIT: finaliza sessao \n"+
        "/JOIN (canal): cria ou entra em um canal \n"+
        "/PART (canal): sai de um canal, o qual esta participando \n"+
        "/LIST: lista os canais existentes e o numero de usuarios no canal \n"+
        "/PRIVMSG (canal/nickname) (mensagem): envia mensagem a um canal ou a um usuario \n"+
        "/WHO (canal): lista os participantes do canal \n"
        )

    elif msg == "QUIT":
        send(msg)
        s.close()
        exit()

    elif msg[:len("JOIN ")] == "JOIN ":
        if msg.find('#') > 0:
            send(msg)
        else:
            msg = format_message(msg,"JOIN")
            send(msg)



    else:
        send(msg)
        # sys.stdout.write("\033[F") # Apaga a ultima linha pra evitar mensagem duplicada no chat do usuario que enviou a mensagem
        # sys.stdout.write("\033[K")
