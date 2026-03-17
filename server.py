import socket       
import struct        
import time          

PORT = 8888            
GOOGLE_DNS = "8.8.8.8" 
DNS_PORT = 53          
BUF_SIZE = 2048        

dns_cache = {}

# CHUYỂN DOMAIN → DNS FORMAT
def format_dns_name(domain):
    qname = b''

    for part in domain.split('.'): # tách domain theo dấu chấm
        qname += bytes([len(part)]) + part.encode()  # thêm độ dài + nội dung


    return qname + b'\x00'  # kết thúc bằng byte 0

# BỎ QUA TRƯỜNG NAME TRONG DNS
# (do DNS có thể dùng pointer nén)
def skip_name(response, offset):
    while True:
        length = response[offset]   # đọc byte đầu

        if length == 0:
            # kết thúc chuỗi domain
            return offset + 1

        elif (length & 0xC0) == 0xC0:
            # nếu là pointer (2 byte)
            return offset + 2

        else:
            # nếu là label thường → nhảy qua
            offset += length + 1

# HÀM RESOLVE DNS
def resolve_dns(domain, qtype=1):
    now = time.time()   # lấy thời gian hiện tại

    # ===== KIỂM TRA CACHE =====
    if domain in dns_cache:
        entry = dns_cache[domain]

        # nếu chưa hết hạn
        if now < entry['expire']:
            ttl = int(entry['expire'] - now)

            # nếu là NXDOMAIN
            if entry['is_nx']:
                return f"Error: NXDOMAIN '{domain}'\nSource: cache\nTTL: {ttl}s\n"

            # trả kết quả từ cache
            return f"{domain} -> {entry['ip']}\nSource: cache\nTTL: {ttl}s\n"

    # ===== TẠO DNS QUERY =====
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # AF_INET: IPv4
        # SOCK_DGRAM: UDP

        sock.settimeout(3.0)  # timeout 3 giây

        # ===== HEADER DNS (12 byte) =====
        header = struct.pack(
            "!HHHHHH",
            1234,   # ID: mã request
            0x0100, # Flags: query chuẩn
            1,      # QDCOUNT: 1 câu hỏi
            0, 0, 0 # AN, NS, AR = 0
        )

        # chuyển domain sang format DNS
        qname = format_dns_name(domain)

        # QTYPE: 1 = A (IPv4), 28 = AAAA (IPv6)
        # QCLASS: 1 = IN (Internet)
        qinfo = struct.pack("!HH", qtype, 1)

        # gộp header + question
        query = header + qname + qinfo

        # gửi tới DNS server
        sock.sendto(query, (GOOGLE_DNS, DNS_PORT))

        # nhận response
        response, _ = sock.recvfrom(BUF_SIZE)

        sock.close()

    except socket.error:
        return "Error: Timeout\n"

    # lấy 12 byte đầu
    _, flags, _, ans_count, _, _ = struct.unpack("!HHHHHH", response[:12])

    # lấy mã lỗi (4 bit cuối)
    rcode = flags & 0x000F

    # ===== XỬ LÝ NXDOMAIN =====
    if rcode == 3:
        # lưu cache lỗi
        dns_cache[domain] = {
            'ip': '',
            'expire': now + 60,
            'is_nx': True
        }

        return f"Error: NXDOMAIN '{domain}'\n"

    # ===== NẾU CÓ ANSWER =====
    if ans_count > 0:

        # bỏ qua phần question
        offset = skip_name(response, 12) + 4

        # duyệt từng answer
        for _ in range(ans_count):

            # bỏ qua tên
            offset = skip_name(response, offset)

            # đọc TYPE, CLASS, TTL, RDLENGTH
            atype, _, ttl, rdlength = struct.unpack(
                "!HHIH", response[offset:offset+10])

            offset += 10

            # ===== A RECORD (IPv4) =====
            if atype == 1 and qtype == 1:
                ip = socket.inet_ntoa(response[offset:offset+4])
                # inet_ntoa: convert bytes → IP string

                # lưu cache
                dns_cache[domain] = {
                    'ip': ip,
                    'expire': now + ttl,
                    'is_nx': False
                }
                return f"{domain} -> {ip}\nSource: fresh\nTTL: {ttl}s\n"
            # ===== AAAA RECORD (IPv6) =====
            elif atype == 28 and qtype == 28:
                ip = socket.inet_ntop(socket.AF_INET6,
                                      response[offset:offset+16])
                # inet_ntop: convert IPv6 bytes → string
                dns_cache[domain] = {
                    'ip': ip,
                    'expire': now + ttl,
                    'is_nx': False
                }
                return f"{domain} -> {ip}\nSource: fresh\nTTL: {ttl}s\n"
            # nếu không phải A/AAAA → bỏ qua
            offset += rdlength
        return "Error: No answer\n"
    return "Error: Empty response\n"

# HIỂN THỊ CACHE
def show_cache():
    now = time.time()
    result = "Cached entries:\n"
    for d, v in dns_cache.items():
        ttl = int(v['expire'] - now)
        if ttl < 0:
            continue
        if v['is_nx']:
            result += f"{d} -> NXDOMAIN | TTL: {ttl}s\n"
        else:
            result += f"{d} -> {v['ip']} | TTL: {ttl}s\n"
    return result


# MAIN SERVER UDP
def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # bind server vào tất cả IP local, port 8888
    server_sock.bind(('0.0.0.0', PORT))

    print(f"DNS Resolver chạy port {PORT}")

    while True:
        # nhận dữ liệu từ client
        data, addr = server_sock.recvfrom(BUF_SIZE)

        # decode message
        msg = data.decode().strip()

        if not msg:
            continue

        # lệnh xem cache
        if msg == "/cache":
            response = show_cache()
        else:
            parts = msg.split()

            # kiểm tra format đúng: resolve domain
            if len(parts) < 2 or parts[0] != "resolve":
                response = "Use: resolve <domain> [AAAA]\n"
            else:
                domain = parts[1]

                # mặc định IPv4
                qtype = 1

                # nếu có AAAA → IPv6
                if len(parts) == 3 and parts[2] == "AAAA":
                    qtype = 28

                # gọi hàm resolve
                response = resolve_dns(domain, qtype)

        # gửi kết quả về client
        server_sock.sendto(response.encode(), addr)


# chạy server
if __name__ == "__main__":
    main()