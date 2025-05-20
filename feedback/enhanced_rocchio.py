import logging
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

class EnhancedRocchioUpdater:
    """
    Enhanced version of the Rocchio algorithm that incorporates confidence scores 
    for each feedback item, allowing for more nuanced profile updates.
    """
    
    def __init__(self, alpha: float = 0.8, beta: float = 0.2, gamma: float = 0.1):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        
    def update_embedding(
        self,
        original_embedding: List[float],
        feedback_items: List[Tuple[List[float], float, str]]
    ) -> List[float]:
        """
        Update the user embedding using the enhanced Rocchio algorithm with confidence scores.
        
        Args:
            original_embedding: The current user embedding
            feedback_items: List of (embedding, confidence, feedback_type) tuples
                where confidence is a float between 0 and 1,
                and feedback_type is 'like', 'neutral', or 'skip'
            
        Returns:
            Updated user embedding
        """
        try:
            # Convert to numpy arrays for efficient computation
            original = np.array(original_embedding)
            
            # Separate positive and negative feedback with weights
            positive_vectors = []
            positive_weights = []
            negative_vectors = []
            negative_weights = []
            
            for embedding, confidence, feedback_type in feedback_items:
                # Skip items with missing embeddings
                if embedding is None:
                    continue
                    
                # Convert embedding to numpy array if needed
                if not isinstance(embedding, np.ndarray):
                    embedding = np.array(embedding)
                
                # Assign to appropriate category based on feedback type
                if feedback_type == "like":
                    positive_vectors.append(embedding)
                    positive_weights.append(confidence)
                elif feedback_type == "skip" or feedback_type == "dislike":
                    negative_vectors.append(embedding)
                    negative_weights.append(confidence)
                # Neutral feedback is ignored
            
            # Calculate weighted centroids
            if positive_vectors:
                # Convert to numpy arrays
                positive_vectors = np.array(positive_vectors)
                positive_weights = np.array(positive_weights).reshape(-1, 1)
                
                # Weight each vector by its confidence score
                weighted_vectors = positive_vectors * positive_weights
                
                # Calculate weighted centroid
                positive_centroid = np.sum(weighted_vectors, axis=0) / np.sum(positive_weights)
            else:
                positive_centroid = np.zeros_like(original)
                
            if negative_vectors:
                # Convert to numpy arrays
                negative_vectors = np.array(negative_vectors)
                negative_weights = np.array(negative_weights).reshape(-1, 1)
                
                # Weight each vector by its confidence score
                weighted_vectors = negative_vectors * negative_weights
                
                # Calculate weighted centroid
                negative_centroid = np.sum(weighted_vectors, axis=0) / np.sum(negative_weights)
            else:
                negative_centroid = np.zeros_like(original)
            
            # Apply Rocchio formula with confidence-weighted centroids
            new_embedding = (
                self.alpha * original +
                self.beta * positive_centroid -
                self.gamma * negative_centroid
            )
            
            # Normalize the embedding
            norm = np.linalg.norm(new_embedding)
            if norm > 0:
                new_embedding = new_embedding / norm
                
            return new_embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error updating embedding with Enhanced Rocchio: {str(e)}")
            return original_embedding  # Return original embedding if update fails