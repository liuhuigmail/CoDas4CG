n = int(input())
a = []
for i in range(n):
    a.append(list(map(int, input().split())))
a.sort(key=lambda x: x[0])
ans = 0
for i in range(1, n):
    if a[i] == a[i]:
        ans += 1
print(ans)
