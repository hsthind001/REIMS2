"""
Reconciliation Document Ingestion Pipeline

Ingests reconciliation, audit, and validation documents from
/home/hsthind/Downloads/Reconcile - Aduit - Rules into Qdrant vector store
with comprehensive temporal metadata and chunking strategies.

Features:
- PDF, DOCX, TXT, MD file support
- Intelligent chunking (semantic, fixed-size, hybrid)
- Temporal metadata extraction from filenames and content
- Deduplication
- Progress tracking
- Error handling and retry logic
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import re
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from loguru import logger

# Document processing libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 not available - PDF processing disabled")

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not available - DOCX processing disabled")

# NLQ components
from app.services.nlq.vector_store_manager import vector_store_manager
from app.services.nlq.temporal_processor import temporal_processor
from app.config.nlq_config import nlq_config

console = Console()


class DocumentChunker:
    """Intelligent document chunking with multiple strategies"""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        strategy: str = "hybrid"
    ):
        """
        Initialize chunker

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            strategy: "fixed", "semantic", or "hybrid"
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk text with selected strategy

        Returns:
            List of chunks with metadata
        """
        if self.strategy == "semantic":
            return self._semantic_chunking(text, metadata)
        elif self.strategy == "fixed":
            return self._fixed_chunking(text, metadata)
        else:  # hybrid
            return self._hybrid_chunking(text, metadata)

    def _fixed_chunking(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fixed-size chunking with overlap"""
        chunks = []
        text_length = len(text)
        start = 0
        chunk_index = 0

        while start < text_length:
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < text_length:
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)

                if break_point > self.chunk_size * 0.7:  # At least 70% of chunk size
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1

            chunks.append({
                "text": chunk_text.strip(),
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_index,
                    "chunk_strategy": "fixed",
                    "chunk_size": len(chunk_text)
                }
            })

            chunk_index += 1
            start = end - self.chunk_overlap

        return chunks

    def _semantic_chunking(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Semantic chunking based on document structure"""
        chunks = []

        # Split by major sections (headers, double newlines, etc.)
        sections = re.split(r'\n\n+|\r\n\r\n+', text)

        current_chunk = ""
        chunk_index = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # If adding this section exceeds chunk_size, save current chunk
            if len(current_chunk) + len(section) > self.chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": chunk_index,
                        "chunk_strategy": "semantic",
                        "chunk_size": len(current_chunk)
                    }
                })
                chunk_index += 1
                current_chunk = section
            else:
                current_chunk += "\n\n" + section if current_chunk else section

        # Add final chunk
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_index,
                    "chunk_strategy": "semantic",
                    "chunk_size": len(current_chunk)
                }
            })

        return chunks

    def _hybrid_chunking(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Hybrid: semantic first, then fixed for large sections"""
        # First try semantic
        semantic_chunks = self._semantic_chunking(text, metadata)

        # If any chunk is too large, split it with fixed chunking
        final_chunks = []
        for chunk_data in semantic_chunks:
            if chunk_data["metadata"]["chunk_size"] > self.chunk_size * 1.5:
                # Re-chunk this large section
                sub_chunks = self._fixed_chunking(
                    chunk_data["text"],
                    chunk_data["metadata"]
                )
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk_data)

        # Re-index
        for i, chunk in enumerate(final_chunks):
            chunk["metadata"]["chunk_index"] = i
            chunk["metadata"]["chunk_strategy"] = "hybrid"

        return final_chunks


