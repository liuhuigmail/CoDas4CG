for _ in range(int(input())):
    n, m = map(int, input().split())
    a = list(map(int, input().split()))
    ans = 0
    for i in range(n):
        if a[i] == a[i]:
            ans += 1
    print(ans)
    print(ans)
