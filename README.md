# Dual Player Battleship Game with Real-Time Chat

## Overview
The **Dual Player Battleship Game with Real-Time Chat** is an interactive multiplayer game developed using Python. The game allows two players to compete in a turn-based strategy game where they attempt to locate and sink each other's ships on a 5x5 grid. Additionally, it features real-time chat functionality to enhance player interaction.

## Features
- **Multiplayer Gameplay**
  - Players take turns guessing the opponent's ship positions.
  - The first player to sink all opponent ships wins.
- **Real-Time Chat**
  - Players can communicate through an in-game chat feature.
- **Graphical User Interface (GUI)**
  - Built using Tkinter for a user-friendly experience.
  - Displays game board, turn updates, and real-time chat.
- **Technical Implementation**
  - Uses **socket programming** for server-client communication.
  - Implements **multithreading** for handling multiple connections simultaneously.

## Technologies Used
- Python
- Tkinter (GUI)
- Socket Programming (TCP)
- Multithreading

## Installation
### Prerequisites
Ensure you have **Python 3.x** installed on your system.

### Steps
1. **Clone the repository**
   ```bash
   git clone https://github.com/kbruhadesh/Dual Player Battleship Game with Real-Time Chat.git
   cd Battleship-Game
   ```
2. **Install dependencies**
   ```bash
   pip install tkinter
   ```
3. **Run the server**
   ```bash
   python server.py
   ```
4. **Run the client (on both player machines)**
   ```bash
   python client.py
   ```

## How to Play
1. **Start the server** on one machine.
2. **Start the client** on two separate machines and connect to the server.
3. **Enter the IP address** of the server when prompted.
4. **Place your ships** on the 5x5 grid.
5. **Take turns guessing** opponent ship locations.
6. The game ends when one player sinks all of the opponent's ships.
7. Use the **chat feature** to communicate with the opponent.

## Project Structure
```
Battleship-Game/
│── server.py         # Server-side script to handle game logic & connections
│── client.py         # Client-side script with GUI and game logic
│── README.md         # Project documentation
```

## Future Enhancements
- Increase grid size for more complex gameplay.
- Add AI opponents for single-player mode.
- Introduce additional ship types with different attributes.
- Support for more than two players.

## Contributors
- **Bruhadesh Varma** ([GitHub Profile](https://github.com/kbruhadesh))
- **Sri Varma B**
- **Sriram A**
- **Vivek Reddy**


