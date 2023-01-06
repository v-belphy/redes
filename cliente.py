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

quit_flag = False


# essas flags sao usadas para verificar se o cadastro foi efetivado
nick_flag = False  
user_flag = False



########################################################

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def send(msg):
    s.send(bytes(msg, "utf-8"))

# Usa a funcao select para implementar um timeout para uam resposta do servidor
# Caso o servidor nao responda a funcao assume que nao houve erro e retorna OK
# Acaba sendo usada apenas para a verificacao do cadastro
def wait_for_response():
    ready = select.select([s],[],[],0.5)
    if ready[0]:
        reply = s.recv(buffer_size).decode("utf-8")
    else:
        reply = "OK"
    return reply

####################################################################
# MESSAGE TREATMENT
####################################################################

def parse_message(msg: str) -> str:
    if msg[:len(":server ")] == ':server ':
        reply = msg[len(":server "):]
        numeric = int(reply[:3])
        
        # ERRORS
        if numeric in [432,433,461,403,401,421]:
            if numeric == 432:
                tmp = f"Problemas no nome {reply.split(' ')[2]}"
            elif numeric == 433:
                tmp = f"O nick {reply.split(' ')[2]} ja esta em uso"
            elif numeric == 461:
                tmp = "Numero de parametros insuficiente"
            elif numeric == 403:
                tmp = f"{reply.split(' ')[2]} canal nao encontrado" 
            elif numeric == 401:
                tmp = f"{reply.split(' ')[2]} usuario nao encontrado"
            elif numeric == 421:
                tmp = f"Comando {reply.split(' ')[2]} nao existe"

            print(f"Erro {numeric}: {tmp}")

        # REPLIES
        elif numeric in [353,366,321,322,323,352,315]:

            # printa a lista de usuarios de um canal
            if numeric == 353:
                chan = reply[reply.find('=')+2:reply.find(':')-1]
                print(chan+':')
                users = reply[reply.find(':')+1:].split()
                for user in users:
                    print("    " + user)
            

            # Sempre que o usuario usar o comando JOIN ele recebe uma lista e a mensagem de fim da lista possui o canal que o usuario entrou
            # entao ela pode ser usada para manter a variavel channel sincronizada com o canal salvo no servidor.
            elif numeric == 366:
                global channel
                print("Fim da Lista")
                channel = reply.split(' ')[2]

            elif numeric == 323 or numeric == 315:
                print("Fim da Lista")
            
            elif numeric == 321:
                print("Canal:Usuario Nome")
            
            elif numeric == 322:
                print(reply.split(' ')[2])
            

            # Printa os resultados da query
            elif numeric == 352:
                params = reply[:reply.find(':')].split()[2:] + [reply[reply.find(':')+1:]]
                (chan,host,nick,real) = (params[0],params[1],params[2],params[4])
                print(f"{nick}: {chan} {host} {real}".rstrip())


        else:
            print("Something went wrong: reply parse")
    else:
        (orig,msg) = (msg[1:msg.find(' ')],msg[msg.find(' ')+1:])
        (op,msg) = (msg[:msg.find(' ')],msg[msg.find(' ')+1:])
        if op == "PRIVMSG":
            tmp = ""
            if msg[0] == '#': # se o destino eh um canal botar canal junto com orig
                tmp += msg[:msg.find(' ')]+' '
            tmp+=orig+': '+msg[msg.find(':')+1:]
        elif op == "NICK":
            tmp = f"{orig} mudou o nick para {msg}"
        elif op == "PART":
            tmp = f"{orig} saiu desse canal"
        elif op == "JOIN":
            tmp = f"{orig} entrou no canal {msg}"
        elif op == "QUIT":
            tmp = f"{orig} desconectou do servidor"
        print(tmp)


def format_message(msg: str,command: str) -> str:
    if command == 'J':
        idx = msg.find(' ')+1
        return msg[:idx]+'#'+msg[idx:]

    elif command == "PM":
        msg = msg[len("PRIVMSG "):]
        text = msg[msg.find(' ')+1:]
        dest = msg[:msg.find(' ')+1]
        return "PRIVMSG " + dest+':'+text
    
    elif command == 'U':
        msg = msg[len("USER "):]
        idx = msg.find(' ')
        (username,realname) = (msg[:idx],msg[idx:])
        return f"USER {username} hostname :{realname}"

####################################################################

def receive_messages():

    while True:
        try:
            msg = s.recv(buffer_size).decode('utf-8')

        except ConnectionAbortedError:
            print("Conexao Terminada")
            break

        except Exception as e:
            s.close()
            print(f'Falha na conexao:{e}')
            exit(1)

        parse_message(msg)

while True:
    try:
        s.connect((HOST, PORT))
        break

    except:
        print("Servidor offline")
        exit()

s.setblocking(False)

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
    send(f"USER {username} hostname :{realname}")
    reply = wait_for_response()
    if reply != "OK":
        parse_message(reply)
        user_flag = False

print("Conectado\n")

s.setblocking(True)

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
        quit_flag = True
        send(msg)
        s.close()
        exit()

    elif msg[:len("JOIN ")] == "JOIN ":
        if msg.find('#') > 0:
            send(msg)
        else:
            msg = format_message(msg,"J")
            send(msg)

    elif msg[:len("PRIVMSG ")] == "PRIVMSG ":
        if msg.find(':') > 0:
            send(msg)
        else:
            msg = format_message(msg,"PM")
            send(msg)

    elif msg[:len("PART ")] == "PART ":
        channel = "#MAIN"
        send(msg)

    elif msg[:len("USER ")] == "USER ":
        send(format_message(msg,"U"))

    else:
        send(msg)

