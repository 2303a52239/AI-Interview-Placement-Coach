"""Builds app/data/problem_pack.json: classic algorithm problems for the coding arena.

Every problem is written in our own words (they are NOT copies of any website's statements) and reads stdin / writes
stdout, like the rest of the arena. Expected outputs are not typed by hand: each problem carries a reference solution
and the builder RUNS it on every test input, so the stored expected output is exactly what a correct program prints.

    python -m scripts.build_problem_pack          # rewrites app/data/problem_pack.json
"""
import json
import os
import random
import subprocess
import sys
import tempfile

rnd = random.Random(2026)  # fixed seed: test data is reproducible
PROBLEMS = []


def P(title, difficulty, topic, statement, infmt, outfmt, constraints, ref, inputs):
    PROBLEMS.append(dict(title=title, difficulty=difficulty, topic_tag=topic, problem_statement=statement,
                         input_format=infmt, output_format=outfmt, constraints=constraints, ref=ref, inputs=inputs))


def arr(a):
    return f"{len(a)}\n{' '.join(map(str, a))}"


def ra(n, lo, hi):
    return [rnd.randint(lo, hi) for _ in range(n)]


# ---------------------------------------------------------------- arrays & hashing
P("Two Sum Indices", "easy", "arrays",
  "Given n integers and a target, find two different positions i < j whose values add up to the target. Print i and j (0-based) separated by a space. If several pairs exist print the one with the smallest j, then the smallest i. A pair is guaranteed to exist.",
  "Line 1: n. Line 2: n integers. Line 3: target.", "Two integers i j.", "2 <= n <= 10^4",
  "n=int(input());a=list(map(int,input().split()));t=int(input())\nseen={}\nfor j,x in enumerate(a):\n    if t-x in seen:\n        print(seen[t-x],j);break\n    seen.setdefault(x,j)\n",
  ["4\n2 7 11 15\n9", "3\n3 2 4\n6", "2\n3 3\n6", "5\n-1 -2 -3 -4 -5\n-8", "6\n1 5 3 7 9 2\n12", "5\n0 4 3 0 8\n0"])
P("Contains Duplicate", "easy", "arrays", "Print YES if any value occurs at least twice in the array, otherwise NO.",
  "Line 1: n. Line 2: n integers.", "YES or NO", "1 <= n <= 10^5",
  "n=int(input());a=input().split()\nprint('YES' if len(set(a))<n else 'NO')\n",
  [arr([1, 2, 3, 1]), arr([1, 2, 3, 4]), arr([5]), arr([1, 1, 1, 3, 3, 4, 3, 2, 4, 2]), arr(list(range(1000)))])
P("Valid Anagram", "easy", "strings", "Two lowercase words are anagrams if one can be rearranged into the other. Print YES or NO.",
  "Two lines, one word each.", "YES or NO", "1 <= length <= 10^5",
  "a=input().strip();b=input().strip()\nprint('YES' if sorted(a)==sorted(b) else 'NO')\n",
  ["anagram\nnagaram", "rat\ncar", "a\na", "listen\nsilent", "abc\nabcc"])
P("Best Time to Trade", "easy", "arrays", "Given the price of a stock on each day, you may buy on one day and sell on a later day. Print the maximum profit, or 0 if no profit is possible.",
  "Line 1: n. Line 2: n prices.", "One integer.", "1 <= n <= 10^5",
  "n=int(input());p=list(map(int,input().split()))\nbest=0;lo=p[0]\nfor x in p:\n    lo=min(lo,x);best=max(best,x-lo)\nprint(best)\n",
  [arr([7, 1, 5, 3, 6, 4]), arr([7, 6, 4, 3, 1]), arr([5]), arr([2, 4, 1]), arr(ra(50, 1, 100))])
P("Missing Number", "easy", "arrays", "An array holds n distinct numbers taken from 0..n. Exactly one number of that range is missing. Print it.",
  "Line 1: n. Line 2: n integers.", "One integer.", "1 <= n <= 10^5",
  "n=int(input());a=list(map(int,input().split()))\nprint(n*(n+1)//2-sum(a))\n",
  [arr([3, 0, 1]), arr([0, 1]), arr([9, 6, 4, 2, 3, 5, 7, 0, 1]), arr([0]), arr([1])])
