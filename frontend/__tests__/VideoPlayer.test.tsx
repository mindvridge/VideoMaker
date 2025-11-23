import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import VideoPlayer from '@/components/VideoPlayer';

describe('VideoPlayer Component', () => {
  const defaultProps = {
    videoUrl: 'https://example.com/video.mp4',
    presignedUrl: 'https://example.com/presigned/video.mp4',
  };

  describe('Rendering', () => {
    it('renders correctly with video URL', () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = screen.getByRole('video', { hidden: true }) ||
        container.querySelector('video');

      expect(video).toBeInTheDocument();
      expect(container).toMatchSnapshot();
    });

    it('renders download button', () => {
      render(<VideoPlayer {...defaultProps} />);

      const downloadButton = screen.getByRole('button', { name: /download/i });
      expect(downloadButton).toBeInTheDocument();
    });

    it('renders success message', () => {
      render(<VideoPlayer {...defaultProps} />);

      expect(screen.getByText(/video generated successfully/i)).toBeInTheDocument();
    });

    it('sets video source correctly', () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = container.querySelector('video');
      expect(video).toHaveAttribute('src', defaultProps.videoUrl);
    });
  });

  describe('Video Controls', () => {
    it('video has controls attribute', () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = container.querySelector('video');
      expect(video).toHaveAttribute('controls');
    });

    it('video has autoplay attribute', () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = container.querySelector('video');
      expect(video).toHaveAttribute('autoplay');
    });

    it('video has loop attribute', () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = container.querySelector('video');
      expect(video).toHaveAttribute('loop');
    });
  });

  describe('Download Functionality', () => {
    beforeEach(() => {
      // Mock window.open
      global.open = jest.fn();
    });

    afterEach(() => {
      jest.restoreAllMocks();
    });

    it('opens presigned URL on download click', () => {
      render(<VideoPlayer {...defaultProps} />);

      const downloadButton = screen.getByRole('button', { name: /download/i });
      fireEvent.click(downloadButton);

      expect(global.open).toHaveBeenCalledWith(
        defaultProps.presignedUrl,
        '_blank'
      );
    });

    it('falls back to video URL if no presigned URL', () => {
      render(<VideoPlayer videoUrl={defaultProps.videoUrl} />);

      const downloadButton = screen.getByRole('button', { name: /download/i });
      fireEvent.click(downloadButton);

      expect(global.open).toHaveBeenCalledWith(
        defaultProps.videoUrl,
        '_blank'
      );
    });

    it('calls custom onDownload handler if provided', () => {
      const onDownload = jest.fn();

      render(<VideoPlayer {...defaultProps} onDownload={onDownload} />);

      const downloadButton = screen.getByRole('button', { name: /download/i });
      fireEvent.click(downloadButton);

      expect(onDownload).toHaveBeenCalled();
      expect(global.open).not.toHaveBeenCalled();
    });
  });

  describe('Snapshots', () => {
    it('matches snapshot with all props', () => {
      const { container } = render(
        <VideoPlayer
          videoUrl="https://cdn.example.com/video.mp4"
          presignedUrl="https://s3.example.com/presigned/video.mp4"
          onDownload={() => {}}
        />
      );

      expect(container).toMatchSnapshot();
    });

    it('matches snapshot without presigned URL', () => {
      const { container } = render(
        <VideoPlayer videoUrl="https://cdn.example.com/video.mp4" />
      );

      expect(container).toMatchSnapshot();
    });
  });
});
