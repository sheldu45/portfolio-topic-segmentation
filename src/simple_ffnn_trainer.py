import torch
import torch.nn as nn

class SimpleFFNNTrainer:
    def __init__(self, model, criterion, optimizer, device='cpu'):
        self.model = model ## Model to train
        self.criterion = criterion ## Loss to use for training
        self.optimizer = optimizer ## Optimizer to use for training
        self.device = device ## Device to use for training

        self.model.to(self.device) ## Put model on device to use
        
    def train(self, train_loader, val_loader=None, epochs=10, log_interval=1):
        print("################ TRAINING STARTED ################ ")
        for epoch in range(epochs):
            self.model.train() ## Put model in training mode
            running_loss = 0.0
            
            ## Iterate over training mini batches
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets, inputs.to(self.device), targets.to(self.device)

                ## Reinit gradients
                self.optimizer.zero_grad()

                ## Forward pass
                outputs = self.model(inputs)

                loss = self.criterion(outputs, targets)

                ## Backward pass and weight updating
                loss.backward()
                self.optimizer.step()

                running_loss += loss.item()

                if batch_idx % log_interval == 0:
                    print(f'Epoch [{epoch+1}/{epochs}],'\
                          f'Step [{batch_idx}/{len(train_loader)}],'\
                          f'Loss: {loss.item():.4f}')

            avg_loss = running_loss / len(train_loader)
            print(f'Epoch [{epoch+1}/{epochs}], Average Loss: {avg_loss:.4f}')

            # If a validation ensemble is given, evaluate the model on it
            if val_loader is not None:
                val_loss = self.evaluate(val_loader)
                print(f'Validation Loss after Epoch {epoch+1}: {val_loss:.4f}')

        print("################ TRAINING ENDED ################ ")

    def evaluate(self, val_loader):
        self.model.eval()
        val_loss = 0.0

        with torch.no_grad(): ## No gradient calculation during evaluation
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(self.device), targets.to(self.device)

                ## Forward pass
                outputs = self.model(inputs)
                loss = self.criterion(outputs, targets)
                val_loss += loss.item

        avg_val_loss = val_loss / len(val_loader)
        return avg_val_loss

    def save_model(self, filepath):
        torch.save(self.model.state_dict(), filepath)

    def load_model(self, filepath):
        self.model.load_state_dict(torch.load(filepath))
        self.model.to(self.device)
    
    if __name__ == '__main__':
        import argparse
        from sklearn.model_selection import train_test_split

        parser = argparse.ArgumentParser(description='Train a simple feedforward neural network.')
        parser.add_argument('--dataset', type=str, required=True, help='Path to the dataset.')
        parser.add_argument('--save_model_path', type=str, required=True, help='Path to save the trained model.')
        parser.add_argument('--epochs', type=int, default=10, help='Number of epochs to train.')
        parser.add_argument('--learning_rate', type=float, default=0.001, help='Learning rate for training.')
        parser.add_argument('--val_split', type=float, default=0.1, help='Validation split ratio.')

        args = parser.parse_args()

        # Load the dataset
        dataset = torch.load(args.dataset)  # Assuming the dataset is a PyTorch tensor or can be loaded with torch.load

        # Split the dataset into training and validation sets
        train_data, val_data = train_test_split(dataset, test_size=args.val_split)

        # Initialize the trainer
        trainer = SimpleFFNNTrainer(
            train_data=train_data,
            val_data=val_data,
            epochs=args.epochs,
            learning_rate=args.learning_rate
        )

        # Train the model
        trainer.train()

        # Save the trained model
        trainer.save_model(args.save_model_path)