P("Single Number", "easy", "arrays", "Every value appears exactly twice except one that appears once. Print that value.",
  "Line 1: n (odd). Line 2: n integers.", "One integer.", "1 <= n <= 10^5",
  "n=int(input());x=0\nfor v in map(int,input().split()):\n    x^=v\nprint(x)\n",
  [arr([2, 2, 1]), arr([4, 1, 2, 1, 2]), arr([1]), arr([-3, 5, -3]), arr([9, 8, 9, 7, 8])])
P("Move Zeroes", "easy", "arrays", "Move all zeroes to the end of the array while keeping the order of the other values. Print the resulting array.",
  "Line 1: n. Line 2: n integers.", "n integers separated by spaces.", "1 <= n <= 10^5",
  "n=int(input());a=list(map(int,input().split()))\nr=[x for x in a if x!=0]\nprint(*(r+[0]*(n-len(r))))\n",
  [arr([0, 1, 0, 3, 12]), arr([0]), arr([1, 2, 3]), arr([0, 0, 1]), arr([4, 0, 0, 5, 0, 6])])
P("Merge Two Sorted Arrays", "easy", "arrays", "Merge two sorted (ascending) arrays into one sorted array and print it.",
  "Line 1: n, line 2: n integers. Line 3: m, line 4: m integers (an empty array is an empty line).", "n+m integers.", "0 <= n, m <= 10^5",
  "n=int(input());a=list(map(int,input().split()))\nm=int(input());b=list(map(int,input().split()))\nprint(*sorted(a+b))\n",
  ["3\n1 2 4\n3\n1 3 4", "1\n1\n0\n", "0\n\n1\n5", "2\n-5 0\n2\n-3 9", "4\n1 1 1 1\n2\n1 1"])
P("Majority Element", "easy", "arrays", "One value appears more than n/2 times. Print it.",
  "Line 1: n. Line 2: n integers.", "One integer.", "1 <= n <= 10^5",
  "from collections import Counter\nn=int(input());a=input().split()\nprint(Counter(a).most_common(1)[0][0])\n",
  [arr([3, 2, 3]), arr([2, 2, 1, 1, 1, 2, 2]), arr([7]), arr([5, 5, 5, 1, 2]), arr([1] * 30 + ra(20, 2, 9))])
P("Rotate Array", "medium", "arrays", "Rotate the array to the right by k positions and print the result.",
  "Line 1: n. Line 2: n integers. Line 3: k.", "n integers.", "1 <= n <= 10^5, 0 <= k <= 10^9",
  "n=int(input());a=list(map(int,input().split()));k=int(input())%n\nprint(*(a[-k:]+a[:-k] if k else a))\n",
  ["7\n1 2 3 4 5 6 7\n3", "4\n-1 -100 3 99\n2", "1\n5\n10", "5\n1 2 3 4 5\n0", "5\n1 2 3 4 5\n5", "6\n9 8 7 6 5 4\n1000000001"])
P("Product of Array Except Self", "medium", "arrays", "For each position print the product of all other values. Use the fact that the answer fits in 64 bits; do not use division.",
  "Line 1: n. Line 2: n integers.", "n integers.", "2 <= n <= 10^5, |value| <= 10",
  "n=int(input());a=list(map(int,input().split()))\nL=[1]*n;R=[1]*n\nfor i in range(1,n):L[i]=L[i-1]*a[i-1]\nfor i in range(n-2,-1,-1):R[i]=R[i+1]*a[i+1]\nprint(*(L[i]*R[i] for i in range(n)))\n",
  [arr([1, 2, 3, 4]), arr([-1, 1, 0, -3, 3]), arr([2, 3]), arr([0, 0, 5]), arr(ra(12, -5, 5))])
P("Container With Most Water", "medium", "two_pointers", "Each number is the height of a vertical line at positions 0..n-1. Choose two lines; the water held is the smaller height times the distance between them. Print the maximum.",
  "Line 1: n. Line 2: n heights.", "One integer.", "2 <= n <= 10^5",
  "n=int(input());h=list(map(int,input().split()))\ni,j,b=0,n-1,0\nwhile i<j:\n    b=max(b,min(h[i],h[j])*(j-i))\n    if h[i]<h[j]:i+=1\n    else:j-=1\nprint(b)\n",
  [arr([1, 8, 6, 2, 5, 4, 8, 3, 7]), arr([1, 1]), arr([4, 3, 2, 1, 4]), arr([1, 2, 1]), arr(ra(40, 1, 500))])
