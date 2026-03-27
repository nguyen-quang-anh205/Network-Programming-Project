# DNS Resolver & Cache Server (UDP, From Scratch)

## 1. Language and Operating System

* **Programming Language:** Python 3
* **Standard Libraries Used:** `socket`, `struct`, `time`, `colorama` (for terminal output formatting)
* **Operating System Tested:** Debian 
* **Network Protocol:** UDP over IPv4 (Localhost `127.0.0.1`)

---

## 2. Introduction

This project implements a fully functional DNS Resolver Server using low-level UDP socket programming in Python. The resolver is built entirely from scratch without relying on external, high-level DNS libraries (such as dnspython or system gethostbyname calls). It serves to demonstrate a deep understanding of how the Domain Name System (DNS) operates at the binary packet level according to RFC 1035.

The system is capable of constructing raw DNS queries manually, communicating with a public DNS server (Google Public DNS at 8.8.8.8), parsing binary responses (including pointer compression), and caching results based on Time-To-Live (TTL) mechanisms.

---

## 3. Key Features

* **Manual DNS Packet Construction:** Assembles 12-byte headers and variable-length question sections bit-by-bit.
* **Custom UDP Framing Protocol:** Ensures reliable message length validation between the local client and the resolver server.
* **DNS Query Forwarding:** Resolves cache misses by querying 8.8.8.8:53.
* **Full DNS Response Parsing:** Navigates raw bytes and handles DNS message compression (0xC0 pointers) to extract IP addresses.
* **Record Support:** Resolves both A (IPv4) and AAAA (IPv6) records.
* **TTL-Based Caching:** Stores successful resolutions in memory and serves repeated queries instantly until the TTL expires.
* **Negative Caching:** Detects NXDOMAIN (non-existent domain) errors, caching the failure for 60 seconds to optimize network overhead.
* **Cache Inspection:** Provides a /cache command to dump the current memory state.

---

## 4. System Architecture

**Client ↔ Resolver Server ↔ External DNS Server (8.8.8.8)**

### Workflow
1. Client sends a length-prefixed domain query to the resolver via UDP.
2. Resolver intercepts the request and checks the internal dictionary cache.
3. **If cache hit:** Resolver instantly returns the cached IP and remaining TTL.
4. **If cache miss:** Resolver constructs a raw DNS packet and forwards it to 8.8.8.8.
5. Resolver receives the response, unpacks the binary payload, and extracts the Answer section.
6. Resolver stores the new IP and TTL in its local memory cache.
7. Resolver sends the formatted result back to the client.

---

## 5. Project Structure

    Network-Programming-Project/
    ├── resolver_server.py        # Main DNS Resolver & Cache Server script
    ├── client.py        # Interactive DNS Client script
    └── README.md        # Project Documentation

---

## 6. DNS Protocol Implementation Details

### 6.1 DNS Header Construction
Each outgoing DNS query includes a strictly formatted 12-byte header constructed using Python's struct.pack:
* **ID:** Fixed Transaction ID (1234).
* **Flags:** Standard recursive query (0x0100).
* **QDCOUNT:** Number of questions (1).
* **ANCOUNT, NSCOUNT, ARCOUNT:** Set to 0 for outgoing queries.

### 6.2 Domain Name Encoding
Domain names are parsed into a sequence of length-prefixed labels.
* Example: usth.edu.vn becomes \x04 usth \x04 edu \x02 vn \x00.

### 6.3 Name Compression Handling
The resolver features a skip_name algorithm to parse incoming responses from 8.8.8.8. It detects prefix 0xC0 (indicating a compressed pointer) to bypass the mirrored Question section and directly read the Answer section (Type, Class, TTL, and IP Data).

---

## 7. Caching and Negative Caching

### Cache Structure
The server utilizes an in-memory dictionary dns_cache mapping (domain, record_type) to a state object: {ip, expire_timestamp, is_nx}.

### Behavior
* **Standard Caching:** Valid IP addresses are stored based on the TTL provided by 8.8.8.8.
* **Negative Caching:** If the DNS response flag indicates an RCODE of 3 (NXDOMAIN), the server stores this failure state for 60 seconds. This actively prevents redundant upstream queries for known dead domains.
* **Eviction:** Expired entries are dynamically ignored and overwritten upon the next request.

---

## 8. Cybersecurity Considerations

As an implementation designed for academic study, the current architecture contains specific security trade-offs that must be acknowledged from a cybersecurity perspective:

1. **DNS Cache Poisoning Vulnerability:** The resolver uses a static Transaction ID (1234) for all upstream queries to 8.8.8.8. In a production environment, an off-path attacker could easily predict this ID and spoof a response packet, injecting a malicious IP address into our cache. Mitigation requires cryptographic randomization of the Transaction ID and source port.
2. **UDP Source IP Spoofing:** Because the client-server communication relies on connectionless UDP, the server is susceptible to IP spoofing. While basic 2-byte framing is implemented to prevent malformed buffer crashes, it lacks authentication.
3. **Information Disclosure:** The /cache command allows any connected client to dump the entire memory of the resolver. This exposes the domain lookup history of all users on the network, representing a privacy leak. Access to this command should be authenticated.
4. **Denial of Service (DoS):** The server uses a blocking recvfrom mechanism without rate-limiting. A flood of queries could exhaust the server's processing capabilities. However, the implemented Negative Caching helps mitigate upstream DoS (Random Subdomain Attacks) by dropping repeated invalid queries locally.

---

## 9. Communication Protocol (Client ↔ Server)

### Client Request Format
[2-byte Length Prefix] <domain> [TYPE]

Examples:
* google.com (Defaults to A record)
* google.com AAAA (Requests IPv6 record)
* /cache (Administrative command)

### Server Response Format
**Success:**

    Result: <domain> -> <IP>
    Source: Cache hit / DNS query (fresh)
    TTL: <remaining_seconds>s

**Error:**

    Error: NXDOMAIN - '<domain>' does not exist.

---

## 10. How to Run & Demonstration

### Step 1: Start the Server
Run the resolver server in a terminal. It will bind to port 8888.

    python3 server.py

### Step 2: Start the Client
Open a second terminal instance and run the client:

    python3 client.py

### Step 3: Interactive Testing
Inside the client prompt, test the following sequence to observe caching behavior:

1. **Cache Miss (Fresh Query):**

    >>> usth.edu.vn
    Result: usth.edu.vn -> 104.21.83.99
    Source: DNS query (fresh)
    TTL: 300s

2. **Cache Hit (Repeated Query):**

    >>> usth.edu.vn
    Result: usth.edu.vn -> 104.21.83.99
    Source: Cache hit
    TTL: 285s remaining

3. **Negative Caching (Invalid Domain):**

    >>> notexist.xyz
    Error: NXDOMAIN - 'notexist.xyz' does not exist.

4. **Cache Dump:**

    >>> /cache
    --- CURRENT DNS CACHE ---
    usth.edu.vn [A] -> 104.21.83.99 | TTL: 270s
    notexist.xyz [A] -> NXDOMAIN | TTL: 45s
