The file has an ELF64 header and one executable load segment, with entry at `0x400078`. It uses a 4096-byte stack buffer, preserves counting state across reads, formats decimal output backward, and handles partial writes using only the specified syscalls.

```hex
7f 45 4c 46 02 01 01 00
00 00 00 00 00 00 00 00
02 00 3e 00 01 00 00 00
78 00 40 00 00 00 00 00
40 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 40 00 38 00
01 00 00 00 00 00 00 00

01 00 00 00 05 00 00 00
00 00 00 00 00 00 00 00
00 00 40 00 00 00 00 00
00 00 40 00 00 00 00 00
87 01 00 00 00 00 00 00
87 01 00 00 00 00 00 00
00 10 00 00 00 00 00 00

48 81 ec 00 10 00 00
45 31 e4
45 31 ed
45 31 f6
45 31 ff
31 db
31 ed

31 c0
31 ff
48 89 e6
ba 00 10 00 00
0f 05
48 83 f8 fc
74 ec
48 85 c0
7e 49
49 01 c6
49 89 e0
4c 8d 0c 04

41 0f b6 00
49 ff c0
3c 0a
75 0e
49 ff c4
4c 39 fb
4c 0f 47 fb
31 db
eb 1d
48 ff c3
3c 20
74 16
83 e8 09
83 f8 04
76 0e
85 ed
75 0c
49 ff c5
bd 01 00 00 00
eb 02
31 ed
4d 39 c8
72 c3
eb 9e

4c 39 fb
4c 0f 47 fb
48 8d bc 24 00 10 00 00
c6 47 ff 0a
48 ff cf
4c 89 f8
e8 60 00 00 00
48 ff cf
c6 07 20
4c 89 f0
e8 52 00 00 00
48 ff cf
c6 07 20
4c 89 e8
e8 44 00 00 00
48 ff cf
c6 07 20
4c 89 e0
e8 36 00 00 00
48 89 fe
48 8d 94 24 00 10 00 00
48 29 f2

b8 01 00 00 00
bf 01 00 00 00
0f 05
48 83 f8 fc
74 ee
48 85 c0
7e 08
48 01 c6
48 29 c2
75 e1

b8 e7 00 00 00
31 ff
0f 05

b9 0a 00 00 00
31 d2
48 f7 f1
80 c2 30
48 ff cf
88 17
48 85 c0
75 ee
c3
```