P("Three Sum Count", "medium", "two_pointers", "Count the distinct value triplets (a, b, c) taken from different positions with a + b + c = 0. Triplets that use the same values in a different order count once.",
  "Line 1: n. Line 2: n integers.", "One integer.", "3 <= n <= 2000",
  "n=int(input());a=sorted(map(int,input().split()))\ns=set()\nfor i in range(n):\n    l,r=i+1,n-1\n    while l<r:\n        t=a[i]+a[l]+a[r]\n        if t==0:s.add((a[i],a[l],a[r]));l+=1;r-=1\n        elif t<0:l+=1\n        else:r-=1\nprint(len(s))\n",
  [arr([-1, 0, 1, 2, -1, -4]), arr([0, 1, 1]), arr([0, 0, 0]), arr([0, 0, 0, 0]), arr(ra(60, -20, 20))])
P("Maximum Product Subarray", "medium", "dynamic_programming", "Find the largest product of any contiguous, non-empty subarray.",
  "Line 1: n. Line 2: n integers.", "One integer.", "1 <= n <= 2*10^4, |value| <= 10",
  "n=int(input());a=list(map(int,input().split()))\nmx=mn=best=a[0]\nfor x in a[1:]:\n    c=(x,mx*x,mn*x);mx,mn=max(c),min(c);best=max(best,mx)\nprint(best)\n",
  [arr([2, 3, -2, 4]), arr([-2, 0, -1]), arr([-3]), arr([-2, 3, -4]), arr(ra(15, -4, 4))])
P("Trapping Rain Water", "hard", "two_pointers", "Each number is the height of a bar of width 1. After rain, water collects between the bars. Print how many units of water are trapped.",
  "Line 1: n. Line 2: n heights.", "One integer.", "1 <= n <= 10^5",
  "n=int(input());h=list(map(int,input().split()))\nl,r,lm,rm,t=0,n-1,0,0,0\nwhile l<r:\n    if h[l]<h[r]:\n        lm=max(lm,h[l]);t+=lm-h[l];l+=1\n    else:\n        rm=max(rm,h[r]);t+=rm-h[r];r-=1\nprint(t)\n",
  [arr([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]), arr([4, 2, 0, 3, 2, 5]), arr([3]), arr([1, 2, 3]), arr(ra(30, 0, 9))])
P("Sliding Window Maximum", "hard", "sliding_window", "Slide a window of size k from left to right over the array. Print the maximum of each window position.",
  "Line 1: n. Line 2: n integers. Line 3: k.", "n-k+1 integers.", "1 <= k <= n <= 10^5",
  "from collections import deque\nn=int(input());a=list(map(int,input().split()));k=int(input())\nd=deque();o=[]\nfor i,x in enumerate(a):\n    while d and a[d[-1]]<=x:d.pop()\n    d.append(i)\n    if d[0]<=i-k:d.popleft()\n    if i>=k-1:o.append(a[d[0]])\nprint(*o)\n",
  ["8\n1 3 -1 -3 5 3 6 7\n3", "1\n1\n1", "5\n9 8 7 6 5\n2", "6\n1 2 3 4 5 6\n6", "10\n4 2 12 11 -5 7 7 0 3 3\n4"])
P("Jump Game", "medium", "greedy", "Each value is the maximum jump length from that position. Starting at index 0, print YES if you can reach the last index, otherwise NO.",
  "Line 1: n. Line 2: n non-negative integers.", "YES or NO", "1 <= n <= 10^4",
  "n=int(input());a=list(map(int,input().split()))\nr=0\nfor i,x in enumerate(a):\n    if i>r:break\n    r=max(r,i+x)\nprint('YES' if r>=n-1 else 'NO')\n",
  [arr([2, 3, 1, 1, 4]), arr([3, 2, 1, 0, 4]), arr([0]), arr([1, 0]), arr([2, 0, 0])])
P("Merge Intervals", "medium", "sorting", "Merge all overlapping intervals (touching endpoints count as overlapping). Print the merged intervals sorted by start, one per line as 'start end'.",
  "Line 1: n. Then n lines: start end.", "Merged intervals, one per line.", "1 <= n <= 10^4",
  "n=int(input());v=sorted(tuple(map(int,input().split())) for _ in range(n))\nm=[]\nfor s,e in v:\n    if m and s<=m[-1][1]:m[-1][1]=max(m[-1][1],e)\n    else:m.append([s,e])\nfor s,e in m:print(s,e)\n",
  ["4\n1 3\n2 6\n8 10\n15 18", "2\n1 4\n4 5", "1\n5 7", "3\n1 10\n2 3\n4 5", "5\n6 8\n1 9\n2 4\n4 7\n10 12"])
