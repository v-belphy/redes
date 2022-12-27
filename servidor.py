import socket
import threading

HOST = ""
PORT = 194
buffer_size = 1024 # Tamanho da mensagem

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

class Channel:
    def __init__(self, name):
        self.name = name
        self.members = []

class User:
    instances = []
    channels = [Channel('VOID'), Channel('MAIN')]

    def __init__(self, sock, address):
        self.sock = sock
        self.address = address[0]
        self.nickname = None
        self.username = None
        self.host = None
        self.realname = None
        self.format_nick = ''
        self.current = self.find_channel('VOID')
        self.current.members += [self]
        self.instances.append(self)

    def find_channel(self, name):
        for channel in self.channels:
            if channel.name == name:
                return channel
        
    def find_user(self, nick):
        for user in self.current.members:
            if user.nickname == nick:
                return user
        else: 
            return None

    def change_channel(self, channel):
        self.current = channel
        self.format_the_nickname()

        # Avisa que entrou no canal
        self.send('Voce entrou no canal "' + channel.name)
        self.send_channel(self.format_nick + " entrou no canal", to_self = False, to_currents_only = True)
        

    def change_nick(self, nickname):
        # Garantir que o nickname e valido
        if ' ' in nickname or len(nickname) > 9:
            self.send("Seu nickname deve conter menos de 9 caracteres e nao ter espaco")

        # Garantir que o nickname nao esta em uso
        elif str(nickname).upper() in [str(user.nickname).upper() for user in self.instances]:
            self.send("Nickname ja esta em uso")

        else:
            old_nickname = self.format_nick
            self.nickname = nickname
            self.format_the_nickname()
            self.send("Voce mudou seu nickname para " + self.format_nick)
            if old_nickname == "":
                self.send_channels(self.format_nick + " entrou no canal", to_self = False)
            else:
                self.send_channels(old_nickname + " mudou seu nickname para " + self.format_nick, to_self = False)

    def format_the_nickname(self):
        # Coloca o nickname em capslock
        self.format_nick = self.nickname.upper()

    def recv(self):
        return self.sock.recv(buffer_size).decode('utf8')
    
    def send(self, msg):
        try:
            self.sock.send(bytes(msg + '\n', 'utf8'))
        except Exception:
            del_user(self)    

    def send_channel(self, msg, to_self = True, to_non_currents_only = False, to_currents_only = False):
        for user in self.current.members:
            if to_non_currents_only and user.current != self.current:
                user.send(msg)
            elif to_currents_only and user.current == self.current:
                user.send(msg)
            elif not to_non_currents_only and not to_currents_only:
                user.send(msg)             

    def send_channels(self, msg, to_self = True, to_current = True, to_MAIN = True):
        sender_channels = []
        for channel in self.channels:
            if self in channel.members:
                if (channel != self.current or to_current) and (channel.name != 'MAIN' or to_MAIN):
                    sender_channels += [channel]
        for user in self.instances:
            if user.current in sender_channels:
                if user.nickname != self.nickname or to_self:
                    user.send(msg)

    def send_all(self, msg, to_self = True):
        for user in self.instances:
            if user.nickname != self.nickname or to_self:
                user.send(msg)


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
        print(user.address + " conectou ao canal")
        threading.Thread(target=func_client, args=(user,)).start()


