import unittest
import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compound_service import CompoundService

class TestCompoundService(unittest.TestCase):
    def setUp(self):
        # Create a temporary test Excel file
        self.test_file = 'data/test_compounds.xlsx'
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        data = {
            'Compound Name': ['TestSweetener', 'Sugar', 'DuplicateSweetener', 'DuplicateSweetener'],
            'PubChem CID': [123, 456, 789, 789],
            'Relative_Sweetness': [100, 1.0, 50, 50],
            'MolecularWeight': [300.5, 342.3, 150.0, 150.0],
            # Add other required columns with dummy values or handle missing gracefully
            'MolecularFormula': ['C10H20O5', 'C12H22O11', 'C5H10O5', 'C5H10O5']
        }
        df = pd.DataFrame(data)
        df.to_excel(self.test_file, index=False)
        
        self.service = CompoundService(data_path=self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_load_data_mapping(self):
        """Test column mapping and loading"""
        # Mapping should convert 'Compound Name' to 'name', 'PubChem CID' to 'cid', etc.
        self.assertIn('name', self.service._df.columns)
        self.assertIn('cid', self.service._df.columns)
        self.assertIn('sweetness', self.service._df.columns)
        # Duplicate with same CID (789) should be removed, so 4 rows -> 3 unique
        self.assertEqual(len(self.service._df), 3)

    def test_deduplication(self):
        """Test duplicate removal based on CID"""
        # We added 2 rows with CID 789, expecting 1 in the loaded dataframe
        cids = self.service._df['cid'].tolist()
        self.assertEqual(cids.count(789), 1)

    def test_numeric_conversion(self):
        """Test numeric columns are converted"""
        # Sweetness and CID should be numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(self.service._df['sweetness']))
        self.assertTrue(pd.api.types.is_numeric_dtype(self.service._df['cid']))

    def test_search_exact(self):
        """Test exact search"""
        results = self.service.search("Sugar")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['name'], 'Sugar')

    def test_search_fuzzy(self):
        """Test fuzzy search"""
        results = self.service.search("Sugr")  # Typo
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['name'], 'Sugar')
        # Expect a reasonable match score
        self.assertTrue(results[0]['match_score'] > 60)

    def test_get_by_id(self):
        """Test get by ID (CID)"""
        # Since 'id' is mapped from 'cid' if 'id' is missing
        # The service logic: if 'id' not in columns, copy 'cid' to 'id'
        # So we can search by 123 (which is the CID)
        item = self.service.get_by_id(123)
        self.assertIsNotNone(item)
        self.assertEqual(item['name'], 'TestSweetener')

    def test_get_stats(self):
        """Test stats"""
        stats = self.service.get_stats()
        self.assertEqual(stats['total_count'], 3)

if __name__ == '__main__':
    unittest.main()
