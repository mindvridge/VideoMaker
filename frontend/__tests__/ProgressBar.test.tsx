import React from 'react';
import { render, screen } from '@testing-library/react';
import ProgressBar from '@/components/ProgressBar';

describe('ProgressBar Component', () => {
  describe('Rendering', () => {
    it('renders correctly with default props', () => {
      const { container } = render(
        <ProgressBar progress={50} status="Processing..." />
      );

      expect(screen.getByText('Processing...')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(container).toMatchSnapshot();
    });

    it('renders at 0% progress', () => {
      const { container } = render(
        <ProgressBar progress={0} status="Starting..." />
      );

      expect(screen.getByText('0%')).toBeInTheDocument();
      expect(container).toMatchSnapshot();
    });

    it('renders at 100% progress', () => {
      const { container } = render(
        <ProgressBar progress={100} status="Complete!" />
      );

      expect(screen.getByText('100%')).toBeInTheDocument();
      expect(container).toMatchSnapshot();
    });

    it('applies custom className', () => {
      const { container } = render(
        <ProgressBar
          progress={75}
          status="Loading..."
          className="custom-class"
        />
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  describe('Progress Bar Width', () => {
    it('has correct width style at 50%', () => {
      const { container } = render(
        <ProgressBar progress={50} status="Halfway" />
      );

      const progressBar = container.querySelector('.bg-gradient-to-r');
      expect(progressBar).toHaveStyle({ width: '50%' });
    });

    it('has correct width style at 0%', () => {
      const { container } = render(
        <ProgressBar progress={0} status="Start" />
      );

      const progressBar = container.querySelector('.bg-gradient-to-r');
      expect(progressBar).toHaveStyle({ width: '0%' });
    });

    it('has correct width style at 100%', () => {
      const { container } = render(
        <ProgressBar progress={100} status="Done" />
      );

      const progressBar = container.querySelector('.bg-gradient-to-r');
      expect(progressBar).toHaveStyle({ width: '100%' });
    });
  });

  describe('Status Display', () => {
    it('displays long status text correctly', () => {
      const longStatus = 'Generating video frames: Step 45 of 100 - Applying filters...';

      render(<ProgressBar progress={45} status={longStatus} />);

      expect(screen.getByText(longStatus)).toBeInTheDocument();
    });

    it('displays status with special characters', () => {
      const statusWithSpecialChars = 'Loading: Model (v2.2) [GPU: 0]';

      render(<ProgressBar progress={30} status={statusWithSpecialChars} />);

      expect(screen.getByText(statusWithSpecialChars)).toBeInTheDocument();
    });
  });

  describe('Snapshots', () => {
    it('matches snapshot at various progress levels', () => {
      const progressLevels = [0, 25, 50, 75, 100];

      progressLevels.forEach((progress) => {
        const { container } = render(
          <ProgressBar progress={progress} status={`Progress: ${progress}%`} />
        );

        expect(container).toMatchSnapshot();
      });
    });
  });
});
