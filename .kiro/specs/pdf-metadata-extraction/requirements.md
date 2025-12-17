# Requirements Document

## Introduction

本文档定义了PDF文献元数据提取和优化显示功能的需求。该功能旨在改进当前参考文献（Reference）面板的显示效果，通过提取PDF文献的元数据（期刊、年份、标题、作者、DOI）并以简洁的格式展示，同时提供悬停交互显示详细信息。

## Glossary

- **System**: SweetSeek RAG系统
- **PDF Metadata**: PDF文献的元数据，包括期刊名、发表年份、标题、作者列表、DOI
- **Reference Panel**: 网页右侧显示参考文献的面板
- **Hover Tooltip**: 鼠标悬停时显示的详细信息弹窗
- **Reference Identifier**: 参考文献标识符，格式为 [ref_N 期刊名 年份]

## Requirements

### Requirement 1

**User Story:** 作为用户，我希望系统能够自动提取PDF文献的元数据，以便我能看到规范的文献引用信息。

#### Acceptance Criteria

1. WHEN the system processes a PDF file THEN the system SHALL extract the journal name from the PDF metadata or content
2. WHEN the system processes a PDF file THEN the system SHALL extract the publication year from the PDF metadata or content
3. WHEN the system processes a PDF file THEN the system SHALL extract the title from the PDF metadata or content
4. WHEN the system processes a PDF file THEN the system SHALL extract the authors list from the PDF metadata or content
5. WHEN the system processes a PDF file THEN the system SHALL extract the DOI from the PDF metadata or content
6. WHEN metadata extraction fails for any field THEN the system SHALL use a default placeholder value

### Requirement 2

**User Story:** 作为用户，我希望参考文献面板以简洁的格式显示文献引用，以便我能快速浏览相关文献。

#### Acceptance Criteria

1. WHEN the system displays references THEN the system SHALL show each reference in the format [ref_N 期刊名 年份]
2. WHEN multiple references are displayed THEN the system SHALL number them sequentially starting from ref_1
3. WHEN the reference identifier is displayed THEN the system SHALL use a distinct visual style (color, font weight)
4. WHEN the datasets file is referenced THEN the system SHALL display it with identifier [ref_N 营养数据集 N/A]
5. WHEN references are displayed THEN the system SHALL maintain the retrieval order from the RAG system

### Requirement 3

**User Story:** 作为用户，我希望鼠标悬停在参考文献标识符上时能看到详细信息，以便我了解文献的完整信息。

#### Acceptance Criteria

1. WHEN the user hovers over a reference identifier THEN the system SHALL display a tooltip with detailed information
2. WHEN the tooltip is displayed THEN the system SHALL show the full title
3. WHEN the tooltip is displayed THEN the system SHALL show the complete authors list
4. WHEN the tooltip is displayed THEN the system SHALL show the DOI with a clickable link format
5. WHEN the tooltip is displayed THEN the system SHALL show the publication year
6. WHEN the user moves the mouse away THEN the system SHALL hide the tooltip with a smooth animation
7. WHEN the tooltip appears THEN the system SHALL use a fade-in animation effect

### Requirement 4

**User Story:** 作为用户，我希望系统能够持久化存储提取的元数据，以便避免重复提取和提高性能。

#### Acceptance Criteria

1. WHEN metadata is extracted from a PDF THEN the system SHALL store the metadata in a persistent storage
2. WHEN the system needs metadata for a previously processed PDF THEN the system SHALL retrieve it from storage instead of re-extracting
3. WHEN a PDF file is updated or replaced THEN the system SHALL re-extract and update the metadata
4. WHEN the system stores metadata THEN the system SHALL associate it with the file path and filename

### Requirement 5

**User Story:** 作为用户，我希望参考文献面板的UI设计简洁美观，以便获得良好的视觉体验。

#### Acceptance Criteria

1. WHEN references are displayed THEN the system SHALL use consistent spacing between reference items
2. WHEN the reference identifier is displayed THEN the system SHALL use the primary blue color (#2563eb)
3. WHEN the tooltip is displayed THEN the system SHALL position it near the reference identifier without overlapping
4. WHEN the tooltip is displayed THEN the system SHALL use a white background with shadow for visual hierarchy
5. WHEN multiple references are shown THEN the system SHALL maintain visual consistency across all items

### Requirement 6

**User Story:** 作为开发者，我希望元数据提取功能具有良好的错误处理能力，以便系统在遇到问题时能够优雅降级。

#### Acceptance Criteria

1. WHEN PDF metadata extraction fails THEN the system SHALL log the error with file information
2. WHEN a required metadata field is missing THEN the system SHALL use a default value (e.g., "Unknown Journal")
3. WHEN the DOI is not found THEN the system SHALL display "DOI: Not Available"
4. WHEN authors list is too long THEN the system SHALL truncate it with "et al." after the first 3 authors
5. WHEN metadata extraction encounters an exception THEN the system SHALL continue processing other files

### Requirement 7

**User Story:** 作为用户，我希望在问答回答中也能看到简洁的文献引用标识，以便知道信息来源。

#### Acceptance Criteria

1. WHEN the AI generates an answer THEN the system SHALL include reference identifiers in the answer text where appropriate
2. WHEN a reference identifier is mentioned in the answer THEN the system SHALL use the same format [ref_N 期刊名 年份]
3. WHEN the user clicks on a reference identifier in the answer THEN the system SHALL highlight the corresponding reference in the panel
4. WHEN references are cited in the answer THEN the system SHALL ensure the identifiers match those in the reference panel
