import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App Component', () => {
  it('should render the main application', () => {
    render(<App />);
    // Check that the app renders without crashing
    expect(document.body).toBeTruthy();
  });

  it('should contain main application structure', () => {
    const { container } = render(<App />);
    expect(container.firstChild).toBeTruthy();
  });
});

