# Implementation Plan

- [x] 1. Create PDF metadata extraction module
  - Create `pdf_metadata_extractor.py` with PDFMetadataExtractor class
  - Implement `extract_metadata()` method to extract journal, year, title, authors, DOI
  - Implement `extract_from_pdf_metadata()` to read PDF metadata fields
  - Implement `extract_from_first_page()` to parse first page text
  - Add regex patterns for DOI, year, and journal name matching
  - Handle extraction failures with default values
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 6.2, 6.3, 6.4, 6.5_

- [x] 2. Create metadata storage manager
  - Create `metadata_storage.py` with MetadataStorage class
  - Implement `save_metadata()` to persist metadata to JSON file
  - Implement `get_metadata()` to retrieve metadata by file path
  - Implement `get_all_metadata()` to retrieve all stored metadata
  - Implement `update_metadata()` to update existing metadata
  - Create storage directory if not exists
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 3. Integrate metadata extraction into RAG system
  - Modify `persistent_storage.py` to initialize MetadataStorage and PDFMetadataExtractor
  - Update `_build_new_index()` to extract metadata during indexing
  - Extract metadata for each PDF document
  - Save extracted metadata to storage
  - Add logging for metadata extraction process
  - _Requirements: 1.1-1.6, 4.1, 6.1_

- [x] 4. Enhance API response with metadata
  - Modify `/api/ask` endpoint in `app.py`
  - Retrieve metadata for each reference from storage
  - Build enhanced references array with ref_id, journal, year, title, authors, DOI
  - Format authors list (truncate with "et al." if more than 3)
  - Handle missing metadata gracefully
  - _Requirements: 2.1, 2.2, 2.5, 6.2, 6.4_

- [x] 5. Update frontend to display compact references
  - Modify `displayReferences()` function in `static/main.js`
  - Display references in format [ref_N: Journal Year]
  - Create reference items with data attributes for tooltip
  - Add event listeners for mouse hover
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. Implement tooltip functionality
  - Add `showRefTooltip()` function in `static/main.js`
  - Add `hideRefTooltip()` function in `static/main.js`
  - Add `formatAuthors()` helper function
  - Create tooltip HTML structure with title, authors, year, DOI
  - Make DOI clickable with proper link format
  - Position tooltip near reference identifier
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 7. Add CSS styling for compact references and tooltips
  - Add `.reference-item-compact` styles in `static/style.css`
  - Add `.ref-identifier` styles with hover effects
  - Add `.ref-tooltip` styles with positioning and shadow
  - Add `.tooltip-content` styles for text formatting
  - Add fade-in/fade-out animation for tooltip
  - Add hover transform effect for reference identifier
  - Ensure responsive design for different screen sizes
  - _Requirements: 3.7, 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Handle special case for datasets file
  - Detect when reference is from datasets folder
  - Display datasets reference as [ref_N: 营养数据集 N/A]
  - Create appropriate metadata for datasets file
  - _Requirements: 2.4_

- [x] 9. Add error handling and logging
  - Add try-catch blocks in metadata extraction
  - Log extraction errors with file information
  - Use default values for missing fields
  - Add error handling in frontend tooltip display
  - Ensure UI doesn't break on metadata errors
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 10. Test and validate the implementation
  - Test metadata extraction with all 7 PDF files
  - Verify metadata.json is created and populated
  - Test API response includes correct metadata
  - Test frontend displays compact references correctly
  - Test tooltip shows and hides properly on hover
  - Test with missing or incomplete metadata
  - Verify DOI links work correctly
  - _Requirements: All_

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
