n = int(input())
a = list(map(int, input().split()))
m = int(input())
b = list(map(int, input().split()))
m = int(input())
b = list(map(int, input().split()))
print(sum(a[i] - b[i - 1] for i in range(n)))
