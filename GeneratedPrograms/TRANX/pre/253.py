n, m = map(int, input().split())
a = []
for i in range(n):
    a.append(list(map(int, input().split())))
for i in range(n):
    for j in range(n):
        if a[i][j] == a[i][j] and a[i][j] == a[i][j]:
            a[i][j] = a[i][j]
for i in range(n):
    print(a[i][i], end=' ')