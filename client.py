import socket
import struct
from colorama import init

init()

class Color:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"

SERVER_IP = "127.0.0.1"
SERVER_PORT = 8888
BUFFER = 4096
TIMEOUT = 5

def send_to_resolver(sock, message):
    try:
        msg_bytes = message.encode()
        packet = struct.pack("!H", len(msg_bytes)) + msg_bytes
        sock.sendto(packet, (SERVER_IP, SERVER_PORT))

        data, _ = sock.recvfrom(BUFFER)
        
        if len(data) >= 2:
            resp_len = struct.unpack("!H", data[:2])[0]
            resp_msg = data[2:2 + resp_len].decode()

            print(Color.BLUE + "\n--- Resolver Reply ---" + Color.RESET)
            if "Error" in resp_msg:
                print(Color.RED + resp_msg + Color.RESET)
            else:
                print(Color.GREEN + resp_msg + Color.RESET)
            print(Color.BLUE + "----------------------\n" + Color.RESET)
        else:
            print(Color.RED + "Error: Invalid response format from server." + Color.RESET)

    except socket.timeout:
        print(Color.RED + "Error: Request timed out." + Color.RESET)
    except Exception as e:
        print(Color.RED + f"Error: {e}" + Color.RESET)

def main():
    print(Color.CYAN + "="*55)
    print("        Simple DNS Client (UDP with Framing)")
    print("Commands:")
    print("  <domain>         (vd: google.com)")
    print("  <domain> AAAA    (vd: google.com AAAA)")
    print("  /cache           (dump server cache)")
    print("  exit")
    print("="*55 + Color.RESET + "\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    try:
        while True:
            try:
                user_input = input(Color.YELLOW + ">>> " + Color.RESET).strip()

                if user_input.lower() == "exit":
                    break
                elif user_input:
                    send_to_resolver(sock, user_input)

            except KeyboardInterrupt:
                print(Color.MAGENTA + "\nInterrupt received (Ctrl+C). Exiting..." + Color.RESET)
                break

    finally:
        sock.close()
        print(Color.MAGENTA + "\nSocket closed. Goodbye :>>" + Color.RESET)

if __name__ == "__main__":
    main()