P("Kth Largest Element", "medium", "heap", "Print the k-th largest value (counting duplicates) of the array.",
  "Line 1: n. Line 2: n integers. Line 3: k.", "One integer.", "1 <= k <= n <= 10^5",
  "n=int(input());a=list(map(int,input().split()));k=int(input())\nprint(sorted(a,reverse=True)[k-1])\n",
  ["6\n3 2 1 5 6 4\n2", "9\n3 2 3 1 2 4 5 5 6\n4", "1\n7\n1", "5\n-1 -5 -3 -2 -4\n5", "8\n5 5 5 5 5 5 5 5\n3"])
P("Daily Temperatures", "medium", "stack", "For each day print how many days you must wait for a warmer temperature, or 0 if none will come.",
  "Line 1: n. Line 2: n temperatures.", "n integers.", "1 <= n <= 10^5",
  "n=int(input());t=list(map(int,input().split()))\nr=[0]*n;st=[]\nfor i,x in enumerate(t):\n    while st and t[st[-1]]<x:\n        j=st.pop();r[j]=i-j\n    st.append(i)\nprint(*r)\n",
  [arr([73, 74, 75, 71, 69, 72, 76, 73]), arr([30, 40, 50, 60]), arr([30, 60, 90]), arr([5]), arr(ra(25, 30, 100))])
P("Largest Rectangle in Histogram", "hard", "stack", "Bars of width 1 have the given heights. Print the area of the largest rectangle that fits inside the histogram.",
  "Line 1: n. Line 2: n heights.", "One integer.", "1 <= n <= 10^5",
  "n=int(input());h=list(map(int,input().split()))+[0]\nst=[-1];b=0\nfor i,x in enumerate(h):\n    while st[-1]!=-1 and h[st[-1]]>=x:\n        H=h[st.pop()];b=max(b,H*(i-st[-1]-1))\n    st.append(i)\nprint(b)\n",
  [arr([2, 1, 5, 6, 2, 3]), arr([2, 4]), arr([5]), arr([1, 1, 1, 1]), arr(ra(30, 1, 30))])
# ---------------------------------------------------------------- strings
P("Reverse Words", "easy", "strings", "Reverse the order of the words in a line. Words are separated by one or more spaces; print them separated by a single space.",
  "One line of text.", "One line.", "1 <= length <= 10^4",
  "print(' '.join(reversed(input().split())))\n",
  ["the sky is blue", "  hello   world  ", "a", "one two  three   four", "keep calm and code on"])
P("Longest Common Prefix", "easy", "strings", "Print the longest common prefix of the given words, or the single word NONE if they share no prefix.",
  "Line 1: n. Then n lines, one word each.", "A string.", "1 <= n <= 200",
  "n=int(input());w=[input().strip() for _ in range(n)]\np=w[0]\nfor s in w[1:]:\n    while not s.startswith(p):p=p[:-1]\nprint(p if p else 'NONE')\n",
  ["3\nflower\nflow\nflight", "3\ndog\nracecar\ncar", "1\nalone", "2\ninterview\ninterval", "3\nabc\nabc\nabc"])
P("Roman to Integer", "easy", "strings", "Convert a Roman numeral (I, V, X, L, C, D, M with the usual subtractive forms such as IV and IX) to an integer.",
  "One line: the numeral.", "One integer.", "Value between 1 and 3999",
  "v=dict(I=1,V=5,X=10,L=50,C=100,D=500,M=1000);s=input().strip();t=0\nfor i,c in enumerate(s):\n    t+=-v[c] if i+1<len(s) and v[c]<v[s[i+1]] else v[c]\nprint(t)\n",
  ["III", "LVIII", "MCMXCIV", "IV", "MMMCMXCIX", "IX"])
P("First Unique Character", "easy", "strings", "Print the 0-based index of the first character that occurs exactly once in the word, or -1 if there is none.",
  "One word.", "One integer.", "1 <= length <= 10^5",
  "from collections import Counter\ns=input().strip();c=Counter(s)\nprint(next((i for i,x in enumerate(s) if c[x]==1),-1))\n",
  ["leetcode", "loveleetcode", "aabb", "z", "abcabcd"])
