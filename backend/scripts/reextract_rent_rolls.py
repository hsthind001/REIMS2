#!/usr/bin/env python3
"""
Re-extract Rent Roll Data Using Template v2.0

Finds all rent roll document uploads and re-extracts them using the new
comprehensive extraction logic with all 24 fields, validation, and quality scoring.
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.rent_roll_data import RentRollData
from app.services.extraction_orchestrator import ExtractionOrchestrator


def reextract_all_rent_rolls(dry_run=False):
    """
    Re-extract all rent roll uploads
    
    Args:
        dry_run: If True, only report what would be done without actually doing it
    """
    db = SessionLocal()
    
    try:
        # Find all rent roll uploads
        uploads = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'rent_roll'
        ).order_by(DocumentUpload.id).all()
        
        if not uploads:
            print("No rent roll uploads found.")
            return
        
        print(f"\nFound {len(uploads)} rent roll upload(s)")
        print("="*80)
        
        results = []
        
        for idx, upload in enumerate(uploads, 1):
            print(f"\n[{idx}/{len(uploads)}] Processing: {upload.file_name}")
            print(f"    Upload ID: {upload.id}")
            print(f"    Property ID: {upload.property_id}")
            print(f"    Period ID: {upload.period_id}")
            print(f"    Original Status: {upload.extraction_status}")
            
            # Count existing records
            existing_count = db.query(RentRollData).filter(
                RentRollData.upload_id == upload.id
            ).count()
            print(f"    Existing Records: {existing_count}")
            
            if dry_run:
                print(f"    [DRY RUN] Would delete {existing_count} existing records and re-extract")
                results.append({
                    'upload_id': upload.id,
                    'filename': upload.filename,
                    'action': 'DRY_RUN',
                    'old_count': existing_count,
                    'new_count': 0,
                    'quality_score': None
                })
                continue
            
            try:
                # Delete existing rent_roll_data records
                deleted = db.query(RentRollData).filter(
                    RentRollData.upload_id == upload.id
                ).delete()
                db.commit()
                print(f"    ✓ Deleted {deleted} existing records")
                
                # Re-extract using orchestrator
                orchestrator = ExtractionOrchestrator(db)
                result = orchestrator.extract_and_parse_document(upload.id)
                
                if result['success']:
                    records_count = result.get('records_inserted', 0)
                    print(f"    ✓ Re-extracted: {records_count} records")
                    if 'quality_score' in result:
                        print(f"    ✓ Quality Score: {result.get('quality_score', 0):.1f}%")
                    
                    results.append({
                        'upload_id': upload.id,
                        'filename': upload.file_name,
                        'action': 'SUCCESS',
                        'old_count': existing_count,
                        'new_count': result['records_inserted'],
                        'quality_score': result.get('quality_score')
                    })
                else:
                    print(f"    ✗ Extraction failed: {result.get('error')}")
                    results.append({
                        'upload_id': upload.id,
                        'filename': upload.file_name,
                        'action': 'FAILED',
                        'old_count': existing_count,
                        'new_count': 0,
                        'quality_score': None,
                        'error': result.get('error')
                    })
            
            except Exception as e:
                db.rollback()
                print(f"    ✗ Error: {str(e)}")
                results.append({
                    'upload_id': upload.id,
                    'filename': upload.file_name,
                    'action': 'ERROR',
                    'old_count': existing_count,
                    'new_count': 0,
                    'quality_score': None,
                    'error': str(e)
                })
        
        # Print summary
        print("\n" + "="*80)
        print("RE-EXTRACTION SUMMARY")
        print("="*80)
        
        success_count = sum(1 for r in results if r['action'] == 'SUCCESS')
        failed_count = sum(1 for r in results if r['action'] in ['FAILED', 'ERROR'])
        total_old = sum(r['old_count'] for r in results)
        total_new = sum(r['new_count'] for r in results)
        
        print(f"\nTotal Uploads: {len(results)}")
        print(f"  Success: {success_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total Records Deleted: {total_old}")
        print(f"  Total Records Created: {total_new}")
        
        if success_count > 0:
            avg_quality = sum(r['quality_score'] for r in results if r['quality_score']) / success_count
            print(f"  Average Quality Score: {avg_quality:.1f}%")
        
        # Detailed results
        print("\n" + "-"*80)
        print("DETAILED RESULTS")
        print("-"*80)
        
        for r in results:
            status_symbol = "✓" if r['action'] == 'SUCCESS' else ("✗" if r['action'] in ['FAILED', 'ERROR'] else "○")
            quality_str = f" (Quality: {r['quality_score']:.1f}%)" if r['quality_score'] else ""
            print(f"{status_symbol} {r['filename']}: {r['old_count']} → {r['new_count']} records{quality_str}")
            if 'error' in r:
                print(f"    Error: {r['error']}")
        
        if not dry_run:
            print("\n✅ Re-extraction complete!")
            print("\nNext steps:")
            print("1. Review the quality scores above")
            print("2. Check any failed extractions")
            print("3. Verify data in the database")
            print("4. Test the frontend to see updated data")
        else:
            print("\n[DRY RUN COMPLETE] No changes were made.")
            print("Run without --dry-run to perform actual re-extraction.")
        
        return results
    
    except Exception as e:
        db.rollback()
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-extract rent roll data using Template v2.0')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--upload-id', type=int, 
                       help='Re-extract only a specific upload ID')
    
    args = parser.parse_args()
    
    print("="*80)
    print("RENT ROLL RE-EXTRACTION - Template v2.0")
    print("="*80)
    
    if args.dry_run:
        print("\n[DRY RUN MODE] No changes will be made")
    
    if args.upload_id:
        print(f"\nRe-extracting only upload ID: {args.upload_id}")
        # TODO: Implement single upload re-extraction
        print("Single upload re-extraction not yet implemented. Use full re-extraction.")
        return
    
    reextract_all_rent_rolls(dry_run=args.dry_run)


if __name__ == '__main__':
    main()

