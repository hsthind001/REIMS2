/**
 * Inline Citation Component
 * 
 * Displays citations inline with answer text.
 * Clickable citations that show source information on hover.
 */
import React, { useState } from 'react';
import { Box, Typography, Tooltip, Popover, Chip, IconButton } from '@mui/material';
import { Description, TableChart, OpenInNew } from '@mui/icons-material';

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

interface InlineCitationProps {
  text: string;
  citations: Array<{
    claim: string;
    sources: CitationSource[];
    confidence: number;
  }>;
  onSourceClick?: (source: CitationSource) => void;
}

export const InlineCitation: React.FC<InlineCitationProps> = ({
  text,
  citations,
  onSourceClick
}) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<CitationSource[] | null>(null);

  const handleCitationClick = (event: React.MouseEvent<HTMLElement>, sources: CitationSource[]) => {
    setAnchorEl(event.currentTarget);
    setSelectedCitation(sources);
  };

  const handleClose = () => {
    setAnchorEl(null);
    setSelectedCitation(null);
  };

  const formatTextWithCitations = () => {
    if (!citations || citations.length === 0) {
      return <Typography>{text}</Typography>;
    }

    // Find all citations in text and create segments
    const segments: Array<{ text: string; isCitation: boolean; sources?: CitationSource[] }> = [];
    let lastIndex = 0;

    citations.forEach((citation) => {
      const claimIndex = text.indexOf(citation.claim);
      if (claimIndex !== -1) {
        // Add text before citation
        if (claimIndex > lastIndex) {
          segments.push({ text: text.substring(lastIndex, claimIndex), isCitation: false });
        }
        
        // Add citation
        segments.push({
          text: citation.claim,
          isCitation: true,
          sources: citation.sources
        });
        
        lastIndex = claimIndex + citation.claim.length;
      }
    });

    // Add remaining text
    if (lastIndex < text.length) {
      segments.push({ text: text.substring(lastIndex), isCitation: false });
    }

    return (
      <Typography component="span">
        {segments.map((segment, index) => {
          if (segment.isCitation && segment.sources) {
            return (
              <React.Fragment key={index}>
                <Typography
                  component="span"
                  sx={{
                    color: 'primary.main',
                    textDecoration: 'underline',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'action.hover'
                    }
                  }}
                  onClick={(e) => handleCitationClick(e, segment.sources!)}
                >
                  {segment.text}
                </Typography>
                <Chip
                  label={`[${segment.sources.length}]`}
                  size="small"
                  sx={{
                    ml: 0.5,
                    height: 18,
                    fontSize: '0.7rem',
                    cursor: 'pointer'
                  }}
                  onClick={(e) => handleCitationClick(e, segment.sources!)}
                />
              </React.Fragment>
            );
          }
          return <span key={index}>{segment.text}</span>;
        })}
      </Typography>
    );
  };

  const formatSourceLabel = (source: CitationSource): string => {
    if (source.type === 'document') {
      const parts: string[] = [];
      
      if (source.document_type) {
        const docType = source.document_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        parts.push(docType);
      }
      
      if (source.page) {
        parts.push(`Page ${source.page}`);
      }
      
      if (source.line) {
        parts.push(`Line ${source.line}`);
      }
      
      return parts.join(', ') || 'Document';
    } else if (source.type === 'sql') {
      return 'Database Query';
    }
    
    return 'Source';
  };

  return (
    <Box>
      {formatTextWithCitations()}
      
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left'
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left'
        }}
      >
        <Box sx={{ p: 2, maxWidth: 400 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            Sources
          </Typography>
          
          {selectedCitation?.map((source, index) => (
            <Box
              key={index}
              sx={{
                mb: 1,
                p: 1,
                backgroundColor: 'action.hover',
                borderRadius: 0.5,
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}
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
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
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
                      fontSize: '0.7rem'
                    }}
                  >
                    "{source.excerpt}"
                  </Typography>
                )}
              </Box>
              
              <IconButton
                size="small"
                onClick={() => {
                  if (onSourceClick) {
                    onSourceClick(source);
                  }
                  handleClose();
                }}
              >
                <OpenInNew fontSize="small" />
              </IconButton>
            </Box>
          ))}
        </Box>
      </Popover>
    </Box>
  );
};

export default InlineCitation;

