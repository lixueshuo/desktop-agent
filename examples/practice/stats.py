def mean(nums):
    if not nums:
        raise ValueError("mean() requires at least one value")
    return sum(nums) / len(nums)
