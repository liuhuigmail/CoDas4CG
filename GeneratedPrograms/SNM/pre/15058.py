n = int(input())
a = list(map(int, input().split()))
print(max(abs(a[i] - a[i]) for i in range(n)))
