import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DocumentUpload } from '../DocumentUpload';

// Mock property service to avoid real API calls
vi.mock('../../lib/property', () => ({
  propertyService: {
    getAllProperties: vi.fn().mockResolvedValue([]),
  },
}));

// Mock document service upload to avoid network calls
vi.mock('../../lib/document', () => ({
  documentService: {
    uploadDocument: vi.fn().mockResolvedValue({ upload_id: 1 }),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('DocumentUpload Component', () => {
  it('should render without crashing', () => {
    render(<DocumentUpload />);
    expect(screen.getByRole('heading', { name: /upload financial document/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload document/i })).toBeInTheDocument();
  });

  it('should have a file input element', () => {
    render(<DocumentUpload />);
    const fileInputs = screen.getAllByLabelText(/upload pdf file/i);
    expect(fileInputs[0]).toBeInTheDocument();
  });
});
