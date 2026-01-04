import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DocumentUpload } from '../DocumentUpload';

// Mock the API module
vi.mock('../../lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  }
}));

describe('DocumentUpload Component', () => {
  it('should render without crashing', () => {
    render(<DocumentUpload />);
    expect(screen.getByText(/upload/i)).toBeInTheDocument();
  });

  it('should have a file input element', () => {
    render(<DocumentUpload />);
    const fileInput = screen.getByLabelText(/file/i) || screen.getByRole('button', { name: /upload/i });
    expect(fileInput).toBeInTheDocument();
  });
});
