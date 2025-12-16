/**
 * Citation Component
 * 
 * Displays granular citations for claims in NLQ answers.
 * Provides clickable citations that jump to source documents.
 */
import React from 'react';
import { Box, Typography, Chip, Tooltip, IconButton, Link } from '@mui/material';
import { OpenInNew, Description, TableChart } from '@mui/icons-material';

interface CitationSource {
  type: 'document' | 'sql';
  document_type?: string;
  document_id?: number;
  chunk_id?: number;
  file_name?: string;
  page?: number;
  line?: number;
  coordinates?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
  excerpt?: string;
  confidence?: number;
  query?: string;
  value?: number;
}

interface Citation {
  claim: string;
  sources: CitationSource[];
  confidence: number;
  type: string;
}

interface CitationProps {
  citation: Citation;
  onSourceClick?: (source: CitationSource) => void;
  compact?: boolean;
}

export const CitationComponent: React.FC<CitationProps> = ({
  citation,
  onSourceClick,
  compact = false
}) => {
  const handleSourceClick = (source: CitationSource) => {
    if (onSourceClick) {
      onSourceClick(source);
    } else {
      // Default: open document viewer or scroll to source
      if (source.type === 'document' && source.document_id) {
        // Navigate to document viewer
        window.open(`/documents/${source.document_id}?page=${source.page || 1}`, '_blank');
      }
    }
  };

  const formatSourceLabel = (source: CitationSource): string => {
    if (source.type === 'document') {
      const parts: string[] = [];
      
      // Document type
      if (source.document_type) {
        const docType = source.document_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        parts.push(docType);
      }
      
      // Page number
      if (source.page) {
        parts.push(`Page ${source.page}`);
      }
      
      // Line number
      if (source.line) {
        parts.push(`Line ${source.line}`);
      }
      
      return parts.join(', ') || 'Document';
    } else if (source.type === 'sql') {
      return 'Database Query';
    }
    
    return 'Source';
  };

  if (compact) {
    return (
      <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, ml: 1 }}>
        {citation.sources.map((source, index) => (
          <Tooltip
            key={index}
            title={`${formatSourceLabel(source)}${source.file_name ? ` - ${source.file_name}` : ''}`}
            arrow
          >
            <Chip
              label={`[${index + 1}]`}
              size="small"
              icon={source.type === 'document' ? <Description fontSize="small" /> : <TableChart fontSize="small" />}
              onClick={() => handleSourceClick(source)}
              sx={{
                cursor: 'pointer',
                '&:hover': {
                  backgroundColor: 'primary.light',
                  color: 'primary.contrastText'
                }
              }}
            />
          </Tooltip>
        ))}
      </Box>
    );
  }

  return (
    <Box
      sx={{
        mt: 1,
        p: 1.5,
        backgroundColor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        '&:hover': {
          borderColor: 'primary.main',
          boxShadow: 1
        }
      }}
    >
      <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
        {citation.claim}
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {citation.sources.map((source, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              p: 1,
              backgroundColor: 'action.hover',
              borderRadius: 0.5,
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: 'action.selected'
              }
            }}
            onClick={() => handleSourceClick(source)}
          >
            {source.type === 'document' ? (
              <Description fontSize="small" color="primary" />
            ) : (
              <TableChart fontSize="small" color="primary" />
            )}
            
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" sx={{ fontWeight: 500 }}>
                {formatSourceLabel(source)}
              </Typography>
              
              {source.file_name && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                  {source.file_name}
                </Typography>
              )}
              
              {source.excerpt && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{
                    display: 'block',
                    mt: 0.5,
                    fontStyle: 'italic',
                    maxWidth: '100%',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}
                >
                  "{source.excerpt}"
                </Typography>
              )}
            </Box>
            
            {source.confidence && (
              <Chip
                label={`${Math.round(source.confidence * 100)}%`}
                size="small"
                color={source.confidence >= 0.9 ? 'success' : source.confidence >= 0.7 ? 'warning' : 'error'}
                sx={{ minWidth: 50 }}
              />
            )}
            
            <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleSourceClick(source); }}>
              <OpenInNew fontSize="small" />
            </IconButton>
          </Box>
        ))}
      </Box>
      
      {citation.confidence && (
        <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-end' }}>
          <Typography variant="caption" color="text.secondary">
            Overall Confidence: {Math.round(citation.confidence * 100)}%
          </Typography>
        </Box>
      )}
    </Box>
  );
};

interface CitationListProps {
  citations: Citation[];
  onSourceClick?: (source: CitationSource) => void;
  compact?: boolean;
}

export const CitationList: React.FC<CitationListProps> = ({
  citations,
  onSourceClick,
  compact = false
}) => {
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
        Citations
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {citations.map((citation, index) => (
          <CitationComponent
            key={index}
            citation={citation}
            onSourceClick={onSourceClick}
            compact={compact}
          />
        ))}
      </Box>
    </Box>
  );
};

export default CitationComponent;

