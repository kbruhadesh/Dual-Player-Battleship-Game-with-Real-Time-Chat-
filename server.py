import socket
import threading
import json
import random
import logging
from datetime import datetime, timedelta
import signal
import sys
import queue

class EnhancedBattleshipServer:
    def __init__(self, host="0.0.0.0", port=8000, chat_port=8001):
        # Initialize logging
        self.setup_logging()
        
        # Server settings
        self.host = host
        self.game_port = port
        self.chat_port = chat_port
        self.running = True
        
        # Game constants
        self.GRID_SIZE = 10
        self.TIMEOUT = 30  # seconds
        
        # Game state
        self.games = {}  # Dictionary to store active games
        self.players = {}  # Dictionary to store player information
        self.waiting_queue = queue.Queue()  # Queue for matching players
        
        # Setup server sockets
        self.setup_servers()
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        logging.info("Battleship server initialized")

    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            filename=f'battleship_server_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def setup_servers(self):
        """Initialize server sockets"""
        try:
            # Game server
            self.game_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.game_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.game_server.bind((self.host, self.game_port))
            self.game_server.listen(10)
            
            # Chat server
            self.chat_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chat_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.chat_server.bind((self.host, self.chat_port))
            self.chat_server.listen(10)
            
            logging.info(f"Servers started - Game Port: {self.game_port}, Chat Port: {self.chat_port}")
            
        except Exception as e:
            logging.error(f"Failed to setup servers: {e}")
            sys.exit(1)

    def setup_signal_handlers(self):
        """Setup handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Handle server shutdown"""
        logging.info("Initiating server shutdown...")
        self.running = False
        
        # Close all active games
        for game_id in list(self.games.keys()):
            self.end_game(game_id, "Server shutting down")
        
        # Close server sockets
        self.game_server.close()
        self.chat_server.close()
        
        logging.info("Server shutdown complete")
        sys.exit(0)

    def start(self):
        """Start the server"""
        logging.info("Starting server...")
        print(f"Server running on {self.host}")
        print(f"Game Port: {self.game_port}")
        print(f"Chat Port: {self.chat_port}")
        
        # Start matchmaking thread
        threading.Thread(target=self.matchmaking_loop, daemon=True).start()
        
        # Start accepting connections
        game_thread = threading.Thread(target=self.accept_game_connections)
        chat_thread = threading.Thread(target=self.accept_chat_connections)
        
        game_thread.start()
        chat_thread.start()
        
        game_thread.join()
        chat_thread.join()

    def accept_game_connections(self):
        """Accept game connections"""
        self.game_server.settimeout(1)  # Allow checking self.running
        while self.running:
            try:
                client_socket, address = self.game_server.accept()
                threading.Thread(target=self.handle_new_player,
                              args=(client_socket, address)).start()
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Error accepting game connection: {e}")

    def accept_chat_connections(self):
        """Accept chat connections"""
        self.chat_server.settimeout(1)  # Allow checking self.running
        while self.running:
            try:
                chat_socket, address = self.chat_server.accept()
                threading.Thread(target=self.handle_chat_connection,
                              args=(chat_socket, address)).start()
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Error accepting chat connection: {e}")

    def handle_new_player(self, client_socket, address):
        """Handle new player connection"""
        try:
            # Generate player ID
            player_id = self.generate_player_id()
            
            # Initialize player data
            self.players[player_id] = {
                'socket': client_socket,
                'address': address,
                'game_id': None,
                'ships': {},
                'ready': False,
                'last_action': datetime.now()
            }
            
            # Add to matching queue
            self.waiting_queue.put(player_id)
            
            logging.info(f"New player {player_id} connected from {address}")
            
            # Send player their ID
            self.send_game_message(client_socket, {
                'type': 'connect',
                'player_id': player_id
            })
            
            # Start listening for player messages
            self.handle_player_messages(player_id)
            
        except Exception as e:
            logging.error(f"Error handling new player: {e}")
            client_socket.close()

    def handle_chat_connection(self, chat_socket, address):
        """Handle chat connection"""
        try:
            while self.running:
                try:
                    message = chat_socket.recv(1024).decode()
                    if not message:
                        break
                    
                    # Parse message
                    data = json.loads(message)
                    game_id = data.get('game_id')
                    player_id = data.get('player_id')
                    
                    if game_id in self.games:
                        self.broadcast_chat(game_id, player_id, data.get('message'))
                        
                except Exception as e:
                    logging.error(f"Error handling chat message: {e}")
                    break
                    
        finally:
            chat_socket.close()

    def matchmaking_loop(self):
        """Main matchmaking loop"""
        while self.running:
            try:
                # Need two players to start a game
                if self.waiting_queue.qsize() >= 2:
                    player1_id = self.waiting_queue.get()
                    player2_id = self.waiting_queue.get()
                    
                    # Verify players are still connected
                    if (player1_id in self.players and 
                        player2_id in self.players):
                        self.create_game(player1_id, player2_id)
                    else:
                        # Put back valid player if any
                        if player1_id in self.players:
                            self.waiting_queue.put(player1_id)
                        if player2_id in self.players:
                            self.waiting_queue.put(player2_id)
                
                # Sleep to prevent CPU spinning
                threading.Event().wait(0.1)
                
            except Exception as e:
                logging.error(f"Error in matchmaking: {e}")

    def create_game(self, player1_id, player2_id):
        """Create a new game"""
        game_id = self.generate_game_id()
        
        game = {
            'id': game_id,
            'players': [player1_id, player2_id],
            'current_turn': random.choice([player1_id, player2_id]),
            'state': 'setup',
            'start_time': datetime.now(),
            'board_size': self.GRID_SIZE,
            'moves': [],
            'chat_history': []
        }
        
        self.games[game_id] = game
        
        # Update player game IDs
        self.players[player1_id]['game_id'] = game_id
        self.players[player2_id]['game_id'] = game_id
        
        # Notify players
        for player_id in [player1_id, player2_id]:
            self.send_game_message(self.players[player_id]['socket'], {
                'type': 'game_start',
                'game_id': game_id,
                'player_id': player_id,
                'opponent_id': player2_id if player_id == player1_id else player1_id,
                'board_size': self.GRID_SIZE,
                'first_turn': game['current_turn']
            })
        
        logging.info(f"Created game {game_id} with players {player1_id} and {player2_id}")

    def handle_player_messages(self, player_id):
        """Handle messages from a player"""
        player = self.players[player_id]
        socket = player['socket']
        
        while self.running:
            try:
                data = socket.recv(1024).decode()
                if not data:
                    break
                
                message = json.loads(data)
                self.process_game_message(player_id, message)
                
                # Update last action time
                player['last_action'] = datetime.now()
                
            except json.JSONDecodeError:
                logging.error(f"Invalid JSON from player {player_id}")
            except Exception as e:
                logging.error(f"Error handling player {player_id} message: {e}")
                break
        
        self.handle_player_disconnect(player_id)

    def process_game_message(self, player_id, message):
        """Process a game message from a player"""
        msg_type = message.get('type')
        game_id = self.players[player_id]['game_id']
        
        if not game_id:
            return
        
        game = self.games[game_id]
        
        if msg_type == 'place_ships':
            self.handle_ship_placement(player_id, game_id, message.get('ships', {}))
        elif msg_type == 'shot':
            self.handle_shot(player_id, game_id, message.get('position'))
        elif msg_type == 'ready':
            self.handle_player_ready(player_id, game_id)
        elif msg_type == 'surrender':
            self.handle_surrender(player_id, game_id)

    def handle_ship_placement(self, player_id, game_id, ships):
        """Handle ship placement"""
        player = self.players[player_id]
        game = self.games[game_id]
        
        # Validate ship placement
        if self.validate_ship_placement(ships):
            player['ships'] = ships
            player['ready'] = True
            
            # Check if both players are ready
            if all(self.players[p_id]['ready'] for p_id in game['players']):
                self.start_battle_phase(game_id)
            else:
                # Notify player waiting for opponent
                self.send_game_message(player['socket'], {
                    'type': 'wait_opponent_setup'
                })

    def handle_shot(self, player_id, game_id, position):
        """Handle a shot"""
        game = self.games[game_id]
        
        # Verify it's player's turn
        if game['current_turn'] != player_id:
            return
        
        # Get opponent
        opponent_id = game['players'][0] if game['players'][1] == player_id else game['players'][1]
        opponent_ships = self.players[opponent_id]['ships']
        
        # Check if hit
        hit = self.check_hit(position, opponent_ships)
        
        # Record move
        game['moves'].append({
            'player': player_id,
            'position': position,
            'hit': hit,
            'time': datetime.now()
        })
        
        # Send results to both players
        self.broadcast_shot_result(game_id, player_id, position, hit)
        
        # Check for game over
        if self.check_game_over(opponent_ships):
            self.end_game(game_id, winner=player_id)
        else:
            # Switch turns
            game['current_turn'] = opponent_id
            self.notify_turn_change(game_id)

    def validate_ship_placement(self, ships):
        """Validate ship placement"""
        # Implementation of ship placement validation
        # This would check for valid positions, no overlapping, etc.
        return True  # Simplified for this example

    def check_hit(self, position, ships):
        """Check if a shot hits a ship"""
        for ship_positions in ships.values():
            if position in ship_positions:
                return True
        return False

    def check_game_over(self, ships):
        """Check if all ships are sunk"""
        # Implementation of game over check
        return False  # Simplified for this example

    def broadcast_shot_result(self, game_id, shooter_id, position, hit):
        """Broadcast shot result to both players"""
        game = self.games[game_id]
        
        for player_id in game['players']:
            self.send_game_message(self.players[player_id]['socket'], {
                'type': 'shot_result',
                'shooter': shooter_id,
                'position': position,
                'hit': hit
            })

    def notify_turn_change(self, game_id):
        """Notify players of turn change"""
        game = self.games[game_id]
        
        for player_id in game['players']:
            self.send_game_message(self.players[player_id]['socket'], {
                'type': 'turn_change',
                'current_turn': game['current_turn']
            })

    def broadcast_chat(self, game_id, sender_id, message):
        """Broadcast chat message to all players in a game"""
        game = self.games[game_id]
        
        for player_id in game['players']:
            if player_id != sender_id:
                try:
                    self.send_game_message(self.players[player_id]['socket'], {
                        'type': 'chat',
                        'sender': sender_id,
                        'message': message
                    })
                except Exception as e:
                    logging.error(f"Error sending chat message: {e}")

    def end_game(self, game_id, winner=None, reason=None):
        """End a game"""
        game = self.games[game_id]
        
        # Notify players
        for player_id in game['players']:
            try:
                self.send_game_message(self.players[player_id]['socket'], {
                    'type': 'game_over',
                    'winner': winner,
                    'reason': reason
                })
            except Exception as e:
                logging.error(f"Error notifying game over: {e}")
        
        # Cleanup
        self.cleanup_game(game_id)

    def cleanup_game(self, game_id):
        """Clean up game resources"""
        if game_id in self.games:
            game = self.games[game_id]
            
            # Clean up player references