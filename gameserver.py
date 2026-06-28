"""2d rooty tooty shooty game
you can bring your friends!
with dynamic scoreboards, bullet trails, and chat!
all working in pygame!
@author Domenic Mancuso
@version 12/15/2025

"""

import socket
import threading
import json
import random as rand

import time
import numpy as np

clock = 0

game_name = "dom's game"

def respawn(clients, username):
    height = len(map)
    width = len(map[0])
    while True:
        x = rand.randint(0, width - 1)
        y = rand.randint(0, height - 1)
        if map[y][x] != "#":
            break
    clients[username]["pos"] = [x,y]
    broadcast(f"200 PLAYER {username},{x},{y}\n")
    
DIRECTIONS = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}
def handle_shot(shooter_us,clients,map,direction,x,y):
    if direction not in DIRECTIONS:
        return
    
    dx, dy = DIRECTIONS[direction]

    height = len(map)
    width = len(map[0])

    cx, cy = x, y
    while True:
        cx += dx
        cy += dy
        
     
        if cx < 0 or cy < 0 or cx >= width or cy >= height:
            break

     
        if map[cy][cx] == '#':
            break
    
        for username, info in clients.items():
            if clients[username]["pos"] == [cx, cy]:
                print(f"{username} HIT")
                clients[shooter_us]["score"] +=1
                broadcast(f"200 LEADERBOARD {shooter_us},{clients[shooter_us]["score"]} ")
                respawn(clients, username)
    
    broadcast(f"200 SHOOT {x},{y},{cx},{cy}\n")
def send_player_positions(clients,conn):
    with lock:
        lines = [f"200 PLAYER {username},{info['pos'][0]},{info['pos'][1]}" for username, info in clients.items()]
        message = "\n".join(lines)
        conn.sendall((message + "\n").encode())

#annoying info pinging function that causes lag
def timeclock():
    global clock
    while True:
        with lock:
            clock += 1  
        time.sleep(1)

def heartbeat(conn,us):
    try:
        data = conn.recv(1024)
        if not data:
            broadcast(f"200 DISCONNECT {us}")
            print(f"{us} disconnected")
            with lock:
                del clients[us] 
    except ConnectionResetError:
        broadcast(f"200 DISCONNECT {us}")
        print(f"{us} disconnected")
        with lock:
            del clients[us]
            


def send_map(map, connec):
    message_lines = []
    for row_index, row in enumerate(map):
        row_str = ''.join(row)
        message_lines.append(f"200 MAP {row_index:03d}, {row_str}")
    message = '\n'.join(message_lines)
    connec.sendall(message.encode("utf-8"))
    return None
map = [ "................................................................................",
        "................................................................................",
        "................................................................................",
        "..................#....#...######..#.......#..#.....#..######..#....#..#######..",
        "..................#....#...#.......#.......#..##...##..#.......#....#.....#.....",
        "..................######...#####...#.......#..#.#.#.#..#####...######.....#.....",
        "..................#....#...#.......#.......#..#..#..#..#.......#....#.....#.....",
        "..................#....#...######..######..#..#.....#..######..#....#.....#.....",
        "................................................................................",
        "................................................................................",
        "................................................................................",
        "................................................................................",
        "................................................................................",
        "................................................................................",
        "..................#....#...######..#.......#..#.....#..######..#....#..#######..",
        "..................#....#...#.......#.......#..##...##..#.......#....#.....#.....",
        "..................######...#####...#.......#..#.#.#.#..#####...######.....#.....",
        "..................#....#...#.......#.......#..#..#..#..#.......#....#.....#.....",
        "..................#....#...######..######..#..#.....#..######..#....#.....#.....",
        "................................................................................",
        "................................................................................",
        "................................................................................"  ]
print(len(map[1]))
print(len(map))
map = [list(row) for row in map]
w = len(map[0])
h = len(map)
HOST = '0.0.0.0'
PORT = 8880
clients = {}
info_msg = f"200 INFO {game_name},{w},{h},{clock},{len(clients)}"
lock = threading.Lock()
def info(conn):
    global info_msg
    

    conn.send(f"{info_msg}\n".encode())
    return None
#DICT: {username: conn, pos, score }


#send to all
def broadcast(message):
    """Send a message to all connected clients."""
    with lock:  # prevent concurrent modification
        for client_info in clients.values():  # iterate over each user's info dict
            try:
                client_socket = client_info["conn"]  # extract socket
                client_socket.sendall(f"{message}\n".encode())
          
            except Exception as e:
                print(f"400 Error sending to client: {e}")
                