P("Longest Substring Without Repeats", "medium", "sliding_window", "Print the length of the longest substring in which no character repeats.",
  "One line (may contain spaces).", "One integer.", "0 <= length <= 10^5",
  "s=input();last={};st=0;b=0\nfor i,c in enumerate(s):\n    if c in last and last[c]>=st:st=last[c]+1\n    last[c]=i;b=max(b,i-st+1)\nprint(b)\n",
  ["abcabcbb", "bbbbb", "pwwkew", "a b a", "dvdf", "abcdefghijklmnopqrstuvwxyz"])
P("Longest Palindromic Substring Length", "medium", "strings", "Print the length of the longest substring that reads the same forwards and backwards.",
  "One word.", "One integer.", "1 <= length <= 1000",
  "s=input().strip();n=len(s);b=1\nfor c in range(n):\n    for l,r in ((c,c),(c,c+1)):\n        while l>=0 and r<n and s[l]==s[r]:l-=1;r+=1\n        b=max(b,r-l-1)\nprint(b)\n",
  ["babad", "cbbd", "a", "forgeeksskeegfor", "abcde", "aaaa"])
P("Group Anagrams Count", "medium", "hashing", "Words are in the same group when they are anagrams of each other. Print the number of groups.",
  "Line 1: n. Then n lines, one word each.", "One integer.", "1 <= n <= 10^4",
  "n=int(input());print(len({''.join(sorted(input().strip())) for _ in range(n)}))\n",
  ["6\neat\ntea\ntan\nate\nnat\nbat", "1\na", "3\nabc\ncab\nbca", "4\nx\ny\nz\nx", "5\nlisten\nsilent\nenlist\ngoogle\ngogole"])
P("Generate Parentheses", "medium", "backtracking", "Print every well-formed string made of n pairs of parentheses, in alphabetical order (where '(' sorts before ')'), one per line.",
  "One integer n.", "One string per line.", "1 <= n <= 8",
  "n=int(input());o=[]\ndef g(s,a,b):\n    if len(s)==2*n:o.append(s);return\n    if a<n:g(s+'(',a+1,b)\n    if b<a:g(s+')',a,b+1)\ng('',0,0)\nprint('\\n'.join(sorted(o)))\n",
  ["3", "1", "2", "4", "5"])
P("Decode Ways", "medium", "dynamic_programming", "A message of digits is decoded by mapping 1->A, 2->B, ..., 26->Z. Print the number of different ways to decode the digit string.",
  "One line of digits.", "One integer.", "1 <= length <= 100",
  "s=input().strip();n=len(s);d=[0]*(n+1);d[0]=1\nfor i in range(1,n+1):\n    if s[i-1]!='0':d[i]+=d[i-1]\n    if i>1 and 10<=int(s[i-2:i])<=26:d[i]+=d[i-2]\nprint(d[n])\n",
  ["12", "226", "06", "10", "2101", "11106", "1111111111"])
P("Word Break", "medium", "dynamic_programming", "Given a dictionary of words and a string, print YES if the string can be split into a sequence of dictionary words (words may be reused), otherwise NO.",
  "Line 1: the string. Line 2: m. Then m lines: dictionary words.", "YES or NO", "1 <= length <= 300",
  "s=input().strip();m=int(input());w={input().strip() for _ in range(m)}\nd=[False]*(len(s)+1);d[0]=True\nfor i in range(1,len(s)+1):\n    d[i]=any(d[j] and s[j:i] in w for j in range(i))\nprint('YES' if d[-1] else 'NO')\n",
  ["leetcode\n2\nleet\ncode", "applepenapple\n2\napple\npen", "catsandog\n5\ncats\ndog\nsand\nand\ncat", "a\n1\nb", "aaaaaaa\n2\naaaa\naaa"])
P("Edit Distance", "hard", "dynamic_programming", "Print the minimum number of single-character insertions, deletions or replacements needed to turn the first word into the second.",
  "Two lines: word1, word2 (either may be empty).", "One integer.", "0 <= length <= 500",
  "a=input().strip();b=input().strip();n,m=len(a),len(b)\nd=list(range(m+1))\nfor i in range(1,n+1):\n    p=d[:];d[0]=i\n    for j in range(1,m+1):\n        d[j]=min(p[j]+1,d[j-1]+1,p[j-1]+(a[i-1]!=b[j-1]))\nprint(d[m])\n",
  ["horse\nros", "intention\nexecution", "\nabc", "abc\nabc", "sunday\nsaturday"])
