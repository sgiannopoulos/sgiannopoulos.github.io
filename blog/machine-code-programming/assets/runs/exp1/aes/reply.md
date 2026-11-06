# Summary

This is a small, self-contained **Linux x86-64 AES encryption utility**. It reads commands from standard input, encrypts hexadecimal data using **AES-128 or AES-256 in ECB mode**, and writes lowercase hexadecimal ciphertext to standard output.

It supports encryption only—not decryption—and performs no padding, authentication, file access, networking, or random-number generation.

## 1. Executable format

The file is a 64-bit, little-endian ELF executable:

- **Architecture:** AMD64/x86-64
- **Executable type:** Fixed-address `ET_EXEC`, not PIE
- **Entry point:** `0x4015a0`
- **File size:** `0x23c0` bytes, or 9,152 bytes
- **Dynamic dependencies:** None; it uses Linux system calls directly
- **Compiler identification string:** `GCC: (Debian 12.2.0-14) 12.2.0`

The executable contains code, read-only constants, and zero-initialized working buffers. The numerous zero bytes in the dump are principally alignment padding, not additional functionality.

The entry point invokes a small runtime wrapper, which calls the main routine at `0x401000`. On completion, the wrapper flushes pending output and calls Linux `exit_group`.

Command-line arguments and environment variables are not used.

## 2. Input interface

The expected command format is:

```text
enc 128 KEY_HEX DATA_HEX
```

or:

```text
enc 256 KEY_HEX DATA_HEX
```

Each command occupies one line.

For example, this standard AES-128 test case:

```text
enc 128 000102030405060708090a0b0c0d0e0f 00112233445566778899aabbccddeeff
```

produces:

```text
69c4e0d86a7b0430d8cdb78070b4c55a
```

### Parsing rules

- The command must be exactly lowercase `enc`.
- The key-size argument must be exactly `128` or `256`.
- There must be exactly four tokens.
- Tokens are separated by spaces or tabs.
- Leading, trailing, and repeated spaces or tabs are accepted.
- Empty lines and whitespace-only lines are ignored.
- A trailing carriage return is removed, allowing ordinary CRLF line endings.
- An unterminated final line is processed when EOF is reached.
- Multiple commands can be supplied in one input stream.
- There is no prompt, greeting, or special quit command.

Quotes, comments, escape sequences, and other shell-like syntax are not implemented.

### Hexadecimal decoding

Both uppercase and lowercase hexadecimal digits are accepted:

```text
0123456789abcdefABCDEF
```

Hexadecimal strings must contain complete byte pairs. Odd-length strings, invalid characters, and excessive decoded lengths are rejected.

There is no support for `0x` prefixes, colons, or separators within a hexadecimal token.

## 3. Key and data requirements

### Keys

| Size argument | Required key length | Hexadecimal characters |
|---|---:|---:|
| `128` | 16 bytes | 32 |
| `256` | 32 bytes | 64 |

AES-192 is not supported.

The key comes directly from the command. There is no password derivation, hashing, salt, or embedded secret key.

### Data

The decoded data must:

- Be nonempty.
- Have a length divisible by 16 bytes.
- Be at most 1,024 bytes long.

Thus, each command encrypts between **1 and 64 AES blocks**.

The corresponding data token can contain at most 2,048 hexadecimal characters.

There is **no padding**. An incomplete final block produces an error rather than being padded.

## 4. Encryption algorithm

The binary implements standard AES in software.

Strong identifying evidence includes:

- The standard 256-byte AES S-box at virtual address `0x4020a0`, beginning:

  ```text
  63 7c 77 7b f2 6b 6f c5 ...
  ```

- The standard AES round constants near `0x402078`:

  ```text
  00 01 02 04 08 10 20 40 80 1b 36
  ```

- The AES key-expansion operations.
- SubBytes, ShiftRows, MixColumns, and AddRoundKey transformations.
- Omission of MixColumns from the final round.

This is not merely a program containing an AES table: the executable code uses those tables to carry out the complete AES encryption procedure.

### Key expansion

For AES-128, it expands the 16-byte key into:

- 44 words
- 11 round keys
- 10 encryption rounds

For AES-256, it expands the 32-byte key into:

- 60 words
- 15 round keys
- 14 encryption rounds

The expansion implements the usual RotWord/SubWord/Rcon operation at each key-length boundary. AES-256 also performs its additional SubWord operation halfway through each eight-word group.

### Block encryption

Each 16-byte data block undergoes:

1. Initial AddRoundKey.
2. Nine full rounds for AES-128, or thirteen for AES-256:
   - SubBytes
   - ShiftRows
   - MixColumns
   - AddRoundKey
