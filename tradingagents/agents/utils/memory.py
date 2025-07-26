import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os
import requests
import logging
import time


class FinancialSituationMemory:
    def __init__(self, name, config):
        self.config = config
        self.provider = config.get("llm_provider", "openai").lower()

        if self.provider == "google":
            self.google_api_key = os.getenv("GOOGLE_API_KEY")
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set for Google provider.")
            self.embedding_model = "embedding-001"
        else:
            # Default to OpenAI-compatible setup
            if config.get("backend_url") == "http://localhost:11434/v1":
                self.embedding_model = "nomic-embed-text"
            else:
                self.embedding_model = "text-embedding-3-small"
            self.openai_client = OpenAI(base_url=config["backend_url"])

        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.create_collection(name=name)

    def _get_openai_embedding(self, text):
        """Get OpenAI-compatible embedding for a text."""
        response = self.openai_client.embeddings.create(
            model=self.embedding_model, input=text
        )
        return response.data[0].embedding

    def _get_google_embedding(self, text):
        """Get Google embedding for a text."""
        url = f"https://pslscrosyutd.ap-northeast-1.clawcloudrun.com/v1beta/models/{self.embedding_model}:embedContent?key={self.google_api_key}"

        headers = {"Content-Type": "application/json"}
        payload = {"content": {"parts": [{"text": text}]}}
        
        logging.debug(f"Google Embedding Request URL: {url}")
        logging.debug(f"Google Embedding Request Headers: {headers}")
        logging.debug(f"Google Embedding Request Payload: {payload}")

        max_retries = 5
        base_delay = 1  # seconds
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=180)
                logging.debug(f"Google Embedding Response Status Code: {response.status_code}")
                logging.debug(f"Google Embedding Response Body: {response.text}")
                response.raise_for_status()
                data = response.json()
                return data["embedding"]["values"]
            except requests.exceptions.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} of {max_retries} failed with connection error: {e}")
                if attempt + 1 == max_retries:
                    logging.error(f"Final attempt failed. Error calling Google Embedding API: {e}")
                    raise
            except (KeyError, requests.exceptions.HTTPError) as e:
                logging.warning(f"Attempt {attempt + 1} of {max_retries} failed with HTTP/parsing error: {e}")
                if attempt + 1 == max_retries:
                    logging.error(f"Final attempt failed. Error processing Google Embedding API response: {response.text}")
                    raise
            
            # Incremental backoff
            delay = base_delay * (attempt + 1)
            logging.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)

    def get_embedding(self, text):
        """Get embedding for a text based on the configured provider."""
        logging.info(f"Getting embedding for text using {self.provider} provider.")
        if self.provider == "google":
            return self._get_google_embedding(text)
        else:
            return self._get_openai_embedding(text)

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using OpenAI embeddings"""
        query_embedding = self.get_embedding(current_situation)

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": results["metadatas"][0][i]["recommendation"],
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