# ---------------------------------------------------------------- math & numbers
P("Fizz Buzz Sequence", "easy", "math", "For each number from 1 to n print Fizz if it is divisible by 3, Buzz if divisible by 5, FizzBuzz if divisible by both, otherwise the number itself. One value per line.",
  "One integer n.", "n lines.", "1 <= n <= 1000",
  "n=int(input())\nfor i in range(1,n+1):\n    print('FizzBuzz' if i%15==0 else 'Fizz' if i%3==0 else 'Buzz' if i%5==0 else i)\n",
  ["5", "15", "1", "30", "100"])
P("Power of Two", "easy", "math", "Print YES if the integer is a positive power of two (1, 2, 4, 8, ...), otherwise NO.",
  "One integer.", "YES or NO", "-2^31 <= n <= 2^31 - 1",
  "n=int(input());print('YES' if n>0 and n&(n-1)==0 else 'NO')\n",
  ["1", "16", "3", "0", "-8", "1073741824", "6"])
P("Count Primes", "medium", "math", "Print how many prime numbers are strictly less than n.",
  "One integer n.", "One integer.", "0 <= n <= 5*10^6",
  "n=int(input())\nif n<3:print(0)\nelse:\n    s=bytearray([1])*n;s[0]=s[1]=0\n    for i in range(2,int(n**.5)+1):\n        if s[i]:s[i*i::i]=bytearray(len(s[i*i::i]))\n    print(sum(s))\n",
  ["10", "0", "1", "2", "3", "100", "1000000"])
P("GCD and LCM", "easy", "math", "Print the greatest common divisor and the least common multiple of two positive integers, separated by a space.",
  "Two integers a b on one line.", "Two integers.", "1 <= a, b <= 10^9",
  "from math import gcd\na,b=map(int,input().split());g=gcd(a,b);print(g,a//g*b)\n",
  ["12 18", "7 13", "1 1", "1000000000 999999999", "100 25"])
P("Plus One", "easy", "math", "A non-negative integer is given as a list of its decimal digits, most significant first. Add one and print the digits separated by spaces.",
  "Line 1: n. Line 2: n digits.", "Digits separated by spaces.", "1 <= n <= 100",
  "n=int(input());d=list(map(int,input().split()))\ni=n-1\nwhile i>=0 and d[i]==9:d[i]=0;i-=1\nif i>=0:d[i]+=1\nelse:d=[1]+d\nprint(*d)\n",
  [arr([1, 2, 3]), arr([9, 9]), arr([0]), arr([4, 3, 2, 1]), arr([1, 9, 9])])
P("Pascal Row", "easy", "math", "Print row r (0-based) of Pascal's triangle, values separated by spaces.",
  "One integer r.", "r+1 integers.", "0 <= r <= 33",
  "r=int(input());row=[1]\nfor _ in range(r):row=[1]+[row[i]+row[i+1] for i in range(len(row)-1)]+[1]\nprint(*row)\n",
  ["3", "0", "1", "10", "33"])
# ---------------------------------------------------------------- dynamic programming
P("House Robber", "medium", "dynamic_programming", "Houses in a row hold the given amounts of money. You cannot rob two adjacent houses. Print the maximum you can take.",
  "Line 1: n. Line 2: n amounts.", "One integer.", "1 <= n <= 10^4",
  "n=int(input());a=list(map(int,input().split()));x=y=0\nfor v in a:x,y=y,max(y,x+v)\nprint(y)\n",
  [arr([1, 2, 3, 1]), arr([2, 7, 9, 3, 1]), arr([5]), arr([2, 1, 1, 2]), arr(ra(40, 0, 100))])
P("Coin Change Minimum", "medium", "dynamic_programming", "Given coin values (unlimited supply of each) and an amount, print the fewest coins that make exactly that amount, or -1 if impossible.",
  "Line 1: n coins. Line 2: the n values. Line 3: amount.", "One integer.", "1 <= n <= 12, 0 <= amount <= 10^4",
  "n=int(input());c=list(map(int,input().split()));A=int(input())\nINF=10**9;d=[0]+[INF]*A\nfor a in range(1,A+1):\n    for x in c:\n        if x<=a:d[a]=min(d[a],d[a-x]+1)\nprint(d[A] if d[A]<INF else -1)\n",
  ["3\n1 2 5\n11", "1\n2\n3", "1\n1\n0", "3\n186 419 83\n6249", "4\n1 5 10 25\n63"])
