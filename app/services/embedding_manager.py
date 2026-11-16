import numpy as np
from sentence_transformers import SentenceTransformer
import uuid
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity

class Vectore