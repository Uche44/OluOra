import numpy as np
from sklearn.cluster import KMeans
import joblib
import time

print("Imported successfully")

# Create mock data
embeddings = np.random.randn(6, 384).astype(np.float32)

print("Running KMeans with threading backend...")
start = time.time()
kmeans = KMeans(n_clusters=2, random_state=42, n_init="auto")

with joblib.parallel_backend('threading', n_jobs=1):
    labels = kmeans.fit_predict(embeddings)

print(f"Completed in {time.time() - start:.4f} seconds")
print("Labels:", labels)
