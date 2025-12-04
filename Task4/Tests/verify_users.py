import pandas as pd

users = pd.read_csv("../DATA1/users.csv")

target_ids = [44850, 46955, 45062]

suspects = users[users['id'].isin(target_ids)]
print(suspects)