import socket
import threading
import sys

HOST = "localhost"
PORT = 194
buffer_size = 1024 # Tamanho da mensagem

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

class Channel:
    def __init__(self, name):
        self.name = name
        self.members = []

class User:
    instances = []
    channels = [Channel('#VOID'), Channel('#MAIN')]

    def __init__(self, sock, address):
        self.sock = sock
        self.address = address[0]
        self.nickname = None
        self.username = None
        self.host = None
        self.realname = None
        self.format_nick = ''
        self.current = self.find_channel('#VOID')
        self.current.members += [self]
        self.instances.append(self)

    def find_channel(self, name):
        for channel in self.channels:
            if channel.name == name:
                return channel
        else:
            return None
        
    def find_user(self, nick):
        for user in self.instances:
            if user.nickname == nick:
                return user
        else: 
            return None

    def change_channel(self, channel):
        self.current.members.remove(self)
        if len(self.current.members) == 0 and self.current.name!="#VOID" and self.current.name!="#MAIN":
            self.channels.remove(self.current)
        self.current = channel
        channel.members += [self]


    def change_nick(self, nickname,cadastro=False):
        # Garantir que o nickname e valido
        if ' ' in nickname or len(nickname) > 9:
            # self.send("Seu nickname deve conter menos de 9 caracteres e nao ter espaco")
            self.send(f":server 431 {self.nickname} {nickname} :Erroneus nickname")

        # Garantir que o nickname nao esta em uso
        elif str(nickname).upper() in [str(user.nickname).upper() for user in self.instances]:
            # self.send("Nickname ja esta em uso")
            self.send(f":server 433 {self.nickname} {nickname} :Nickname is already in use")

        else:
            old_nickname = self.nickname
            self.nickname = nickname
            if not cadastro:
                self.send_all(f":{old_nickname} NICK {nickname}")



    def format_the_nickname(self):
        # Coloca o nickname em capslock
        self.format_nick = self.nickname.upper()

    def recv(self):
        msg = self.sock.recv(buffer_size).decode("utf-8")
        print(f"{msg} <- {self.nickname}")
        return msg
    
    def send(self, msg):
        try:
            print(f"{msg} -> {self.nickname}")
            self.sock.send(bytes(msg + '\n', 'utf-8'))
        except Exception:
            del_user(self)    

    def send_channel(self, msg):
        [target.send(msg) for target in self.current.members if target != self]

    def send_all(self, msg:str, to_self = False):
        [user.send(msg) for user in self.instances if user != self or to_self]


def del_user(user):
    for channel in user.channels:
        if user in channel.members: channel.members.remove(user)
    user.sock.close()
    if user in user.instances: user.instances.remove(user)


def connect():
    # Processa conexao do cliente ao servidor
    while True:
        client, client_address = s.accept()
        user = User(client, client_address)
        # print(user.address + " conectou ao canal")
        threading.Thread(target=func_client, args=(user,)).start()