def handle_client(conn,addr):
    us = None
    logged_in= False

    buffer = ""
    conn.sendall(f"200 Login with Username\n".encode())
    while not logged_in:
        chunk = conn.recv(1024).decode("utf-8")
        if not chunk:
            conn.close()
            print("not chunk")
            return

        buffer += chunk


        while "\n" in buffer:
            message, buffer = buffer.split("\n", 1)
            message = message.strip()

            if not message:
                print('not message')
                continue

            parts = message.split()
            if parts[0].lower() == "quit":
                conn.close()
                return
      
   
            if parts[0].lower() == "login" and len(parts) > 1:
                username = parts[1]

                if username in clients:
                    conn.sendall("500 Username Taken\n".encode('utf-8'))
                    continue
                # assign spawn
                while True:
                    x = rand.randint(0, w - 1)
                    y = rand.randint(0, h - 1)
                    if map[y][x] != "#":
                        break
                clients[username] = {
                    "conn": conn,
                    "pos": [x, y],
                    "score": 0
                }
                us = username
                conn.sendall("200 Login Successful\n".encode())
                send_player_positions(clients, conn)
                send_map(map, conn)
                conn.sendall("\n300 MAP END\n".encode())
                broadcast(f"200 {us} logged in!\n")
                broadcast(f"200 PLAYER {us},{x},{y}\n")

                logged_in =True
                break       
            else:
                conn.sendall("400 Not logged in\n".encode())
    #LOGGED IN LOOP
    while True:
        chunk = conn.recv(1024).decode("utf-8")
        if not chunk:
            break

        buffer += chunk

        while "\n" in buffer:
            message, buffer = buffer.split("\n", 1)
            message = message.strip()

            if not message:
                continue

            parts = message.split()
            cmd = parts[0].upper()
            match cmd:
                case "PING":
                    conn.sendall("PONG\n".encode())

                case "INFO":
                    info(conn)

                case "LEADERBOARD":
                    broadcast_leaderboard(clients, conn)

                case "MAP":
                    send_map(map, conn)
                    conn.sendall("300 MAP END\n".encode())

                case "MOVE":
                    if len(parts) < 3 and len(parts) > 3:
                        conn.sendall("400 Invalid MOVE request\n".encode())
                        continue

                    try:
                        dx = int(parts[1])
                        dy = int(parts[2])
                    except ValueError:
                        conn.sendall("400 Invalid MOVE request\n".encode())
                        continue

                    with lock:
                        x, y = clients[us]["pos"]
                        nx = x + dx
                        ny = y + dy

                        if not (0 <= nx < w and 0 <= ny < h):
                            # conn.sendall("400 Out of bounds\n".encode())
                            continue

                        if map[ny][nx] == "#":
                            # conn.sendall("400 Can't move onto this tile\n".encode())
                            continue

                        clients[us]["pos"] = [nx, ny]

                    broadcast(f"200 PLAYER {us},{nx},{ny}")
                
                case "MSG":
                    if len(parts) < 2:
                        conn.sendall("400 MSG missing target or message\n".encode())
                        continue

                    target = parts[1]

                    # private message
                    if target in clients:
                        if len(parts) < 3:
                            conn.sendall("400 MSG missing message\n".encode())
                            continue
                        message_text = " ".join(parts[2:])
                        start_msg = f"200 MSG {us} to {target}: "
                        clients[target]["conn"].sendall(f"{start_msg}{message_text}\n".encode())
                        clients[us]["conn"].sendall(f"{start_msg}{message_text}\n".encode())


                    # public message
                    else:
                        message_text = " ".join(parts[1:])
                        broadcast(f"200 MSG {us}: {message_text}")
                case "SHOOT":
                    direction = parts[1]
                    x,y = clients[us]["pos"]
                    print(direction)
                    broadcast(f"200 SHOOT {us},{x},{y},{direction}\n")
                    handle_shot(us,clients,map,direction,x,y)
                case "QUIT":
                    broadcast(f"200 DISCONNECT {us}")

                    conn.close()
                    with lock:
                        del clients[us]
                    return

                case _:
                    conn.sendall(f"400 {cmd} unreachable request\n".encode())

                    
    print(f"200 DISCONNECT {us}")
    broadcast(f"200 DISCONNECT {us}")

    conn.close()
    with lock:
        if us in clients:
            del clients[us]


def broadcast_leaderboard(clients,conn):
    leaderboard_lines = []
    with lock: 
        sorted_players = sorted(
            clients.items(), 
            key=lambda item: item[1].get('score', 0), 
            reverse=True
        )
        for username, info in sorted_players:
            score = info.get('score', 0)
            leaderboard_lines.append(f"200 LEADERBOARD {username},{score}\n")
           
        full_message = "\n".join(leaderboard_lines)
        if full_message:
            conn.sendall(full_message.encode()),
            print(full_message)
        return None    
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Server started on {HOST}:{PORT}")

    threading.Thread(target=timeclock,args=(),daemon=True).start()
    # threading.Thread(target=broadcast_leaderboard,args=(),daemon=True).start()

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
if __name__ == "__main__":
    start_server()