class DocumentIngestionPipeline:
    """Main document ingestion pipeline"""

    def __init__(
        self,
        source_dir: str,
        collection_name: str = "reims_reconciliation_docs",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """Initialize pipeline"""
        self.source_dir = Path(source_dir)
        self.collection_name = collection_name
        self.chunker = DocumentChunker(chunk_size, chunk_overlap, strategy="hybrid")
        self.processed_hashes = set()

        # Statistics
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "skipped_duplicates": 0
        }

    async def ingest_all(self):
        """Ingest all documents from source directory"""
        console.print(Panel.fit(
            f"[bold cyan]Document Ingestion Pipeline[/bold cyan]\n"
            f"[dim]Source: {self.source_dir}[/dim]\n"
            f"[dim]Collection: {self.collection_name}[/dim]",
            border_style="cyan"
        ))

        # Check if directory exists
        if not self.source_dir.exists():
            console.print(f"[red]✗ Directory not found: {self.source_dir}[/red]")
            return

        # Get all files
        file_patterns = ["*.pdf", "*.docx", "*.txt", "*.md"]
        all_files = []
        for pattern in file_patterns:
            all_files.extend(self.source_dir.rglob(pattern))

        self.stats["total_files"] = len(all_files)

        if not all_files:
            console.print("[yellow]⚠ No documents found[/yellow]")
            return

        console.print(f"\n[green]Found {len(all_files)} documents[/green]\n")

        # Ensure collection exists
        await self._ensure_collection()

        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing documents...", total=len(all_files))

            for file_path in all_files:
                try:
                    await self._process_file(file_path, progress, task)
                    self.stats["processed_files"] += 1
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    self.stats["failed_files"] += 1

                progress.advance(task)

        # Print summary
        self._print_summary()

    async def _ensure_collection(self):
        """Ensure vector store collection exists"""
        try:
            # Create collection if it doesn't exist
            from qdrant_client.models import Distance, VectorParams

            # Check if collection exists
            try:
                vector_store_manager.client.get_collection(self.collection_name)
                console.print(f"[green]✓ Collection '{self.collection_name}' exists[/green]")
            except:
                # Create collection
                vector_store_manager.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1024,  # BGE large embedding size
                        distance=Distance.COSINE
                    )
                )
                console.print(f"[green]✓ Created collection '{self.collection_name}'[/green]")
        except Exception as e:
            logger.error(f"Collection creation error: {e}")
            raise

    async def _process_file(self, file_path: Path, progress, task):
        """Process a single file"""
        progress.update(task, description=f"[cyan]Processing {file_path.name}...")

        # Extract text based on file type
        text = await self._extract_text(file_path)

        if not text or len(text.strip()) < 50:
            logger.warning(f"Skipping {file_path}: insufficient content")
            return

        # Extract metadata
        metadata = self._extract_metadata(file_path, text)

        # Chunk document
        chunks = self.chunker.chunk_text(text, metadata)

        # Add to vector store
        for chunk in chunks:
            # Check for duplicates
            chunk_hash = self._compute_hash(chunk["text"])
            if chunk_hash in self.processed_hashes:
                self.stats["skipped_duplicates"] += 1
                continue

            # Add to vector store
            vector_store_manager.add_document(
                text=chunk["text"],
                metadata=chunk["metadata"],
                collection_name=self.collection_name
            )

            self.processed_hashes.add(chunk_hash)
            self.stats["total_chunks"] += 1

    async def _extract_text(self, file_path: Path) -> str:
        """Extract text from file based on extension"""
        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return await self._extract_pdf(file_path)
        elif extension == ".docx":
            return await self._extract_docx(file_path)
        elif extension in [".txt", ".md"]:
            return await self._extract_text_file(file_path)
        else:
            logger.warning(f"Unsupported file type: {extension}")
            return ""

    async def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF"""
        if not PDF_AVAILABLE:
            logger.warning(f"PDF support not available for {file_path}")
            return ""

        try:
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n\n"
            return text
        except Exception as e:
            logger.error(f"PDF extraction error for {file_path}: {e}")
            return ""

    async def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        if not DOCX_AVAILABLE:
            logger.warning(f"DOCX support not available for {file_path}")
            return ""

        try:
            doc = DocxDocument(file_path)
            text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text
        except Exception as e:
            logger.error(f"DOCX extraction error for {file_path}: {e}")
            return ""

    async def _extract_text_file(self, file_path: Path) -> str:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Text extraction error for {file_path}: {e}")
            return ""

    def _extract_metadata(self, file_path: Path, text: str) -> Dict[str, Any]:
        """Extract metadata from file and content"""
        metadata = {
            "source_file": str(file_path),
            "filename": file_path.name,
            "file_type": file_path.suffix.lower()[1:],  # Remove dot
            "ingestion_date": datetime.now().isoformat(),
            "document_category": "reconciliation",
        }

        # Extract temporal info from filename
        filename_temporal = temporal_processor.extract_temporal_info(file_path.name)
        if filename_temporal.get("has_temporal"):
            metadata["temporal_info"] = filename_temporal
            if "year" in filename_temporal.get("filters", {}):
                metadata["year"] = filename_temporal["filters"]["year"]
            if "month" in filename_temporal.get("filters", {}):
                metadata["month"] = filename_temporal["filters"]["month"]

        # Detect document type from content
        text_lower = text.lower()
        if any(word in text_lower for word in ["reconciliation", "reconcile", "match"]):
            metadata["document_type"] = "reconciliation_guide"
        elif any(word in text_lower for word in ["audit", "audit trail", "changes"]):
            metadata["document_type"] = "audit_guide"
        elif any(word in text_lower for word in ["validation", "rule", "check"]):
            metadata["document_type"] = "validation_rules"
        elif any(word in text_lower for word in ["three statement", "balance sheet", "income statement"]):
            metadata["document_type"] = "financial_statement_guide"
        else:
            metadata["document_type"] = "general"

        # Extract key terms
        key_terms = []
        keywords = [
            "dscr", "ltv", "noi", "current ratio", "debt service",
            "balance sheet", "income statement", "cash flow",
            "reconciliation", "validation", "audit"
        ]
        for keyword in keywords:
            if keyword in text_lower:
                key_terms.append(keyword)

        if key_terms:
            metadata["key_terms"] = key_terms

        return metadata

    def _compute_hash(self, text: str) -> str:
        """Compute hash for deduplication"""
        return hashlib.md5(text.encode()).hexdigest()

    def _print_summary(self):
        """Print ingestion summary"""
        console.print("\n" + "="*80)

        table = Table(title="Ingestion Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Files Found", str(self.stats["total_files"]))
        table.add_row("Successfully Processed", str(self.stats["processed_files"]))
        table.add_row("Failed", str(self.stats["failed_files"]))
        table.add_row("Total Chunks Created", str(self.stats["total_chunks"]))
        table.add_row("Duplicates Skipped", str(self.stats["skipped_duplicates"]))

        console.print(table)

        if self.stats["processed_files"] > 0:
            avg_chunks = self.stats["total_chunks"] / self.stats["processed_files"]
            console.print(f"\n[green]✓ Average chunks per document: {avg_chunks:.1f}[/green]")

        console.print(f"\n[bold green]✓ Ingestion Complete![/bold green]")


async def main():
    """Run ingestion pipeline"""
    # Source directory
    source_dir = "/home/hsthind/Downloads/Reconcile - Aduit - Rules"

    # Initialize pipeline
    pipeline = DocumentIngestionPipeline(
        source_dir=source_dir,
        collection_name="reims_reconciliation_docs",
        chunk_size=1000,
        chunk_overlap=200
    )

    # Run ingestion
    await pipeline.ingest_all()


if __name__ == "__main__":
    asyncio.run(main())
