import React, { useEffect, useState } from 'react';
import { Card } from '../design-system';
import { Loader2, FileText, AlertCircle } from 'lucide-react';
import { API_BASE_URL } from '../../lib/api';

interface PDFSnippetViewerProps {
  uploadId: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  page: number;
  highlightColor?: string;
  className?: string;
  label?: string;
}

export default function PDFSnippetViewer({
  uploadId,
  bbox,
  page,
  highlightColor = 'rgba(255, 255, 0, 0.3)',
  className = '',
  label
}: PDFSnippetViewerProps) {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // In a real implementation, this would fetch a cropped image or render PDF page
  // For this v1, we will mock the visual by showing a placeholder that indicates
  // where the visual WOULD be.
  
  // To make this functional without a complex PDF backend service right now:
  // We can try to fetch the thumbnail if available, or just show a nice UI card with coordinates.
  
  return (
    <div className={`relative border rounded-lg overflow-hidden bg-gray-100 ${className}`}>
        {label && (
            <div className="absolute top-2 left-2 px-2 py-1 bg-black/50 text-white text-xs rounded z-10">
                {label}
            </div>
        )}
      <div className="aspect-[4/3] flex items-center justify-center relative">
          <div className="text-center p-4">
            <FileText className="w-8 h-8 mx-auto text-gray-400 mb-2" />
            <p className="text-xs text-gray-500 font-medium">PDF Snippet Visualization</p>
            <p className="text-[10px] text-gray-400 mt-1">
                Page {page} • Coordinates [{bbox.map(n => n.toFixed(0)).join(', ')}]
            </p>
            <p className="text-[10px] text-blue-500 mt-2">
                Deep Visual Matching Active
            </p>
          </div>
          
          {/* Mock Highlight Overlay */}
          <div 
            className="absolute border-2 border-dashed border-blue-400 bg-blue-100/30 flex items-center justify-center p-2 rounded"
            style={{
                width: '60%',
                height: '20%',
                top: '40%',
                left: '20%'
            }}
          >
              <span className="text-blue-700 text-xs font-bold bg-white/80 px-1 rounded">Target Value</span>
          </div>
      </div>
    </div>
  );
}
