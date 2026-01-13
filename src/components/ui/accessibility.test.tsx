import { describe, it, expect } from 'vitest';
import { render } from '../../test/utils';
import { axe } from 'vitest-axe';
import { Button } from './Button';
import { Card } from './Card';
import { MetricCard } from './MetricCard';
import { Modal } from './Modal';
import { Input } from './Input';

describe('Accessibility Tests', () => {
  describe('Button', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(<Button>Click me</Button>);
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });

    it('should be accessible when disabled', async () => {
      const { container } = render(<Button disabled>Disabled</Button>);
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });

    it('should be accessible with aria-label', async () => {
      const { container } = render(<Button aria-label="Submit form">Submit</Button>);
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });
  });

  describe('Card', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(
        <Card>
          <h2>Card Title</h2>
          <p>Card content goes here</p>
        </Card>
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });

    it('should be accessible when interactive', async () => {
      const { container } = render(
        <Card interactive onClick={() => {}}>
          Interactive card
        </Card>
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });
  });

  describe('MetricCard', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(
        <MetricCard
          title="Total Revenue"
          value="$2.5M"
          delta={5.2}
          comparison="vs last month"
        />
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });

    it('should be accessible with all features', async () => {
      const { container } = render(
        <MetricCard
          title="Complete Metric"
          value={2500000}
          delta={5.2}
          comparison="vs last quarter"
          target={3000000}
          status="success"
        />
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });
  });

  describe('Modal', () => {
    it('should not have any accessibility violations when open', async () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });
  });

  describe('Input', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(
        <Input
          label="Email address"
          type="email"
          placeholder="Enter your email"
        />
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });

    it('should be accessible with error state', async () => {
      const { container } = render(
        <Input
          label="Username"
          error="Username is required"
        />
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });

    it('should be accessible when disabled', async () => {
      const { container } = render(
        <Input
          label="Disabled field"
          disabled
        />
      );
      const results = await axe(container);
      expect(results.violations).toHaveLength(0);
    });
  });
});