def func_client(user):
    # Input nickname
    user.send("Digite o seu nickname para continuar:")
    while user.nickname == None:
        proposed_name = user.recv() 
        user.change_nick(proposed_name)

    # Input nome real
    user.send("Digite o seu nome real para continuar:")
    while user.realname == None:
        user.realname = user.recv()

    # T0 D0: Input HOST do usuario

    user.send("Bem vindo(a) " + user.format_nick + '! Digite "/COMANDOS" para verificar os comandos disponiveis.')
    user.current.members.remove(user)

    # Insere o usuario no canal "MAIN"
    channel = user.find_channel('MAIN')
    channel.members += [user]
    user.change_channel(channel)

    # Processa a mensagem do usuario
    while True:
        try: 
            msg = user.recv()
        except:
            print("Falha na conexao: " + user.address)
            del_user(user)
            break

        # Verifica se o usuario enviou um comando
        if msg == "[COMANDO] COMANDOS":
            tmp += "LISTA DE COMANDOS DISPONIVEIS \n"
            tmp += "/NICK: altera seu proprio nickname \n"
            tmp += "/USER (nickname): especifica o nome de usuario, nome do host e nome real de um asuario \n"
            tmp += "/QUIT: finaliza sessao \n"
            tmp += "/JOIN (canal): cria ou entra em um canal \n"
            tmp += "/PART (canal): sai de um canal, o qual esta participando \n"
            tmp += "/LIST: lista os canais existentes e o numero de usuarios no canal \n"
            tmp += "/PRIVMSG (canal/nickname): envia mensagem a um canal ou a um usuario \n"
            tmp += "/WHO (canal): lista os participantes do canal \n"
            user.send(tmp)

        elif msg[:len('[COMANDO] NICK ')] == '[COMANDO] NICK ':
            desired_nickname = msg[len('[COMANDO] NICK '):]
            user.change_nick(desired_nickname)

        #T0 D0: comando USER
        elif msg[:len('[COMANDO] USER ')] == '[COMANDO] USER ':
            msg = msg[len('[COMANDO] USER '):]
            foo = msg.find(':')
            if foo < 0:
                user.send(f"461 {user.nickname} USER :Not enough parameters")
            else:
                user.realname = msg[foo+1:]
                params = msg[:foo]
                if len(params) < 2:
                    user.send(f"461 {user.nickname} USER :Not enough parameters")
                else:
                    user.username = params[0]
                    user.host = user.sock.gethostname()


        elif msg == "[COMANDO] QUIT":
            print(user.address + " encerrou a sessao")
            user.send(user.format_nick + " saiu do canal")
            del_user(user)
            break

        elif msg[:len("[COMANDO] JOIN ")] == "[COMANDO] JOIN ":
            desired_channel = msg[len('[COMANDO] JOIN '):]
            channel = user.find_channel(desired_channel)

            # Caso o canal nao exista
            if channel == None:
                # validacao de nome
                if ' ' in desired_channel or len(desired_channel) > 9 or desired_channel[0]!='#':
                    user.send("ERRO: O nome do servidor nao pode ter espaco, conter mais de 9 caracteres e deve comecar com #")
                else: 
                    new_channel = Channel(desired_channel)
                    user.channels += [new_channel]
                    new_channel.members += [user]
                    user.change_channel(new_channel)
                
            # Caso o canal exista e o usuario nao e membro do canal
            elif user not in channel.members:
                channel.members += [user]
                user.change_channel(channel)
                
            else:
                user.send("Voce ja e um membro do canal")

        elif msg == "[COMANDO] PART":
            # Caso nao estiver no MAIN, sai do canal
            if user.current.name == "MAIN":
                user.send("Voce ja nao faz parte de nenhum canal, com excecao da main")
            else:
                old_channel = user.current
                user.send_channel(user.format_nick + " saiu do canal", to_self = False, to_currents_only = True)
                user.change_channel(user.find_channel('MAIN'))
                if user in old_channel.members: old_channel.members.remove(user)
                # Caso o canal estiver vazio
                if len(old_channel.members) == 0: user.channels.remove(old_channel)

        elif msg == "[COMANDO] LIST":
            tmp = "Canais disponiveis: \n"
            for channel in user.channels:
                if channel.name != 'VOID': 
                    tmp += channel.name + ": " + len(channel.members) + '\n'
            user.send(tmp)

        elif msg[:len("[COMANDO] PRIVMSG ")] == "[COMANDO] PRIVMSG ":
            msg = msg[len("[COMANDO] PRIVMSG "):]
            foo = msg.find(' ')
            (dest,msg) = (msg[:foo],msg[foo+1:])

            if dest[0] == '#':
                target = user.find_channel(dest)
                if target == None:
                    tmp = f"403 {user.nickname} {dest} :No such channel"
                    user.send(tmp)

                else:
                    tmp = f":{user.nickname} PRIVMSG {dest} :{msg}"
                    [target_user.send(tmp) for target_user in target.members if target_user != user]


            else:
                target = user.find_user(dest)
                if target == None:
                    tmp = f"401 {user.nickname} {dest} :No such nick/channel"
                else:
                    tmp = f":{user.nickname} PRIVMSG {dest} :{msg}"
                target.send(tmp)



        elif msg == "[COMANDO] WHO":
            tmp = 'Membros do canal "' + user.current.name + '":\n'
            for client in user.current.members:
                tmp += client.format_nick + '\n'
            user.send(tmp)

        #Se a mensagem nao for o comando, envie para o canal que o usuario faz parte
        else:
            user.send_channel(user.format_nick + ': ' + msg, to_currents_only = True)

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen()

print("Servidor conectado")
thread = threading.Thread(target=connect)
thread.start()
thread.join()
s.close()
