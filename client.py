"""2d rooty tooty shooty game
you can bring your friends!
with dynamic scoreboards, bullet trails, and chat!
all working in pygame!
@author Domenic Mancuso
@version 12/15/2025

"""
import socket
import threading
import pygame
import time
HOST = '0.0.0.0'
PORT = 8880
tile_map = []
grid = []
players = {}
logged_in = False
has_map = False
chat_messages = []   # list of strings
CHAT_MSG_DURATION = 10  # seconds to show messages
MAX_CHAT_LINES = 12      # maximum lines to display  
leaderboard_data = {}  # list of dicts: {"username": str, "score": int, "time": float}


#parse leaderboard entries to dictionary
def add_leaderboard_entry(username, score):
    global leaderboard_data # Reference the new dictionary
    now = time.time()
 
    # Use the username as the key to update the data cleanly
    leaderboard_data[username] = {
        "score": score, 
       
    }

#show leaderboard in pygame
def draw_leaderboard(screen):
    global leaderboard_data # Reference the new dictionary
    now = time.time()
    x = screen.get_width() - 10
    y = 10
    line_height = 22


    sorted_lb = sorted(
        leaderboard_data.items(), 
        key=lambda item: item[1]["score"], 
        reverse=True
    )

    # 3. Draw the entries (using list index and dictionary access)
    for i, (username, data) in enumerate(sorted_lb):
        # NOTE: data is now the nested dict: {'score': score, 'time': time}
        score = data['score']
        
        # This will now correctly display a score of 0 as well
        text_surface = font.render(f"{username}: {score}", True, (0, 0, 0))
        text_rect = text_surface.get_rect(topright=(x, y + i * line_height))
        screen.blit(text_surface, text_rect)
#show chat in pygame
def draw_chat(screen):
    now = time.time()
    x = 10
    y = 10
    line_height = 22

    # Remove expired messages
    chat_messages[:] = [msg for msg in chat_messages if now - msg["time"] <= CHAT_MSG_DURATION]

    # Only keep the last MAX_CHAT_LINES messages
    for i, msg in enumerate(chat_messages[-MAX_CHAT_LINES:]):
        text = font.render(msg["msg"], True, (0, 0, 0))
        screen.blit(text, (x, y + i * line_height))
# network setup 
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
buffer = ""

# pygame setup
pygame.init()
font = pygame.font.SysFont(None, 28)
TILE_SIZE = 32
ROWS = 22
COLS = 80
WIDTH = COLS * TILE_SIZE
HEIGHT = ROWS * TILE_SIZE
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tile Map")
shots = []  # list of dicts: {start, end, time}
SHOT_LIFETIME = 0.15 
#animate bullets across the screen
def draw_shots(screen):
    now = time.time()
    for shot in shots[:]:
        if now - shot["time"] > SHOT_LIFETIME:
            shots.remove(shot)
            continue

        x1, y1 = shot["start"]
        x2, y2 = shot["end"]

        start_px = (
            x1 * TILE_SIZE + TILE_SIZE // 2,
            y1 * TILE_SIZE + TILE_SIZE // 2
        )
        end_px = (
            x2 * TILE_SIZE + TILE_SIZE // 2,
            y2 * TILE_SIZE + TILE_SIZE // 2
        )

        pygame.draw.line(screen, (255, 255, 0), start_px, end_px, 3)
        #draw map upon logging in
