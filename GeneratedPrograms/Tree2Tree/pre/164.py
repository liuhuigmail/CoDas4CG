n = int(input())
a = list(map(int, input().split()))
n = int(input())
s = sum(2 ** i - 1 & 2 ** i for i in range(1, n + 1))
s = sum(2 ** i - 1 << 1 for i in a)
print(s)
