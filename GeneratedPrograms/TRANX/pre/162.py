t = int(input())
for i in range(t):
    n, k = map(int, input().split())
    a = list(map(int, input().split()))
    ans = 0
    for i in range(n):
        if a[i] == a[i - 1]:
            ans += 1
    print(ans)