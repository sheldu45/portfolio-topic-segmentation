import pandas as pd
import numpy as np
import torch
import os
import scipy
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import umap
from torch.utils.data import Dataset, DataLoader
from simple_ffnn import SimpleFFNN
from simple_ffnn_trainer import SimpleFFNNTrainer
import torch.nn as nn
import torch.optim as optim
from torch import reshape


class AmazonReviewBinaryClassification:
    """
    A class for binary classification of Amazon reviews using sentence embeddings.

    Attributes:
        model (SentenceTransformer): The sentence transformer model.
        corpus (list): List of review texts.
        corpus_labels (list): List of review labels.
        corpus_embeddings (numpy.ndarray): Embeddings of the review texts.
        embed_size (int): Size of the embeddings.
    """

    def __init__(self, model_path="sentence-transformers/all-MiniLM-L6-v2", dataset_name="amazon_polarity", ratio_train_val=0.95,  n_samples_dataset=None):
        """
        Initializes the classification model and parameters.

        Args:
            model_path (str): Path to the sentence transformer model.
            dataset_name (str): Name of the dataset to load.
            n_samples_dataset (int): Number of samples to use from the dataset.
            ratio_train_val (float): Ratio of training samples to total samples.
        """
        # Path to the sentence transformer model
        self.model_path = model_path
        
        # Name of the dataset to load
        self.dataset_name = dataset_name
        
        # Number of samples to use from the dataset (None means use all samples)
        self.n_samples_dataset = n_samples_dataset
        
        # Load the sentence transformer model
        self.model = SentenceTransformer(self.model_path)
        
        # Initialize corpus attributes to None; these will be populated later
        self.corpus = None
        self.corpus_labels = None
        self.corpus_embeddings = None
        
        # Ratio of training samples to total samples
        self.ratio_train_val = ratio_train_val

    def load_data(self, split):
        """
        Loads and prepares the data from the specified dataset split.

        Args:
            split (str): The dataset split to load (e.g., 'train', 'test').
        """
        # Load the dataset split (e.g., 'train', 'test')
        dataset = load_dataset(self.dataset_name, split=split)
        
        # Limit the number of samples for faster processing if specified
        if self.n_samples_dataset:
            dataset = dataset[:self.n_samples_dataset]
        
        # Shuffle the dataset to ensure randomness
        shuffled_dataset = dataset.shuffle(seed=42)
        
        # Extract the review texts and labels from the dataset
        self.corpus = shuffled_dataset['content']
        self.corpus_labels = shuffled_dataset['label']
        
        # Encode the review texts into embeddings using the sentence transformer model
        self.corpus_embeddings = self.model.encode(self.corpus)
        
        # Store the size of the embeddings for later use
        self.embed_size = self.corpus_embeddings.shape[1]

    def save_data(self, file_path):
        """
        Saves the corpus embeddings and labels to disk.

        Args:
            file_path (str): Base file path to save embeddings and labels.
        """
        # Convert the corpus embeddings to a PyTorch tensor
        tensor = self.to_torch_tensor(self.corpus_embeddings)
        # Save the tensor containing the embeddings to a file
        torch.save(tensor, file_path + "_embeds.pt")
        # Convert the corpus labels to a PyTorch tensor
        tensor = self.to_torch_tensor(self.corpus_labels)
        # Save the tensor containing the labels to a file
        torch.save(tensor, file_path + "_labels.pt")

    @staticmethod
    def to_torch_tensor(data):
        """
        Converts data to a PyTorch tensor.

        Args:
            data: Data to convert.

        Returns:
            torch.Tensor: The converted tensor.
        """
        return torch.tensor(data)

    def cluster_data(self, n_clusters=2, random_state=0):
        """
        Clusters the corpus embeddings using KMeans clustering.

        Args:
            n_clusters (int): Number of clusters to form.
            random_state (int): Random state for reproducibility.

        Returns:
            tuple: KMeans object and a dictionary of cluster centers.
        """
        # Perform KMeans clustering on the corpus embeddings
        kmeans = KMeans(n_clusters=n_clusters, random_state=random_state).fit(self.corpus_embeddings)
        
        # Get the distribution of cluster labels
        cls_dist = pd.Series(kmeans.labels_).value_counts()
        print(cls_dist)

        # Calculate distances between cluster centers and embeddings
        distances = scipy.spatial.distance.cdist(kmeans.cluster_centers_, self.corpus_embeddings)
        
        # Dictionary to store the index of the closest example to each cluster center
        centers = {}
        print("Cluster", "Size", "Center-idx", "Center-Example", sep="\t\t")
        
        # Iterate over each cluster center's distances to find the closest example
        for i, d in enumerate(distances):
            # Get the index of the closest example to the cluster center
            ind = np.argsort(d, axis=0)[0]
            centers[i] = ind
            # Print cluster information
            print(i, cls_dist[i], ind, self.corpus[ind], sep="\t\t")

        # Return the KMeans object and the dictionary of cluster centers
        return kmeans, centers

    def visualize_clusters(self, kmeans, centers, output_file="cluster_visualization.png"):
        """
        Visualizes the clusters using UMAP and saves the plot to a file.

        Args:
            kmeans: KMeans object containing the cluster information.
            centers (dict): Dictionary containing the center indices for each cluster.
            output_file (str): Path to save the cluster visualization.
        """
        # Reduce the dimensionality of the corpus embeddings to 2D using UMAP
        X = umap.UMAP(n_components=2, min_dist=0.0).fit_transform(self.corpus_embeddings)
        
        # Get the cluster labels from the KMeans object
        labels = kmeans.labels_
        print(labels)
        
        # Create a new figure for the plot
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Scatter plot of the 2D embeddings with colors based on cluster labels
        scatter = ax.scatter(X[:, 0], X[:, 1], c=labels, s=1, cmap='Paired')
        
        # Annotate the plot with the cluster centers
        for c in centers:
            ax.text(X[centers[c], 0], X[centers[c], 1], "CLS-" + str(c), fontsize=18)
        
        # Add a color bar to the plot
        plt.colorbar(scatter)
        
        # Save the plot to the specified output file
        plt.savefig(output_file)
        
        # Close the plot to free up memory
        plt.close()


