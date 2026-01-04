/**
 * Anomaly Comparison View Component
 * 
 * Side-by-side PDF comparison with extracted vs expected values
 */

import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { CheckCircle, XCircle, FileText, AlertCircle } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

// Set up PDF.js worker
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;
}

interface AnomalyComparisonViewProps {
  anomalyId: number;
  extractedValue: number | string;
  expectedValue: number | string;
  pdfUrl?: string;
  coordinates?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    page_number: number;
  } | null;
  onAccept?: () => void;
  onCorrect?: (correctedValue: number | string) => void;
  onClose?: () => void;
}

export default function AnomalyComparisonView({
  anomalyId,
  extractedValue,
  expectedValue,
  pdfUrl,
  coordinates,
  onAccept,
  onCorrect,
  onClose,
}: AnomalyComparisonViewProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(coordinates?.page_number || 1);
  const [scale, setScale] = useState<number>(1.5);
  const [loading, setLoading] = useState<boolean>(true);
  const [correctedValue, setCorrectedValue] = useState<string>(String(extractedValue));
  const [showCorrectionInput, setShowCorrectionInput] = useState<boolean>(false);

  useEffect(() => {
    if (coordinates?.page_number) {
      setPageNumber(coordinates.page_number);
    }
  }, [coordinates]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
  };

  const handleAccept = () => {
    onAccept?.();
  };

  const handleCorrect = () => {
    if (showCorrectionInput) {
      const value = isNaN(Number(correctedValue)) 
        ? correctedValue 
        : Number(correctedValue);
      onCorrect?.(value);
    } else {
      setShowCorrectionInput(true);
    }
  };

  const variance = typeof extractedValue === 'number' && typeof expectedValue === 'number'
    ? Math.abs(extractedValue - expectedValue)
    : null;

  const variancePercent = variance && typeof expectedValue === 'number' && expectedValue !== 0
    ? ((variance / Math.abs(expectedValue)) * 100).toFixed(2)
    : null;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#fff',
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #dee2e6',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText size={20} />
          <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
            Anomaly Comparison
          </h3>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem',
              border: 'none',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              borderRadius: '4px',
            }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Content */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: pdfUrl ? '1fr 1fr' : '1fr',
        gap: '1rem',
        padding: '1rem',
        flex: 1,
        overflow: 'auto',
      }}>
        {/* Values Comparison */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}>
          <div style={{
            padding: '1rem',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            backgroundColor: '#fff3cd',
          }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: '#856404' }}>
              Extracted Value
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#856404' }}>
              {typeof extractedValue === 'number'
                ? `$${extractedValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                : extractedValue}
            </div>
          </div>

          <div style={{
            padding: '1rem',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            backgroundColor: '#d1ecf1',
          }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: '#0c5460' }}>
              Expected Value
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0c5460' }}>
              {typeof expectedValue === 'number'
                ? `$${expectedValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                : expectedValue}
            </div>
          </div>

          {variance !== null && (
            <div style={{
              padding: '1rem',
              border: '1px solid #dee2e6',
              borderRadius: '8px',
              backgroundColor: variance > 0 ? '#f8d7da' : '#d4edda',
            }}>
              <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                Variance
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                ${variance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                {variancePercent && ` (${variancePercent}%)`}
              </div>
            </div>
          )}

          {/* Correction Input */}
          {showCorrectionInput && (
            <div style={{
              padding: '1rem',
              border: '1px solid #0dcaf0',
              borderRadius: '8px',
              backgroundColor: '#e7f5ff',
            }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                Corrected Value:
              </label>
              <input
                type="text"
                value={correctedValue}
                onChange={(e) => setCorrectedValue(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #0dcaf0',
                  fontSize: '1rem',
                }}
                placeholder="Enter corrected value"
              />
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button
              onClick={handleAccept}
              style={{
                flex: 1,
                padding: '0.75rem',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: '#198754',
                color: '#fff',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
              }}
            >
              <CheckCircle size={18} />
              Accept as-is
            </button>
            <button
              onClick={handleCorrect}
              style={{
                flex: 1,
                padding: '0.75rem',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: showCorrectionInput ? '#0dcaf0' : '#fd7e14',
                color: '#fff',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
              }}
            >
              {showCorrectionInput ? (
                <>
                  <CheckCircle size={18} />
                  Confirm Correction
                </>
              ) : (
                <>
                  <XCircle size={18} />
                  Correct
                </>
              )}
            </button>
          </div>
        </div>

        {/* PDF Viewer */}
        {pdfUrl && (
          <div style={{
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            overflow: 'hidden',
            position: 'relative',
          }}>
            <div style={{
              padding: '0.5rem',
              backgroundColor: '#f8f9fa',
              borderBottom: '1px solid #dee2e6',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                PDF Reference
                {coordinates && ` - Page ${coordinates.page_number}`}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => setScale(prev => Math.max(0.5, prev - 0.25))}
                  disabled={scale <= 0.5}
                  style={{
                    padding: '0.25rem 0.5rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    backgroundColor: '#fff',
                    cursor: scale <= 0.5 ? 'not-allowed' : 'pointer',
                  }}
                >
                  −
                </button>
                <span style={{ padding: '0.25rem 0.5rem', fontSize: '0.875rem' }}>
                  {Math.round(scale * 100)}%
                </span>
                <button
                  onClick={() => setScale(prev => Math.min(3, prev + 0.25))}
                  disabled={scale >= 3}
                  style={{
                    padding: '0.25rem 0.5rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    backgroundColor: '#fff',
                    cursor: scale >= 3 ? 'not-allowed' : 'pointer',
                  }}
                >
                  +
                </button>
              </div>
            </div>
            <div style={{ padding: '1rem', overflow: 'auto', maxHeight: '600px' }}>
              {loading && (
                <div style={{ textAlign: 'center', padding: '2rem' }}>
                  <div className="spinner"></div>
                  <p>Loading PDF...</p>
                </div>
              )}
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                loading={<div style={{ textAlign: 'center', padding: '2rem' }}>Loading PDF...</div>}
              >
                <div style={{ position: 'relative', display: 'inline-block' }}>
                  <Page
                    pageNumber={pageNumber}
                    scale={scale}
                  />
                  {coordinates && (
                    <div
                      style={{
                        position: 'absolute',
                        left: `${coordinates.x0 * scale}px`,
                        top: `${coordinates.y0 * scale}px`,
                        width: `${(coordinates.x1 - coordinates.x0) * scale}px`,
                        height: `${(coordinates.y1 - coordinates.y0) * scale}px`,
                        border: '3px solid #dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.2)',
                        pointerEvents: 'none',
                      }}
                    />
                  )}
                </div>
              </Document>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
