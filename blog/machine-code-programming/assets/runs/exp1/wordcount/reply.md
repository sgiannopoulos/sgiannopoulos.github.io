# Summary

This is a small **Linux x86-64 word-counting program**, similar to running:

```sh
wc -l -w -c
```

It reads standard input until end-of-file or a read error, then writes:

```text
<lines> <words> <bytes>
```

followed by a newline. The values are decimal numbers separated by exactly one space, without column padding.

It does not interpret command-line arguments or open named files.

## 1. Executable format

The ELF header identifies the file as:

- **64-bit, little-endian ELF**
- **x86-64**
- A fixed-address executable, rather than a position-independent executable
- Entry point: **`0x401100`**

There is no dynamic-linker interpreter or dynamic-library machinery. The program uses Linux system calls directly.

The important memory regions are:

| Address | Purpose |
|---|---|
| `0x401000`–`0x401321` | Executable code |
| `0x402000` | Input-buffer position |
| `0x402008` | Number of available input bytes |
| `0x402020` | 4,096-byte input buffer |
| `0x403020` | Buffered-output length |
| `0x403040` | 4,096-byte output buffer |

The writable storage is zero-initialized by the ELF loader. The stack is marked non-executable.

A compiler-identification string says `GCC: (Debian 12.2.0-14) 12.2.0`, though that metadata is not involved in execution.

## 2. Startup and overall control flow

Execution begins at `0x401100`. The startup code aligns the stack and calls a wrapper at `0x4012b0`.

That wrapper:

1. Calls the counting routine at `0x401000`.
2. Flushes buffered output to standard output.
3. Terminates using Linux’s `exit_group` system call.

The counting routine returns zero, so normal termination has **exit status 0**.

The relevant system calls are:

| Number | Linux x86-64 operation | Use |
|---:|---|---|
| 0 | `read` | Read standard input, descriptor 0 |
| 1 | `write` | Write standard output, descriptor 1 |
| 231 | `exit_group` | Terminate the process |

## 3. Reading and counting input

The program requests input in blocks of up to **4,096 bytes**. It processes every returned byte before reading another block.

It maintains three 64-bit counters:

- **Bytes:** incremented for every input byte.
- **Lines:** incremented for each line-feed byte, `0x0A`.
- **Words:** incremented when a non-whitespace byte begins a new word.

It also maintains a Boolean “inside a word” state. This state survives buffer refills, so a word spanning two input blocks is counted only once.

### Line counting

Only the byte:

```text
0A    LF / '\n'
```

increments the line counter.

Consequently:

- An unterminated final line does **not** add another line.
- A carriage return alone does not count as a line.
- A CRLF sequence counts as one line because it contains one LF.

### Word counting

The program treats exactly these six ASCII bytes as whitespace:

| Hex | Character |
|---:|---|
| `09` | Horizontal tab |
| `0A` | Line feed |
| `0B` | Vertical tab |
| `0C` | Form feed |
| `0D` | Carriage return |
| `20` | Space |

A word is a maximal consecutive sequence of bytes outside that set.

The instructions implement this by handling LF separately, testing the range `0x09` through `0x0D`, and then testing space.

For whitespace, the program clears its “inside a word” state. For any other byte, it increments the word counter only if that state was previously clear, then sets the state.

This is **byte-based ASCII classification**, not locale-aware or Unicode-aware classification. In particular:

- NUL bytes count as non-whitespace.
- Bytes with the high bit set count as non-whitespace.
- A multibyte UTF-8 character contributes multiple bytes.
- A Unicode whitespace character is not recognized merely because it is whitespace in Unicode.

### Equivalent counting logic

Ignoring low-level buffering details, the behavior is:

```c
lines = 0;
words = 0;
bytes = 0;
inside_word = false;

while ((n = read(0, buffer, 4096)) > 0) {
    for (i = 0; i < n; ++i) {
        c = buffer[i];
        ++bytes;

        if (c == '\n') {
            ++lines;
            inside_word = false;
        } else if ((c >= 9 && c <= 13) || c == ' ') {
            inside_word = false;
        } else if (!inside_word) {
            ++words;
            inside_word = true;
        }
    }
}

print_decimal(lines);
print_char(' ');
print_decimal(words);
print_char(' ');
print_decimal(bytes);
print_char('\n');
```

## 4. Output formatting

The output order is:

1. Line count
2. Word count
3. Byte count

There are no labels, filenames, leading spaces, or field-width padding.

For example, the exact input bytes:

```text
hello world\nabc
```

produce:

```text
1 3 15
```

with a newline after `15`.

Empty input produces:

```text
0 0 0
```

again followed by a newline.

The program normally prints nothing until input ends or reading fails. On an interactive terminal, it therefore waits for input and eventual EOF without displaying a prompt.

### Number conversion

The decimal-conversion routine begins at `0x401190`. It repeatedly divides by ten using multiplication by the reciprocal constant:

```text
0xCCCCCCCCCCCCCCCD
```

and a shift. It collects digits in reverse order on the stack, then copies them to the output buffer in display order.

The formatter supports negative signed 64-bit values. The counting instructions themselves wrap modulo \(2^{64}\); if a counter reached the signed-negative range, it would therefore print as a negative number. There is no overflow check.

## 5. Error handling

Error handling is minimal.

### Input errors

After `read`, a result of zero or any negative result ends counting.

Thus, a read error is handled like EOF:

- Counts accumulated so far are printed.
- No error diagnostic is produced.
- The program still normally exits with status 0.

It does not retry interrupted reads.

### Output errors

The output-flushing code handles successful partial writes by continuing with the remaining bytes.

However, if a write returns zero or a negative value, it stops trying and discards the remaining buffered output. It does not report the error or change the normal exit status.

Ordinary operating-system signal behavior still applies—for example, writing to a closed pipe may terminate the process with `SIGPIPE`.

## 6. Other routines and side effects

Two additional small routines resemble `memset` and `memcpy`, at `0x401290` and `0x4012a0`. They are not called along the normal counting path.

The executable contains no code to:

- Open or modify named files
- Make network connections
- Launch another program
- Interpret commands
- Inspect command-line arguments or environment variables

Its external activity is limited to reading descriptor 0, writing descriptor 1, and exiting.

**In short:** it is a compact, self-contained standard-input line/word/byte counter, with fixed ASCII whitespace rules and intentionally minimal error reporting.