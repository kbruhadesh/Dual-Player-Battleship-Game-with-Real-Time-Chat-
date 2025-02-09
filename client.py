import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

class BattleshipClient:
    def _init_(self, root):
        self.root = root
        self.root.title("Dual Player Battleship with Chat")
        self.root.configure(bg='#2C3E50')

        # Network setup
        self.client_game = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_chat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to the server
        self.server_ip = simpledialog.askstring("Server Connection", "Enter Server IP:", initialvalue="192.168.10.253")
        self.server_port = simpledialog.askinteger("Server Connection", "Enter Game Server Port:", initialvalue=8000)
        self.chat_port = self.server_port + 1  # Chat port assumed to be +1 of game port

        try:
            self.client_game.connect((self.server_ip, self.server_port))
            self.client_chat.connect((self.server_ip, self.chat_port))
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
            self.root.quit()
            return

        # Game variables
        self.grid_size = 5
        self.buttons = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.is_turn = False
        self.hits = 0
        self.misses = 0

        # Setup styling
        self.setup_styles()

        # Layout setup
        self.setup_gui()

        # Start listening to server messages
        self.start_threads()

    def setup_styles(self):
        """Set up custom styles for the game."""
        self.root.option_add("*Font", "Arial 10")
        self.style = {
            'button_default': {
                'width': 4,
                'height': 2,
                'font': ('Arial', 10, 'bold'),
                'relief': tk.RAISED,
                'borderwidth': 3
            },
            'hit': {
                'bg': '#E74C3C',  # Bright red
                'fg': 'white'
            },
            'miss': {
                'bg': '#95A5A6',  # Gray
                'fg': 'white'
            },
            'opponent_hit': {
                'bg': '#F39C12',  # Orange
                'fg': 'black'
            },
            'opponent_miss': {
                'bg': '#BDC3C7',  # Light gray
                'fg': 'black'
            }
        }

    def setup_gui(self):
        """Sets up the game GUI."""
        # Title Frame
        self.title_frame = tk.Frame(self.root, bg='#2C3E50')
        self.title_frame.pack(pady=10)

        title_label = tk.Label(
            self.title_frame,
            text="Multiplayer Battleship with Chat",
            font=("Arial", 16, "bold"),
            fg='white',
            bg='#2C3E50'
        )
        title_label.pack()

        # Info Frame
        self.info_frame = tk.Frame(self.root, bg='#34495E')
        self.info_frame.pack(pady=10)

        self.turn_label = tk.Label(
            self.info_frame,
            text="Connecting to server...",
            font=("Arial", 14, "bold"),
            fg='#ECF0F1',
            bg='#34495E'
        )
        self.turn_label.pack(padx=20, pady=10)

        # Grid Frame
        self.grid_frame = tk.Frame(self.root, bg='#2C3E50')
        self.grid_frame.pack()

        for row in range(self.grid_size):
            for col in range(self.grid_size):
                btn = tk.Button(
                    self.grid_frame,
                    text=" ",
                    command=lambda r=row, c=col: self.fire(r, c),
                    **self.style['button_default'],
                    bg='#3498DB',
                    activebackground='#2980B9'
                )
                btn.grid(row=row, column=col, padx=2, pady=2)
                self.buttons[row][col] = btn

        # Chat Frame
        self.chat_frame = tk.Frame(self.root, bg='#34495E')
        self.chat_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.chat_log = tk.Text(self.chat_frame, state=tk.DISABLED, height=10, bg='#ECF0F1', fg='#2C3E50', wrap=tk.WORD)
        self.chat_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_entry = tk.Entry(self.chat_frame, bg='#ECF0F1', fg='#2C3E50')
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)
        self.chat_entry.bind("<Return>", lambda _: self.send_chat())

        send_button = tk.Button(self.chat_frame, text="Send", command=self.send_chat, bg='#3498DB', fg='white')
        send_button.pack(side=tk.LEFT, padx=10, pady=10)

    def start_threads(self):
        """Start threads to listen for game and chat messages."""
        threading.Thread(target=self.listen_to_server, daemon=True).start()
        threading.Thread(target=self.listen_to_chat, daemon=True).start()

    def listen_to_server(self):
        """Listens for messages from the server."""
        while True:
            try:
                data = self.client_game.recv(1024).decode()

                if data.startswith("HIT"):
                    _, coords = data.split(":")
                    r, c = map(int, coords.split(","))
                    self.buttons[r][c].config(text="X", **self.style['hit'])
                    self.hits += 1

                elif data.startswith("MISS"):
                    _, coords = data.split(":")
                    r, c = map(int, coords.split(","))
                    self.buttons[r][c].config(text="O", **self.style['miss'])
                    self.misses += 1

                elif data.startswith("Opponent HIT"):
                    _, coords = data.split(":")
                    r, c = map(int, coords.split(","))
                    self.buttons[r][c].config(text="O", **self.style['opponent_hit'])

                elif data.startswith("Opponent MISS"):
                    _, coords = data.split(":")
                    r, c = map(int, coords.split(","))
                    self.buttons[r][c].config(text="O", **self.style['opponent_miss'])

                elif "Your turn" in data:
                    self.is_turn = True
                    self.turn_label.config(text="Your Turn!", fg="#2ECC71")

                elif "Not your turn" in data:
                    self.is_turn = False
                    self.turn_label.config(text="Opponent's Turn", fg="#E74C3C")

                elif "You won!" in data:
                    messagebox.showinfo("Game Over", "You won!")
                    self.root.quit()

                elif "You lost!" in data:
                    messagebox.showinfo("Game Over", "You lost!")
                    self.root.quit()

            except Exception as e:
                messagebox.showerror("Connection Error", f"Lost connection: {e}")
                break

    def listen_to_chat(self):
        """Listens for chat messages from the server."""
        while True:
            try:
                message = self.client_chat.recv(1024).decode()
                self.display_chat_message(message)
            except Exception as e:
                self.display_chat_message(f"Chat error: {e}")
                break

    def display_chat_message(self, message):
        """Displays a chat message in the chat log."""
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, f"{message}\n")
        self.chat_log.see(tk.END)
        self.chat_log.config(state=tk.DISABLED)

    def send_chat(self):
        """Sends a chat message to the server."""
        message = self.chat_entry.get()
        if message.strip():
            self.client_chat.send(message.encode())
            self.display_chat_message(f"You: {message}")
            self.chat_entry.delete(0, tk.END)

    def fire(self, row, col):
        """Handles the firing action."""
        if not self.is_turn:
            messagebox.showinfo("Wait", "It's not your turn!")
            return

        self.client_game.send(f"{row},{col}".encode())
        self.is_turn = False
        self.turn_label.config(text="Waiting for opponent...", fg="#E67E22")
        self.buttons[row][col].config(state=tk.DISABLED)

if __name__ == "_main_":
    root = tk.Tk()
    BattleshipClient(root)
    root.mainloop()