3. A final round:
   - SubBytes
   - ShiftRows
   - AddRoundKey

The ShiftRows helper is at `0x4015b0`. MixColumns is implemented using byte operations and reduction by the AES polynomial, with the characteristic `0x1b` reduction constant.

The implementation uses ordinary instructions and S-box lookups, not AES-NI instructions. SSE instructions are used for some 16-byte copies and XOR operations.

### Mode of operation: ECB

Each block is encrypted independently with the same expanded key:

```text
C[i] = AES_encrypt(K, P[i])
```

There is:

- No initialization vector
- No nonce
- No block chaining
- No counter
- No authentication tag

Consequently, identical plaintext blocks under the same key produce identical ciphertext blocks, including when they occur within one command.

## 5. Output

A successful command produces one line containing the ciphertext as lowercase hexadecimal:

```text
CIPHERTEXT_HEX\n
```

There is no label, prefix, or spacing.

For `n` decoded input bytes, the output contains exactly:

```text
2*n hexadecimal characters + one newline
```

For example, the AES-256 test case:

```text
enc 256 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f 00112233445566778899aabbccddeeff
```

corresponds to:

```text
8ea2b7ca516745bfeafc49904b496089
```

Both successful results and error messages go to **standard output**, not standard error.

## 6. Error handling

The read-only strings and their call sites establish these messages:

| Condition | Output |
|---|---|
| First token is not `enc` | `ERR: unknown command` |
| `enc` has the wrong number of tokens | `ERR: bad arguments` |
| Size argument is neither `128` nor `256` | `ERR: bad key size` |
| Invalid key hex or wrong decoded key length | `ERR: bad key` |
| Invalid data hex, excessive length, empty decoded data, or non-block-aligned length | `ERR: bad data` |

Each message ends with a newline.

Validation happens in the order shown: command, argument count, key-size selection, key, then data. Therefore, an unknown command is reported as such even if its argument count is also wrong.

After an invalid command, the program continues reading later lines. Ordinary command errors do not cause a nonzero process exit status; the main routine eventually returns zero.

## 7. Buffering and edge cases

### Input buffering

The program reads standard input in chunks of up to 4,096 bytes.

A separate line buffer retains at most **4,095 bytes**, leaving room for a terminating NUL byte. If a physical line is longer, excess bytes are consumed and discarded until the newline. There is no explicit “line too long” error; the retained prefix is parsed.

Valid maximum-sized commands fit within this limit.

The tokenizer works with NUL-terminated strings. An embedded NUL in a physical input line ends the portion visible to token parsing, although input collection still consumes through the newline.

### Output buffering

Output is accumulated in a 4,096-byte buffer. The buffer is written when needed for more output and again during normal shutdown.

There is no flush after every result line. An interactive caller therefore should not assume that each response becomes visible immediately.

The write loops handle positive partial writes by continuing with the remaining bytes. They stop on a nonpositive result rather than providing robust error recovery.

Read failures are not reported separately; the line-reading code handles a nonpositive read result similarly to EOF.

## 8. Reconstructed high-level behavior

The following summarizes the main logic rather than reproducing its exact source:

```text
while another input line is available:
    retain at most 4095 bytes
    remove one trailing carriage return
    split into space/tab-separated tokens

    if no tokens:
        continue

    if first token != "enc":
        print "ERR: unknown command"
        continue

    if token count != 4:
        print "ERR: bad arguments"
        continue

    if size == "128":
        required_key_bytes = 16
    else if size == "256":
        required_key_bytes = 32
    else:
        print "ERR: bad key size"
        continue

    decode key hex
    if decoding failed or key length is wrong:
        print "ERR: bad key"
        continue

    decode data hex, allowing at most 1024 bytes
    if decoding failed, length is zero,
       or length is not divisible by 16:
        print "ERR: bad data"
        continue

    expand AES key

    for each 16-byte data block:
        encrypt block independently

    print ciphertext as lowercase hex
    print newline

flush output
exit with status 0
```

## 9. Scope and security implications

The program’s functionality is limited to this standard-input/standard-output encryption interface. Its system calls are for reading, writing, and process termination. It does not open files, contact remote hosts, execute other programs, or generate keys.

It should not be mistaken for a complete secure-storage or secure-messaging system:

- ECB reveals repeated-block patterns.
- Ciphertexts have no authentication or integrity protection.
- There is no padding or message framing beyond the textual interface.
- Table-indexed AES operations are not constant-time.
- Key material and working data are not explicitly erased.

**In short:** this executable is a compact, line-oriented AES-128/AES-256 ECB encryption tool operating on hexadecimal keys and data.