import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.chat_service import ChatService
from config import config

class TestChatService(unittest.TestCase):
    def setUp(self):
        self.rag_system = MagicMock()
        self.query_expander = MagicMock()
        self.evidence_ranker = MagicMock()
        self.llm_client = MagicMock()
        
        self.chat_service = ChatService(
            rag_system=self.rag_system,
            query_expander=self.query_expander,
            evidence_ranker=self.evidence_ranker,
            llm_client=self.llm_client
        )

    def test_ask_basic_flow(self):
        # Mock dependencies
        self.query_expander.expand_query.return_value = {
            'search_query': 'expanded query',
            'expanded_terms': ['term1'],
            'matched_concepts': []
        }
        
        mock_chunk = MagicMock()
        mock_chunk.text = "This is a test chunk content."
        mock_chunk.score = 0.9
        mock_chunk.metadata = {'file_path': 'test.pdf', 'file_name': 'test.pdf'}
        
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_chunk]
        self.rag_system.index.as_retriever.return_value = mock_retriever
        
        self.rag_system.metadata_storage.get_metadata.return_value = {
            'title': 'Test Title',
            'journal': 'Test Journal',
            'year': '2023',
            'authors': ['Author A'],
            'doi': '10.1234/test'
        }
        
        # rank_papers should return the list of references passed to it, possibly modified
        # The service calls rank_papers with references_raw
        def mock_rank_papers(refs):
            for ref in refs:
                ref['total_score'] = 5.0
                ref['evidence_level'] = 1
                ref['evidence_label'] = 'High'
            return refs
            
        self.evidence_ranker.rank_papers.side_effect = mock_rank_papers
        
        self.llm_client.chat.return_value = ("This is the answer [ref_1].", None)
        
        # Call ask
        result = self.chat_service.ask("test question")
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['answer'], "This is the answer [ref_1].")
        self.assertEqual(len(result['references']), 1)
        self.assertEqual(result['references'][0]['ref_id'], 'ref_1')
        
        # Verify interactions
        self.query_expander.expand_query.assert_called_with("test question")
        mock_retriever.retrieve.assert_called_with('expanded query')
        self.llm_client.chat.assert_called()

    def test_ask_no_results(self):
        self.query_expander.expand_query.return_value = {
            'search_query': 'query',
            'expanded_terms': [],
            'matched_concepts': []
        }
        
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        self.rag_system.index.as_retriever.return_value = mock_retriever
        
        result = self.chat_service.ask("test question")
        
        self.assertTrue(result['success'])
        self.assertIn("未检索到相关文献", result['answer'])
        self.assertEqual(len(result['references']), 0)

if __name__ == '__main__':
    unittest.main()
