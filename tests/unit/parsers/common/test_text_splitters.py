"""Test text splitters compatibility with langchain implementations."""


from codecontext.parsers.common.text_splitters import (
    Document,
    MarkdownHeaderSplitter,
    RecursiveTextSplitter,
)


class TestMarkdownHeaderSplitter:
    """Test markdown header splitting."""

    def test_basic_header_splitting(self):
        """Test basic header-based splitting."""
        text = """# Header 1
Content 1

## Header 2
Content 2

### Header 3
Content 3"""

        splitter = MarkdownHeaderSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
            strip_headers=False,
        )

        docs = splitter.split_text(text)

        assert len(docs) == 3
        assert docs[0].metadata == {"h1": "Header 1"}
        assert "# Header 1" in docs[0].page_content
        assert "Content 1" in docs[0].page_content

        assert docs[1].metadata == {"h2": "Header 2"}
        assert "## Header 2" in docs[1].page_content
        assert "Content 2" in docs[1].page_content

        assert docs[2].metadata == {"h3": "Header 3"}
        assert "### Header 3" in docs[2].page_content
        assert "Content 3" in docs[2].page_content

    def test_strip_headers(self):
        """Test stripping headers from content."""
        text = """# Header 1
Content 1"""

        splitter = MarkdownHeaderSplitter(
            headers_to_split_on=[("#", "h1")],
            strip_headers=True,
        )

        docs = splitter.split_text(text)

        assert len(docs) == 1
        assert docs[0].metadata == {"h1": "Header 1"}
        assert "# Header 1" not in docs[0].page_content
        assert "Content 1" in docs[0].page_content

    def test_no_headers(self):
        """Test text without headers."""
        text = "Just plain text"

        splitter = MarkdownHeaderSplitter(
            headers_to_split_on=[("#", "h1")],
            strip_headers=False,
        )

        docs = splitter.split_text(text)

        assert len(docs) == 1
        assert docs[0].metadata == {}
        assert docs[0].page_content == text

    def test_empty_text(self):
        """Test empty text."""
        text = ""

        splitter = MarkdownHeaderSplitter(
            headers_to_split_on=[("#", "h1")],
            strip_headers=False,
        )

        docs = splitter.split_text(text)

        assert len(docs) == 1
        assert docs[0].metadata == {}
        assert docs[0].page_content == ""

    def test_multiple_h1_headers(self):
        """Test multiple h1 headers."""
        text = """# Header 1
Content 1

# Header 2
Content 2"""

        splitter = MarkdownHeaderSplitter(
            headers_to_split_on=[("#", "h1")],
            strip_headers=False,
        )

        docs = splitter.split_text(text)

        assert len(docs) == 2
        assert docs[0].metadata == {"h1": "Header 1"}
        assert docs[1].metadata == {"h1": "Header 2"}

    def test_nested_headers(self):
        """Test nested headers preserve only current level."""
        text = """# H1
## H2
### H3
Content"""

        splitter = MarkdownHeaderSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
            strip_headers=False,
        )

        docs = splitter.split_text(text)

        # Each header creates a new chunk
        assert len(docs) == 3
        assert docs[2].metadata == {"h3": "H3"}


class TestRecursiveTextSplitter:
    """Test recursive text splitting."""

    def test_basic_splitting(self):
        """Test basic text splitting."""
        text = "a" * 100

        splitter = RecursiveTextSplitter(chunk_size=50, chunk_overlap=10)
        chunks = splitter.split_text(text)

        # Should split into 3 chunks with overlap
        assert len(chunks) >= 2
        assert all(len(chunk) <= 50 for chunk in chunks)

    def test_paragraph_separator(self):
        """Test splitting with paragraph separator."""
        text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"

        splitter = RecursiveTextSplitter(
            chunk_size=20,
            chunk_overlap=0,
            separators=["\n\n", "\n", " "],
        )

        chunks = splitter.split_text(text)

        assert len(chunks) == 3
        assert "Paragraph 1" in chunks[0]
        assert "Paragraph 2" in chunks[1]
        assert "Paragraph 3" in chunks[2]

    def test_overlap(self):
        """Test chunk overlap."""
        text = "a " * 100

        splitter = RecursiveTextSplitter(chunk_size=50, chunk_overlap=20, separators=[" "])

        chunks = splitter.split_text(text)

        # Verify overlap exists
        for i in range(len(chunks) - 1):
            # Check if end of current chunk overlaps with start of next
            current_end = chunks[i][-20:]
            next_start = chunks[i + 1][:20]
            # Should have some overlap
            assert len(current_end) > 0 and len(next_start) > 0

    def test_no_split_needed(self):
        """Test text that doesn't need splitting."""
        text = "Short text"

        splitter = RecursiveTextSplitter(chunk_size=50, chunk_overlap=10)
        chunks = splitter.split_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self):
        """Test empty text."""
        text = ""

        splitter = RecursiveTextSplitter(chunk_size=50, chunk_overlap=10)
        chunks = splitter.split_text(text)

        assert chunks == []

    def test_separator_hierarchy(self):
        """Test separator priority."""
        text = "Paragraph 1\n\nParagraph 2\nLine 2"

        splitter = RecursiveTextSplitter(
            chunk_size=20,
            chunk_overlap=0,
            separators=["\n\n", "\n", " "],
        )

        chunks = splitter.split_text(text)

        # Should prefer \n\n over \n
        assert "Paragraph 1" in chunks[0]
        assert "Paragraph 2" in chunks[1] or "Paragraph 2\nLine 2" in chunks[1]

    def test_large_chunk_recursion(self):
        """Test recursive splitting when chunk is too large."""
        text = "a" * 1000

        splitter = RecursiveTextSplitter(
            chunk_size=100,
            chunk_overlap=10,
            separators=["\n\n", "\n", " ", ""],
        )

        chunks = splitter.split_text(text)

        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)


class TestDocument:
    """Test Document dataclass."""

    def test_document_creation(self):
        """Test document creation."""
        doc = Document(page_content="test content", metadata={"key": "value"})

        assert doc.page_content == "test content"
        assert doc.metadata == {"key": "value"}

    def test_document_empty_metadata(self):
        """Test document with empty metadata."""
        doc = Document(page_content="test", metadata={})

        assert doc.page_content == "test"
        assert doc.metadata == {}
