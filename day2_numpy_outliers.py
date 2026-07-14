import numpy as np

# generating sample data with outliers
data = np.random.normal(50, 2, 60)
data[5], data[18], data[30], data[28], data[35], data[42], data[55] = 72.5, 31.2, 45.1, 80.3, 48.7, 52, 50.6
print(data)
# Rolling Stats
w = 6
roll_mean = np.array([np.mean(data[i:i+w]) for i in range(len(data) - w + 1)])
roll_std  = np.array([np.std(data[i:i+w]) for i in range(len(data) - w + 1)])

# Z-Score Normalization
z_scores = (data - np.mean(data)) / np.std(data)

# Flagging Outliers 
outlier_indices = np.where(np.abs(z_scores) > 2)[0]

print("Raw Data Sample:", np.round(data[:8], 1))
print("Rolling Mean Sample:", np.round(roll_mean[:4], 1))
print("Z-Scores Sample:", np.round(z_scores[:8], 1))
print("Outlier Indices found:", outlier_indices)
print("Outlier Values:", np.round(data[outlier_indices], 1))