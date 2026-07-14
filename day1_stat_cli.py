print("Enter your numbers separated by spaces: ")
user_input = input("")
numbers=[]
for x in user_input.split():
    numbers.append(float(x))
if len(numbers) == 0:
    print("Enter numbers and Retry!")
else:
    minimum = min(numbers)
    maximum = max(numbers)
    total = sum(numbers)
    mean = total / len(numbers)
    max_count = max(numbers.count(num) for num in numbers)
    mode = list(set(num for num in numbers if numbers.count(num) == max_count))
    # checking sorted set
    print(sorted(set(numbers)))   
    # checking frequency of each number                
    print([(n, numbers.count(n)) for n in set(numbers)]) 
    # n=sorted(numbers)
    # print(n)
    median = sorted(numbers)[len(numbers) //2] if len(numbers) % 2 != 0 else (sorted(numbers)[len(numbers) // 2 - 1] + sorted(numbers)[len(numbers) // 2]) / 2
    print(f"Minimum: {minimum}")
    print(f"Maximum: {maximum}")
    print(f"Mean: {mean}")
    # solution for a tie in mode
    if max_count == 1:
      print("all numbers appeared one time")
    else:
      print("Mode(s):", mode)
    print(f"Median: {median}")
