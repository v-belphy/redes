import socket
import threading

HOST = "localhost"
PORT = 6666
buffer_size = 1024 #tamanho da mensagem
usuarios = []

#COMANDOS BASICOS DE USER:
    #NICK
    #USER
    #QUIT

#COMANDOS DE CANAL:
    #JOIN
    #PART
    #LIST

#COMANDOS AVANCADOS:
    #PRIVMSG
    #WHO

def change_nick(self, nickname):
    # Nao pode ter apelido repetido
    if nickname in [user.nickname for user in self.instances]:
        self.send("ERRO: apelido ja esta em uso")

    # Maximo 9 caracteres, sem espaco
    elif ' ' in nickname or len(nickname) > 9:
        self.send("ERRO: apelido com o uso de espaco ou com mais de 9 caracteres")

    else:
        old_nickname = self.format_nick
        self.nickname = nickname
        self.send(old_nickname + " mudou o apelido para " + self.format_nick)

###############################################################################################
def messagesTreatment(conexao):
    while True:
        try: 
            msg = conexao.recv(buffer_size)
            for user in usuarios:
                 if user != conexao:
                    try:
                        user.send(msg)
                    except:
                        usuarios.remove(user)
        except:
            usuarios.remove(conexao)
            break

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

while True:
    conexao, address = s.accept()
    usuarios.append(conexao)
    
    thread = threading.Thread(target=messagesTreatment, args=[conexao])
    thread.start()