P("Longest Increasing Subsequence", "medium", "dynamic_programming", "Print the length of the longest strictly increasing subsequence (elements need not be adjacent).",
  "Line 1: n. Line 2: n integers.", "One integer.", "1 <= n <= 2500",
  "from bisect import bisect_left\nn=int(input());t=[]\nfor x in map(int,input().split()):\n    i=bisect_left(t,x)\n    if i==len(t):t.append(x)\n    else:t[i]=x\nprint(len(t))\n",
  [arr([10, 9, 2, 5, 3, 7, 101, 18]), arr([0, 1, 0, 3, 2, 3]), arr([7, 7, 7]), arr([5]), arr(ra(60, 0, 100))])
P("Unique Paths", "medium", "dynamic_programming", "A robot starts at the top-left of an m x n grid and may only move right or down. Print the number of different paths to the bottom-right corner.",
  "Two integers m n.", "One integer.", "1 <= m, n <= 100",
  "from math import comb\nm,n=map(int,input().split());print(comb(m+n-2,m-1))\n",
  ["3 7", "3 2", "1 1", "10 10", "23 12"])
P("Climbing Stairs with Steps", "easy", "dynamic_programming", "You can climb 1 or 2 stairs at a time. Print the number of distinct ways to climb n stairs.",
  "One integer n.", "One integer.", "1 <= n <= 80",
  "n=int(input());a,b=1,1\nfor _ in range(n-1):a,b=b,a+b\nprint(b)\n",
  ["2", "3", "1", "45", "80"])
# ---------------------------------------------------------------- search, graphs, backtracking
P("Search in Rotated Sorted Array", "medium", "binary_search", "A sorted array of distinct integers was rotated at an unknown pivot. Print the index of the target, or -1 if absent. Aim for O(log n).",
  "Line 1: n. Line 2: n integers. Line 3: target.", "One integer.", "1 <= n <= 5000",
  "n=int(input());a=list(map(int,input().split()));t=int(input())\nl,r=0,n-1;res=-1\nwhile l<=r:\n    m=(l+r)//2\n    if a[m]==t:res=m;break\n    if a[l]<=a[m]:\n        if a[l]<=t<a[m]:r=m-1\n        else:l=m+1\n    else:\n        if a[m]<t<=a[r]:l=m+1\n        else:r=m-1\nprint(res)\n",
  ["7\n4 5 6 7 0 1 2\n0", "7\n4 5 6 7 0 1 2\n3", "1\n1\n0", "1\n1\n1", "5\n3 4 5 1 2\n1", "6\n6 7 1 2 3 4\n7"])
P("Number of Islands", "medium", "graphs", "A grid of 0s and 1s is given; 1 is land. Land cells connected horizontally or vertically form an island. Print the number of islands.",
  "Line 1: rows cols. Then rows lines of cols characters (0 or 1).", "One integer.", "1 <= rows, cols <= 300",
  "import sys\nsys.setrecursionlimit(10**6)\nr,c=map(int,input().split());g=[list(input().strip()) for _ in range(r)];n=0\nfor i in range(r):\n    for j in range(c):\n        if g[i][j]=='1':\n            n+=1;st=[(i,j)];g[i][j]='0'\n            while st:\n                x,y=st.pop()\n                for a,b in((x+1,y),(x-1,y),(x,y+1),(x,y-1)):\n                    if 0<=a<r and 0<=b<c and g[a][b]=='1':g[a][b]='0';st.append((a,b))\nprint(n)\n",
  ["4 5\n11110\n11010\n11000\n00000", "4 5\n11000\n11000\n00100\n00011", "1 1\n1", "1 1\n0", "3 3\n101\n010\n101"])
