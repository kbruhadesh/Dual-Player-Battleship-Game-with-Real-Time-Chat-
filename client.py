import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import json
import random
from PIL import Image, ImageTk
import os
import time

class EnhancedBattleshipClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Battleship Battle")
        self.root.configure(bg='#1A237E')
        self.root.minsize(1200, 800)
        
        # Game variables
        self.grid_size = 10
        self.setup_phase = True
        self.is_turn = False
        self.current_ship = None
        self.ship_orientation = 'horizontal'
        
        # Game state
        self.player_board = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.opponent_board = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.ships = {
            'carrier': {'size': 5, 'placed': False},
            'battleship': {'size': 4, 'placed': False},
            'cruiser': {'size': 3, 'placed': False},
            'submarine': {'size': 3, 'placed': False},
            'destroyer': {'size': 2, 'placed': False}
        }
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'total_shots': 0,
            'games_played': 0,
            'wins': 0
        }
        
        # Setup network connection
        self.setup_network()
        
        # Setup GUI
        self.setup_styles()
        self.create_layout()
        self.create_boards()
        self.setup_chat()
        self.create_ship_placement_panel()
        
        # Start network threads
        self.start_network_threads()

    def setup_network(self):
        """Initialize network connections"""
        try:
            self.game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Get server details
            self.server_ip = simpledialog.askstring(
                "Server Connection",
                "Enter Server IP:",
                initialvalue="localhost"
            )
            self.game_port = 8000
            self.chat_port = 8001
            
            # Connect to server
            self.game_socket.connect((self.server_ip, self.game_port))
            self.chat_socket.connect((self.server_ip, self.chat_port))
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
            self.root.quit()

    def setup_styles(self):
        """Configure GUI styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Color scheme
        self.colors = {
            'background': '#1A237E',
            'grid_bg': '#E8EAF6',
            'ship': '#303F9F',
            'hit': '#F44336',
            'miss': '#90A4AE',
            'water': '#64B5F6',
            'hover': '#7986CB'
        }
        
        # Custom styles
        self.style.configure(
            'Game.TFrame',
            background=self.colors['background']
        )
        self.style.configure(
            'Board.TFrame',
            background=self.colors['grid_bg'],
            relief='raised',
            borderwidth=2
        )

    def create_layout(self):
        """Create main game layout"""
        # Main container
        self.main_frame = ttk.Frame(self.root, style='Game.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Top section - Game info
        self.info_frame = ttk.Frame(self.main_frame)
        self.info_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.title_label = ttk.Label(
            self.info_frame,
            text="BATTLESHIP WARFARE",
            font=('Arial', 24, 'bold'),
            foreground='white',
            background=self.colors['background']
        )
        self.title_label.pack()
        
        self.status_label = ttk.Label(
            self.info_frame,
            text="Waiting for opponent...",
            font=('Arial', 16),
            foreground='white',
            background=self.colors['background']
        )
        self.status_label.pack()
        
        # Game boards container
        self.boards_frame = ttk.Frame(self.main_frame)
        self.boards_frame.pack(fill=tk.BOTH, expand=True)

    def create_boards(self):
        """Create game boards"""
        # Player's board
        self.player_frame = ttk.Frame(self.boards_frame, style='Board.TFrame')
        self.player_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(
            self.player_frame,
            text="YOUR FLEET",
            font=('Arial', 14, 'bold')
        ).pack(pady=5)
        
        self.create_grid('player')
        
        # Opponent's board
        self.opponent_frame = ttk.Frame(self.boards_frame, style='Board.TFrame')
        self.opponent_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Label(
            self.opponent_frame,
            text="ENEMY WATERS",
            font=('Arial', 14, 'bold')
        ).pack(pady=5)
        
        self.create_grid('opponent')

    def create_grid(self, board_type):
        """Create game grid"""
        grid_frame = ttk.Frame(
            self.player_frame if board_type == 'player' else self.opponent_frame
        )
        grid_frame.pack(padx=10, pady=10)
        
        # Create buttons
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                btn = tk.Button(
                    grid_frame,
                    width=3,
                    height=1,
                    bg=self.colors['water'],
                    relief=tk.RAISED,
                    command=lambda r=row, c=col: self.grid_click(board_type, r, c)
                )
                btn.grid(row=row, column=col, padx=1, pady=1)
                
                if board_type == 'player':
                    self.player_board[row][col] = btn
                else:
                    self.opponent_board[row][col] = btn

    def setup_chat(self):
        """Create chat interface"""
        self.chat_frame = ttk.Frame(self.main_frame)
        self.chat_frame.pack(fill=tk.X, pady=20)
        
        # Chat display
        self.chat_display = tk.Text(
            self.chat_frame,
            height=6,
            width=50,
            state=tk.DISABLED
        )
        self.chat_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.chat_frame, command=self.chat_display.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display['yscrollcommand'] = scrollbar.set
        
        # Chat input
        self.chat_input = ttk.Entry(self.main_frame)
        self.chat_input.pack(fill=tk.X, pady=(0, 20))
        self.chat_input.bind('<Return>', self.send_chat)

    def create_ship_placement_panel(self):
        """Create ship placement interface"""
        self.placement_frame = ttk.Frame(self.main_frame)
        self.placement_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Ship selection buttons
        for ship, data in self.ships.items():
            btn = ttk.Button(
                self.placement_frame,
                text=f"{ship.title()} ({data['size']})",
                command=lambda s=ship: self.select_ship(s)
            )
            btn.pack(side=tk.LEFT, padx=5)
        
        # Rotation button
        self.rotate_btn = ttk.Button(
            self.placement_frame,
            text="Rotate Ship",
            command=self.toggle_orientation
        )
        self.rotate_btn.pack(side=tk.LEFT, padx=5)

    def start_network_threads(self):
        """Start network listening threads"""
        threading.Thread(target=self.listen_for_game_messages, daemon=True).start()
        threading.Thread(target=self.listen_for_chat_messages, daemon=True).start()

    def listen_for_game_messages(self):
        """Listen for game server messages"""
        while True:
            try:
                data = self.game_socket.recv(4096).decode()
                if not data:
                    break
                    
                self.handle_game_message(json.loads(data))
                
            except Exception as e:
                print(f"Game connection error: {e}")
                break
        
        self.handle_disconnection()

    def listen_for_chat_messages(self):
        """Listen for chat messages"""
        while True:
            try:
                data = self.chat_socket.recv(4096).decode()
                if not data:
                    break
                    
                self.display_chat_message(data)
                
            except Exception as e:
                print(f"Chat connection error: {e}")
                break

    def handle_game_message(self, data):
        """Process game messages from server"""
        msg_type = data.get('type')
        
        if msg_type == 'turn':
            self.handle_turn_message(data)
        elif msg_type == 'shot_result':
            self.handle_shot_result(data)
        elif msg_type == 'game_over':
            self.handle_game_over(data)
        elif msg_type == 'opponent_disconnected':
            self.handle_opponent_disconnection()

    def grid_click(self, board_type, row, col):
        """Handle grid button clicks"""
        if self.setup_phase and board_type == 'player':
            self.handle_ship_placement(row, col)
        elif not self.setup_phase and board_type == 'opponent' and self.is_turn:
            self.handle_shot(row, col)

    def handle_ship_placement(self, row, col):
        """Handle ship placement during setup"""
        if not self.current_ship:
            messagebox.showinfo("Ship Selection", "Please select a ship first!")
            return
            
        ship_data = self.ships[self.current_ship]
        if ship_data['placed']:
            messagebox.showinfo("Ship Placed", "This ship has already been placed!")
            return
            
        if self.can_place_ship(row, col, ship_data['size']):
            self.place_ship(row, col, ship_data['size'])
            ship_data['placed'] = True
            
            # Check if all ships are placed
            if all(ship['placed'] for ship in self.ships.values()):
                self.complete_setup()

    def send_chat(self, event=None):
        """Send chat message"""
        message = self.chat_input.get().strip()
        if message:
            self.chat_socket.send(message.encode())
            self.chat_input.delete(0, tk.END)

    def display_chat_message(self, message):
        """Display chat message"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{message}\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def handle_disconnection(self):
        """Handle disconnection from server"""
        messagebox.showerror(
            "Connection Lost",
            "Lost connection to the server. The game will now close."
        )
        self.root.quit()

    def run(self):
        """Start the game client"""
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    client = EnhancedBattleshipClient(root)
    client.run()