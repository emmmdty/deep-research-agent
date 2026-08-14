## Executive Summary

- Unlambda is written in a parenthesis-free prefix notation, where the backquote prefix operator is used to apply a function to an argument. [8]
- In Unlambda, `r` prints a line feed instead of a character. [12]
- In Unlambda, `.x`, where x is any letter, behaves like `i` but has the side-effect of printing the letter x when applied. [12]
- The r builtin prints a newline in Unlambda. [20]
- The .x builtin in Unlambda prints the character x. [20]

## Findings

### Finding 1: The Backquote as Apply Operator
The backquote character (ASCII number 96=0x60) represents Unlambda's apply operation. This is a prefix operator: ` F G means F applied to G. If f and x are expressions, then ``fx` is an expression that applies f to the argument x. Unlambda is written in a parenthesis-free prefix notation. [24]

### Finding 2: Language Overview
Unlambda is a minimal, 'nearly pure' functional programming language invented by David Madore. [3] It relies mainly on two built-in functions (s and k) and an apply operator (written as the backquote character). The language contains the primitives ` (binary function application), s, k, i, v, d, c, r (print new line), and 256 single-character printing functions .x.

### Finding 3: Printing Functions
The `.x` notation, where x is any character, takes one argument and returns it, with the side effect of printing x. The print-character builtin '.' is bound at parse-time to the character which it prints. Unlambda contains 256 printing functions, one for each character. [13] The `r` builtin prints a newline (line feed).

### Finding 4: Other Primitives
In Unlambda, `v` returns itself when applied. [12] The `c` primitive is Scheme's call/cc.

### Finding 5: Program Composition (Qualified)
One claim states that an Unlambda program consists of a string made entirely of the characters s, k, and '`'. [15] This is only partially supported: while the evidence describes this simplified composition, Unlambda also includes other primitives like i, v, d, c, r, and .x, so the claim is qualified.

### Finding 6: Backquote Frequency
The backquote is the most common character in Unlambda programs, making up half of any Unlambda program. [1,5,20]

## Evidence Status

- **Accepted claims (critical=True):** Backquote as apply (multiple confirmations), parenthesis-free prefix notation, `r` prints line feed, `.x` prints character x, `.x` returns its argument with side effect, prefix notation meaning, `.x` outputs character x.
- **Accepted claims (critical=False):** Backquote frequency (half of programs), primitive list, language description, reliance on s/k, `v` returns itself, `c` is call/cc, parse-time binding of '.', 256 printing functions, backquote as apply symbol, prefix operator nature.
- **Qualified claims:** 
  - Claim 17 (program consists only of s, k, and backquote) — partially supported; other primitives exist.
  - Claim 24 (r is synonym for .x where x is newline) — plausible but not fully supported by evidence.
- **Unsupported claim:** Claim 29 — the evidence does not contain information about specific code for "For penguins" or the required character to correct given code.

## References

1. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda (document: web_search-0960397730285581)
2. Unlambda in K — https://nsl.com/papers/unlambda.htm (document: web_search-291b366f7e1686ec)
3. Unlambda - Wikipedia — https://en.wikipedia.org/wiki/Unlambda (document: web_search-f66aa2e07de9c48d)
4. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: web_search-2a954f013cef1741)
5. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda (document: web_search-fafce48050ad38ee)
6. Unlambda — https://esolangs.org/wiki/Unlambda (document: web_search-0f145d238598bab9)
7. Unlambda — https://en.wikipedia.org/wiki/Unlambda (document: web_search-75ae1abe38be576c)
8. Unlambda — https://esolangs.org/wiki/Unlambda (document: web_search-9785ec7f6b59dd5b)
9. irori/unlambda: Unlambda interpreter — https://github.com/irori/unlambda (document: web_search-526dd8dfc375cc3f)
10. Undo (esoteric programming language) - chridd — https://chridd.nfshost.com/esolang/undo (document: web_search-8942cf699af5b680)
11. Friday Pathological Programming: Unlambda, or ... — http://www.goodmath.org/blog/2006/08/11/friday-pathological-programming-unlambda-or-programming-without-variables (document: web_search-dcba2be1bd46845b)
12. Implementing Unlambda - Terbium — https://terbium.io/2019/09/unlambda (document: web_search-50f8524944f48526)
13. Unlambda in K — https://nsl.com/papers/unlambda.htm (document: web_search-3004a7197a307993)
14. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda (document: web_search-e9a8a34fa501fc61)
15. Assignment 6: Prolog — https://student.cs.uwaterloo.ca/~cs442/W26/a6.pdf (document: web_search-c747939a9f8d9503)
16. irori/unlambda: Unlambda interpreter — https://github.com/irori/unlambda (document: web_search-faa7795d0adcdf8a)
17. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda/ (document: fetch_page-740c854c7e7a5eb0)
18. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda/ (document: fetch_page-ba2955f3cb99ece3)
19. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda/ (document: fetch_page-f812b44384138a69)
20. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda/ (document: fetch_page-195d5e973d9eadd8)
21. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda/ (document: fetch_page-81f4978bae8aaaf7)
22. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda/ (document: fetch_page-d035a2e1694f8105)
23. The Unlambda Programming Language — http://www.madore.org/~david/programs/unlambda/ (document: fetch_page-4abb3b71ec2756f3)
24. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: fetch_page-2d7bd57cdab67cca)
25. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: fetch_page-3aa95fe5f8aa6630)
26. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: fetch_page-4ac431dda38e5bbd)
27. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: fetch_page-388936c1a891a08a)
28. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: fetch_page-5a3ad9486ecaa095)
29. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: fetch_page-c7dbdcf4021312dc)
30. Unlambda - Esolang — https://esolangs.org/wiki/Unlambda (document: fetch_page-86abb1c750a3ba0e)

## Claim Register

- (accepted, critical=false) The backquote is the most common character in Unlambda programs, making up half of any Unlambda program. [1,5,20]
- (accepted, critical=false) Unlambda contains the primitives ` (binary function application), s, k, i, v, d, c, r (print new line), and 256 single-character printing functions .x. [2]
- (accepted, critical=false) Unlambda is a minimal, 'nearly pure' functional programming language invented by David Madore. [3]
- (accepted, critical=false) Unlambda relies mainly on two built-in functions (s and k) and an apply operator (written as the backquote character). [3]
- (accepted, critical=false) In Unlambda, the backquote prefix operator is used to apply a function to an argument; if f and x are expressions, then ``fx` is an expression that applies f to the argument x. [4]
- (accepted, critical=true) Unlambda is written in a parenthesis-free prefix notation, where the backquote prefix operator is used to apply a function to an argument. [8]
- (accepted, critical=true) In Unlambda, `r` prints a line feed instead of a character. [12]
- (accepted, critical=true) In Unlambda, `.x`, where x is any letter, behaves like `i` but has the side-effect of printing the letter x when applied. [12]
- (accepted, critical=false) In Unlambda, `v` returns itself when applied. [12]
- (accepted, critical=false) In Unlambda, `c` is Scheme's call/cc. [12]
- (accepted, critical=false) The Unlambda print-character builtin '.' is bound at parse-time to the character which it prints. [13]
- (accepted, critical=false) Unlambda contains 256 printing functions, one for each character. [13]
- (qualified, critical=false) The symbol '`' is an 'apply' operator in Unlambda. [15]
- (qualified, critical=false) An Unlambda program consists of a string made entirely of the characters s, k, and '`'. [15]
- (qualified, critical=false) The '`' apply operator is a prefix operator in Unlambda. [15]
- (accepted, critical=true) The r builtin prints a newline in Unlambda. [20]
- (accepted, critical=true) The .x builtin in Unlambda prints the character x. [20]
- (accepted, critical=true) Function application is designated with the backquote character (ASCII number 96=0x60). [22]
- (qualified, critical=true) The r function is a synonym for . x where x is the newline character. [22]
- (accepted, critical=true) . x (where x is any character) takes one argument and returns it, with the side effect of printing x. [24]
- (accepted, critical=true) The backquote notation is prefix, in other words, ` F G means F applied to G. [23]
- (accepted, critical=false) Unlambda is written in a parenthesis-free prefix notation. [24]
- (accepted, critical=true) In Unlambda, the `.x` notation outputs the character x. [25]