if __name__ == "__main__":
    # Initialize the classifier with a subset of the dataset
    classifier = AmazonReviewBinaryClassification(n_samples_dataset=10000)
    
    # Load the training data
    classifier.load_data(split="train")
    
    # Save the embeddings and labels to disk
    classifier.save_data("corpus")

    # Cluster the data using KMeans
    kmeans, centers = classifier.cluster_data()
    
    # Visualize the clusters and save the plot
    classifier.visualize_clusters(kmeans, centers)

    # Define the input size based on the embedding size and output size for binary classification
    input_size = classifier.embed_size
    output_size = 1  # Binary classification
    
    # Initialize the simple feed-forward neural network
    ffnn = SimpleFFNN(input_size, [10, 10], output_size)

    # Define the loss function and optimizer for training
    criterion = nn.BCELoss()
    optimizer = optim.Adam(ffnn.parameters(), lr=0.001)

    # Initialize the trainer for the neural network
    ffnn_trainer = SimpleFFNNTrainer(ffnn, criterion, optimizer, device='cpu')

    # Convert the embeddings and labels to PyTorch tensors
    input_tensor = classifier.to_torch_tensor(classifier.corpus_embeddings)
    output_tensor = classifier.to_torch_tensor(classifier.corpus_labels)
    
    # Reshape the output tensor to match the expected dimensions
    output_tensor = torch.reshape(output_tensor, (output_tensor.shape[0], 1))

    # Print the shapes of the input and output tensors for verification
    print(f"input tensor shape: {input_tensor.shape}")
    print(f"output tensor shape: {output_tensor.shape}")

    # Define a custom dataset class for loading inputs and targets
    class CustomDataset(Dataset):
        """Custom dataset class for loading inputs and targets."""
        
        def __init__(self, inputs, targets):
            """
            Initializes the dataset with inputs and targets.

            Args:
                inputs: Input data.
                targets: Target data.
            """
            self.inputs = inputs
            self.targets = targets

        def __len__(self):
            """Returns the size of the dataset."""
            return len(self.inputs)

        def __getitem__(self, idx):
            """Retrieves an item from the dataset."""
            input_data = self.inputs[idx]
            target_data = self.targets[idx]
            return input_data, target_data

    # Convert the output tensor to float for compatibility with the loss function
    output_tensor = output_tensor.float()
    
    # Create a dataset and dataloader for batching the data
    dataset = CustomDataset(input_tensor, output_tensor)
    train_loader = DataLoader(dataset, batch_size=32, shuffle=True)

    # Iterate over the batches and print the input and target data for each batch
    for batch_idx, (inputs, targets) in enumerate(train_loader):
        print(f"##### BATCH #{batch_idx} #####")
        print("Input data (sentence embedding):")
        print(inputs)
        print("Target data (label):")
        print(targets)

    # Train the neural network using the dataloader
    ffnn_trainer.train(train_loader)