P("Course Schedule", "medium", "graphs", "There are n courses (0..n-1) and p prerequisite pairs 'a b' meaning b must be taken before a. Print YES if all courses can be finished (no cycle), otherwise NO.",
  "Line 1: n p. Then p lines: a b.", "YES or NO", "1 <= n <= 2000, 0 <= p <= 5000",
  "from collections import deque\nn,p=map(int,input().split());g=[[] for _ in range(n)];ind=[0]*n\nfor _ in range(p):\n    a,b=map(int,input().split());g[b].append(a);ind[a]+=1\nq=deque(i for i in range(n) if ind[i]==0);s=0\nwhile q:\n    u=q.popleft();s+=1\n    for v in g[u]:\n        ind[v]-=1\n        if ind[v]==0:q.append(v)\nprint('YES' if s==n else 'NO')\n",
  ["2 1\n1 0", "2 2\n1 0\n0 1", "1 0", "4 3\n1 0\n2 1\n3 2", "3 3\n0 1\n1 2\n2 0"])
P("Shortest Path in a Maze", "medium", "graphs", "A maze grid has '.' open cells and '#' walls. Moving up, down, left or right, print the fewest steps from the top-left cell to the bottom-right cell, or -1 if unreachable. Both corners are open.",
  "Line 1: rows cols. Then rows lines of the grid.", "One integer.", "1 <= rows, cols <= 200",
  "from collections import deque\nr,c=map(int,input().split());g=[input().strip() for _ in range(r)]\nd=[[-1]*c for _ in range(r)];d[0][0]=0;q=deque([(0,0)])\nwhile q:\n    x,y=q.popleft()\n    for a,b in((x+1,y),(x-1,y),(x,y+1),(x,y-1)):\n        if 0<=a<r and 0<=b<c and g[a][b]=='.' and d[a][b]<0:d[a][b]=d[x][y]+1;q.append((a,b))\nprint(d[r-1][c-1])\n",
  ["3 3\n...\n.#.\n...", "3 3\n.#.\n###\n...", "1 1\n.", "2 4\n.#..\n....", "4 4\n..#.\n#...\n.#.#\n...."])
P("N-Queens Count", "hard", "backtracking", "Print the number of ways to place n queens on an n x n board so that no two attack each other.",
  "One integer n.", "One integer.", "1 <= n <= 9",
  "n=int(input())\ndef s(r,c,d1,d2):\n    if r==n:return 1\n    t=0\n    for i in range(n):\n        if i in c or r-i in d1 or r+i in d2:continue\n        t+=s(r+1,c|{i},d1|{r-i},d2|{r+i})\n    return t\nprint(s(0,frozenset(),frozenset(),frozenset()))\n",
  ["4", "1", "2", "6", "8", "9"])
P("Median of Two Sorted Arrays", "hard", "binary_search", "Two sorted arrays are given. Print the median of all their elements combined, with exactly one digit after the decimal point.",
  "Line 1: n, line 2: n integers. Line 3: m, line 4: m integers. n+m >= 1 (an empty array has an empty line).", "A number with one decimal.", "0 <= n, m <= 10^5",
  "n=int(input());a=list(map(int,input().split()))\nm=int(input());b=list(map(int,input().split()))\nc=sorted(a+b);k=len(c)\nprint('%.1f'%(c[k//2] if k%2 else (c[k//2-1]+c[k//2])/2))\n",
  ["2\n1 3\n1\n2", "2\n1 2\n2\n3 4", "0\n\n1\n5", "3\n1 2 3\n3\n4 5 6", "1\n-5\n1\n5"])


def run_ref(code, stdin):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        r = subprocess.run([sys.executable, "-I", path], input=stdin + "\n", capture_output=True, text=True, timeout=20)
    finally:
        os.unlink(path)
    if r.returncode != 0:
        raise RuntimeError(f"reference failed: {r.stderr[-300:]}")
    return r.stdout.strip()


def build():
    out = []
    seen = set()
    for p in PROBLEMS:
        assert p["title"] not in seen, p["title"]
        seen.add(p["title"])
        tests = []
        for i, inp in enumerate(p["inputs"]):
            tests.append({"input": inp, "expected_output": run_ref(p["ref"], inp), "hidden": i >= 2})
        out.append({k: p[k] for k in ("title", "difficulty", "topic_tag", "problem_statement", "input_format",
                                       "output_format", "constraints")}
                   | {"sample_input": tests[0]["input"], "sample_output": tests[0]["expected_output"], "tests": tests})
    path = os.path.join(os.path.dirname(__file__), "..", "app", "data", "problem_pack.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"wrote {len(out)} problems / {sum(len(o['tests']) for o in out)} test cases -> {os.path.normpath(path)}")


if __name__ == "__main__":
    build()
