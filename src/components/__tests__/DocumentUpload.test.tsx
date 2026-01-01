import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DocumentUpload } from '../DocumentUpload';

vi.mock('../../lib/property', () => ({
  propertyService: {
    getAllProperties: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('../../lib/document', () => ({
  documentService: {
    uploadDocument: vi.fn(),
  },
}));

vi.mock('../../hooks/useExtractionStatus', () => ({
  useExtractionStatus: () => ({
    status: null,
    progress: 0,
    recordsLoaded: 0,
    error: null,
  }),
}));

describe('DocumentUpload Component', () => {
  it('should render without crashing', async () => {
    render(<DocumentUpload />);
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /upload financial document/i })
      ).toBeInTheDocument()
    );
  });

  it('should have a file input element', async () => {
    render(<DocumentUpload />);
    await waitFor(() => expect(screen.getByLabelText(/file upload/i)).toBeInTheDocument());
  });
});
