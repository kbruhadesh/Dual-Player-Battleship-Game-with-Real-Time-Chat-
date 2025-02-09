import socket
import threading

class BattleshipServer:
    def _init_(self, host="0.0.0.0", port=8000, chat_port=8001):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(2)

        self.chat_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_server.bind((host, chat_port))
        self.chat_server.listen(2)

        print("Server started. Waiting for players...")
        self.clients = []  # Game sockets
        self.chat_clients = []  # Chat sockets
        self.turn = 0  # Player 0 starts
        self.grid_size = 5
        self.ships = [{(1, 1), (2, 2), (3, 3)},  # Player 1's ships
                      {(0, 0), (1, 2), (4, 4)}]  # Player 2's ships

    def broadcast(self, message, exclude_client=None):
        """Send a message to all clients except the excluded one."""
        for client in self.clients:
            if client != exclude_client:
                client.send(message.encode())

    def handle_game(self, client, client_id):
        """Handle player actions."""
        while True:
            try:
                data = client.recv(1024).decode()

                if not data:
                    break

                if self.turn != client_id:
                    client.send("Not your turn".encode())
                    continue

                if data.startswith("CHAT:"):
                    self.handle_chat(data[5:], client_id)
                    continue

                row, col = map(int, data.split(","))
                opponent_id = 1 - client_id
                opponent_ships = self.ships[opponent_id]

                if (row, col) in opponent_ships:
                    opponent_ships.remove((row, col))
                    client.send(f"HIT:{row},{col}".encode())
                    self.clients[opponent_id].send(f"Opponent HIT:{row},{col}".encode())

                    if not opponent_ships:
                        client.send("You won!".encode())
                        self.clients[opponent_id].send("You lost!".encode())
                        break
                else:
                    client.send(f"MISS:{row},{col}".encode())
                    self.clients[opponent_id].send(f"Opponent MISS:{row},{col}".encode())

                # Switch turn
                self.turn = opponent_id
                self.clients[self.turn].send("Your turn".encode())
                self.clients[1 - self.turn].send("Not your turn".encode())

            except Exception as e:
                print(f"Error handling client {client_id}: {e}")
                break

        client.close()

    def handle_chat(self, message, client_id):
        """Handle chat messages and forward them to the opponent."""
        opponent_id = 1 - client_id
        try:
            chat_message = f"CHAT:Player {client_id + 1}: {message}"
            self.chat_clients[opponent_id].send(chat_message.encode())
        except Exception as e:
            print(f"Error sending chat message from Player {client_id + 1}: {e}")

    def handle_chat_client(self, chat_client, client_id):
        """Handle chat communication for a specific client."""
        while True:
            try:
                data = chat_client.recv(1024).decode()
                if data:
                    self.handle_chat(data, client_id)
            except Exception as e:
                print(f"Chat error with Player {client_id + 1}: {e}")
                break

        chat_client.close()

    def start(self):
        """Start the game server."""
        while len(self.clients) < 2:
            client, addr = self.server.accept()
            self.clients.append(client)
            print(f"Player {len(self.clients)} connected from {addr}")

        while len(self.chat_clients) < 2:
            chat_client, addr = self.chat_server.accept()
            self.chat_clients.append(chat_client)
            print(f"Player {len(self.chat_clients)} connected to chat from {addr}")

        if len(self.clients) == 2 and len(self.chat_clients) == 2:
            print("Two players connected. Starting the game!")
            self.clients[0].send("Your turn".encode())
            self.clients[1].send("Not your turn".encode())

            threading.Thread(target=self.handle_game, args=(self.clients[0], 0)).start()
            threading.Thread(target=self.handle_game, args=(self.clients[1], 1)).start()

            threading.Thread(target=self.handle_chat_client, args=(self.chat_clients[0], 0)).start()
            threading.Thread(target=self.handle_chat_client, args=(self.chat_clients[1], 1)).start()

if __name__ == "_main_":
    server = BattleshipServer()
    server.start()
