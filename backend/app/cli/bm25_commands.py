"""
BM25 CLI Commands

Command-line interface for BM25 index management.
"""
import click
import logging
from app.db.database import SessionLocal
from app.services.bm25_search_service import BM25SearchService
from app.config.bm25_config import bm25_config

logger = logging.getLogger(__name__)


@click.group()
def bm25():
    """BM25 index management commands"""
    pass


@bm25.command()
def rebuild():
    """Rebuild BM25 index from all document chunks"""
    click.echo("Rebuilding BM25 index...")
    
    db = SessionLocal()
    try:
        service = BM25SearchService(db)
        result = service.rebuild_index()
        
        if result.get("success"):
            click.echo(f"✅ Index rebuilt successfully")
            click.echo(f"   Chunk count: {result.get('chunk_count')}")
            click.echo(f"   Build time: {result.get('build_time_seconds'):.2f}s")
            click.echo(f"   Cache path: {result.get('cache_path')}")
        else:
            click.echo(f"❌ Failed to rebuild index: {result.get('error')}", err=True)
            raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    finally:
        db.close()


@bm25.command()
def stats():
    """Show BM25 index statistics"""
    db = SessionLocal()
    try:
        service = BM25SearchService(db)
        stats = service.get_index_stats()
        
        click.echo("BM25 Index Statistics")
        click.echo("=" * 50)
        click.echo(f"Index built: {'✅ Yes' if stats.get('index_built') else '❌ No'}")
        click.echo(f"Chunk count: {stats.get('chunk_count')}")
        click.echo(f"Built at: {stats.get('built_at') or 'N/A'}")
        click.echo(f"Version: {stats.get('version')}")
        click.echo(f"Cache exists: {'✅ Yes' if stats.get('cache_exists') else '❌ No'}")
        click.echo(f"Cache path: {stats.get('cache_path')}")
        click.echo(f"Cache size: {stats.get('cache_size_mb')} MB")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    finally:
        db.close()


@bm25.command()
def clear_cache():
    """Clear cached BM25 index from disk"""
    if not click.confirm("Are you sure you want to clear the BM25 cache?"):
        click.echo("Cancelled")
        return
    
    db = SessionLocal()
    try:
        service = BM25SearchService(db)
        if service.clear_cache():
            click.echo("✅ Cache cleared successfully")
        else:
            click.echo("⚠️  No cache to clear")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    finally:
        db.close()


@bm25.command()
@click.argument('query')
@click.option('--top-k', default=10, help='Number of results to return')
@click.option('--property-id', type=int, help='Filter by property ID')
@click.option('--document-type', help='Filter by document type')
def search(query, top_k, property_id, document_type):
    """Search document chunks using BM25"""
    db = SessionLocal()
    try:
        service = BM25SearchService(db)
        results = service.search(
            query=query,
            top_k=top_k,
            property_id=property_id,
            document_type=document_type
        )
        
        click.echo(f"BM25 Search Results for: '{query}'")
        click.echo("=" * 50)
        
        if not results:
            click.echo("No results found")
            return
        
        for i, result in enumerate(results, 1):
            click.echo(f"\n{i}. Score: {result['score']:.4f}")
            click.echo(f"   Chunk ID: {result['chunk_id']}")
            click.echo(f"   Property ID: {result.get('property_id')}")
            click.echo(f"   Document Type: {result.get('document_type')}")
            click.echo(f"   Text: {result['chunk_text'][:200]}...")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    finally:
        db.close()


if __name__ == '__main__':
    bm25()

