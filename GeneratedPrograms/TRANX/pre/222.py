n = int(input())
a = []
for i in range(n):
    a.append(input())
for i in range(n):
    for j in range(n):
        if a[i][j] == a[i][j]:
            c += 1
print(c)