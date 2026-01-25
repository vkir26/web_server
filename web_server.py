import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 8000))
server.listen(3)
client_socket, client_address = server.accept()
print("Connected by", client_address)
data = client_socket.recv(1024).decode("UTF-8")
print(data)
html_message = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\nHello World!"
client_socket.send(html_message)