def func_client(user):
    # Input nickname
    while user.nickname == None:
        proposed_name = user.recv() 
        user.change_nick(proposed_name[len("NICK "):], cadastro=True)

    # Input nome real
    while user.realname == None:
        msg = user.recv().split()
        (username,realname) = (msg[1],msg[3][1:])
        user.username = username
        user.realname = realname
        user.host = socket.gethostbyaddr(user.address)[0]

    # Insere o usuario no canal "MAIN"
    channel = user.find_channel('#MAIN')
    user.change_channel(channel)

    # Processa a mensagem do usuario
    while True:
        try: 
            msg = user.recv()
        except:
            print("Falha na conexao: " + user.address)
            del_user(user)
            break

        # NICK
        if msg[:len('NICK ')] == 'NICK ':
            desired_nickname = msg[len('NICK '):]
            user.change_nick(desired_nickname)

        # USER
        elif msg[:len('USER ')] == 'USER ':
            msg = msg[len('USER '):]
            foo = msg.find(':')
            if foo < 0:
                user.send(f":server 461 {user.nickname} USER :Not enough parameters")
            else:
                user.realname = msg[foo+1:]
                params = msg[:foo]
                if len(params) < 2:
                    user.send(f":server 461 {user.nickname} USER :Not enough parameters")
                else:
                    user.username = params[0]
                    user.host = user.sock.gethostname()

        # QUIT
        elif msg == "QUIT":
            print(user.address + " encerrou a sessao")
            del_user(user)
            break

        # JOIN
        elif msg[:len("JOIN ")] == "JOIN ":
            desired_channel = msg[len('JOIN '):]
            channel = user.find_channel(desired_channel)

            # Caso o canal nao exista
            if channel == None:
                # validacao de nome
                if ' ' in desired_channel or len(desired_channel) > 9 or desired_channel[0]!='#':
                    user.send(f":server 432 {user.nickname} {desired_channel} :Erroneus name")
                else: 
                    channel = Channel(desired_channel)
                    user.channels+=[channel]
                    user.change_channel(channel)
                    user.send_channel(f":{user.nickname} {msg}")
                
            # Caso o canal exista e o usuario nao e membro do canal
            elif user not in channel.members:
                user.change_channel(channel)
                user.send_channel(f":{user.nickname} {msg}")
            
            tmp = f":server 353 {user.nickname} = {desired_channel} :"
            for memb in channel.members:
                tmp += f"{memb.nickname} "
            user.send(tmp[:-1])
            user.send(f":server 366 {user.nickname} {desired_channel} :End of/NAMES list")

        # PART
        elif msg == "PART":
            # Caso nao estiver no MAIN, sai do canal
            if user.current.name != "#MAIN":
                old = user.current
                user.change_channel(user.find_channel('#MAIN'))
                [target.send(f":{user.nickname} PART") for target in old.members]

        # LIST
        elif msg == "LIST":
            user.send(f":server 321 {user.nickname} Channel:Users Name")
            print(user.channels)
            [user.send(f":server 322 {user.nickname} {chan.name}:{len(chan.members)}") for chan in user.channels[2:]]
            user.send(f":server 323 {user.nickname} End of/LIST")

        # PRIVMSG
        elif msg[:len("PRIVMSG ")] == "PRIVMSG ":
            msg_tmp = msg[len("PRIVMSG "):]

            dest = msg_tmp[:msg_tmp.find(' ')]
            if dest[0] == '#':
                target = user.find_channel(dest)
                if target == None:
                    user.send(f":server 403 {user.nickname} {dest} :No such channel")

                else:
                    tmp = f":{user.nickname} " + msg
                    [target_user.send(tmp) for target_user in target.members if target_user != user]

            else:
                target = user.find_user(dest)
                if target == None:
                    user.send(f":server 401 {user.nickname} {dest} :No such nick/channel")
                else:
                    target.send(f":{user.nickname} " + msg)

        # WHO
        elif msg[:len("WHO ")] == "WHO ":
            name = msg[len("WHO "):]
            if name[0] == '#':
                target = user.find_channel(name)
                if target == None:
                    target = user.current

                for target_user in target.members:
                    user.send(f":server 352 {user.nickname} {target.name} {target_user.host} {target_user.nickname} H :{target_user.realname}")
            else:
                target = user.find_user(name)
                if target == None:
                    (f":server 401 {user.nickname} {dest} :No such nick/channel")
                else:
                    user.send(f":server 352 {user.nickname} {target.current.name} {target.host} {target.nickname} H :{target.realname}")
            user.send(f":server 315 {user.nickname} {name} :End of/WHO list")
        
        else:
            user.send(f":server 421 {user.nickname} {msg.split()[0]} :Unknown command")

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen()

print("Servidor conectado")
thread = threading.Thread(target=connect)
thread.start()
thread.join()
s.close()