def draw_map(screen, grid):
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if tile == '#':
                pygame.draw.rect(screen, (50, 50, 50), rect)
            else:
                pygame.draw.rect(screen, (200, 200, 200), rect)
        for username, (px, py) in players.items():
            letter = username[0].upper()  # first letter
            text_surface = font.render(letter, True, (255, 0, 0))  # red color
            text_rect = text_surface.get_rect(center=(px * TILE_SIZE + TILE_SIZE // 2, py * TILE_SIZE + TILE_SIZE // 2))
            screen.blit(text_surface, text_rect)
            

# Network thread 
def network_thread():
    global logged_in, has_map, tile_map, grid, buffer 
    flag = False
    while True:
        try:
            chunk = client.recv(1024).decode("utf-8")
            if not chunk:
                print("Server disconnected")
                break
            buffer += chunk

            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                message = message.strip()

                # login
                if not logged_in:
                    # server sends prompt
                    if message == "200 Login with Username":
                        while True:
                            # Block the network thread until valid input is given
                            us = input("Enter username: ").strip()
                            if us:
                                # Send the login command with the username
                                client.sendall(f"LOGIN {us}\n".encode("utf-8"))
                                break
                            print("Username cannot be empty!")
                            
                    # server accepts login
                    elif message == "200 Login Successful":
                        logged_in = True
                        print(f"Logged in successfully as {us}!")
                        # Do not break the loop; continue to process other messages
                        
                    #  Server rejects login (username taken)
                    elif message == "500 Username Taken":
                        print("Username is taken. Please try again.")
                        # Rerun the input prompt sequence
                        while True:
                            us = input("Enter new username: ").strip()
                            if us:
                                client.sendall(f"LOGIN {us}\n".encode("utf-8"))
                                break
                            print("Username cannot be empty!")
                    #server rejects login (other)
                    elif message == "400 Not logged in":
                        print("Login unsuccessful. Please try again.")
                        # Rerun the input prompt sequence
                        while True:
                            us = input("Enter new username: ").strip()
                            if us:
                                client.sendall(f"LOGIN {us}\n".encode("utf-8"))
                                break
                            print("Username cannot be empty!")
                    
                    # Ignore other messages until logged in
                    continue

                # Map parsing 
                elif message.startswith("200 MAP") and not has_map:
                    try:
                        _, row_data = message.split(",", 1)
                        tile_map.append(row_data.strip())
                    except ValueError:
                        continue

                        
                    if len(tile_map) == ROWS:
                        has_map = True
                        grid = [list(row) for row in tile_map]
                        if not flag:
                            print(grid, len(grid))
                            flag =True
                        print("Map received!")
                        #moving player
                elif message.startswith("200 PLAYER"):
                     try:
                        _, data = message.split("200 PLAYER", 1)
                        data = data.strip()
                        username, x, y = data.split(",")
                        players[username.strip()] = (int(x), int(y))
                     except ValueError:
                        pass
                    #disconnect player remove from dictionary
                elif message.startswith("200 DISCONNECT"):
                    try:
                        _, data = message.split("200 DISCONNECT", 1)
                        username = data.strip()
                        del players[username]
                      
                        print(f"{username} disconnected")
                    except ValueError:
                        pass
                    #shoot
                elif message.startswith("200 SHOOT"):
                    try:
                        _, data = message.split("200 SHOOT", 1)
                        x1, y1, x2, y2 = map(int, data.strip().split(","))
                        shots.append({
                            "start": (x1, y1),
                            "end": (x2, y2),
                            "time": time.time()
                        })
                    except ValueError:
                        pass
                    #parse leaderboard
                elif message.startswith("200 LEADERBOARD"):
                    try:
                      
                        _, data = message.split("200 LEADERBOARD", 1)
                        data = data.strip()

                        
                        if not data:
                            raise ValueError("Empty leaderboard data line")

                     
                        name, score = data.split(",")
                        
                
                            
                        add_leaderboard_entry(name, int(score))

                    except ValueError as e:
                        print(f"Leaderboard parsing error: {e}. Message: {message}")
                        pass
                elif message.startswith("200 MSG"):
                    chat_messages.append({"msg": message,
                                            "time": time.time()})
                
                
        except Exception as e:
            print("Network error:", e)
            break

# Start network thread
threading.Thread(target=network_thread, daemon=True).start()

# Main pygame loop 
clock = pygame.time.Clock()
running = True
shoot_mode = False  
chat_mode = False
chat_buffer = ""
while running:
    screen.fill((0, 0, 0))
    if has_map:
        draw_map(screen, grid)
        draw_shots(screen)
    draw_chat(screen)
    draw_leaderboard(screen)
    if chat_mode:
        pygame.draw.rect(screen, (0, 0, 0), (0, HEIGHT - 40, WIDTH, 40))
        text = font.render(chat_buffer, True, (255, 255, 255))
        screen.blit(text, (10, HEIGHT - 30))
    pygame.display.flip()
    clock.tick(60)
    for event in pygame.event.get():
        
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB and not chat_mode and not shoot_mode:
                client.sendall("LEADERBOARD\n".encode('utf-8'))
                continue
            #chat
            if event.key == pygame.K_RETURN:
                if chat_mode:
                    if chat_buffer.strip():
                        client.sendall(f"MSG {chat_buffer}\n".encode("utf-8"))
                    chat_buffer = ""
                    chat_mode = False
                else:
                    chat_mode = True
            elif chat_mode:
                if event.key == pygame.K_BACKSPACE:
                    chat_buffer = chat_buffer[:-1]
                else:
                    chat_buffer += event.unicode
                    pygame.draw.rect(screen, (0, 0, 0), (0, HEIGHT - 40, WIDTH, 40))
                    text = font.render(chat_buffer, True, (255, 255, 255))
                    screen.blit(text, (10, HEIGHT - 30))
                    
#  shoot
            elif event.key == pygame.K_SPACE:
                shoot_mode = True
            elif shoot_mode:
                direction = None
                if event.key == pygame.K_w:
                    direction = 'U'
                elif event.key == pygame.K_s:  
                    direction = 'D'
                elif event.key == pygame.K_a: 
                    direction = 'L'
                elif event.key == pygame.K_d:
                    direction = 'R'
                  
                if direction:
                    client.sendall(f"SHOOT {direction}\n".encode('utf-8'))
                    shoot_mode = False
                    print(f"Shot {direction}")
                    direction = None
                  
            else:
#move
                if event.key == pygame.K_w:  # W key
                    client.sendall("MOVE 0 -1\n".encode('utf-8'))
                    print("Move up")
                elif event.key == pygame.K_s:  # S key
                    client.sendall("MOVE 0 1\n".encode('utf-8'))

                    print("Move down")
                elif event.key == pygame.K_a:  # A key
                    client.sendall("MOVE -1 0\n".encode('utf-8'))

                    print("Move left")
                elif event.key == pygame.K_d:  # D key
                    client.sendall("MOVE 1 0\n".encode('utf-8'))
                    print("Move right")
                
                
                    
                    #easy quit
                elif event.key == pygame.K_ESCAPE:  # Escape key
                    running = False


    
