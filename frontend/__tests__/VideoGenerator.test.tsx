import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VideoGenerator from '@/components/VideoGenerator';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('VideoGenerator Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();

    // Mock successful models fetch
    mockedAxios.get.mockResolvedValue({
      data: {
        models: [
          { id: 'wan-2.2-t2v', name: 'WAN-2.2-T2V', type: 'T2V' },
          { id: 'wan-2.2-i2v', name: 'WAN-2.2-I2V', type: 'I2V' },
          { id: 'skyreels-v2-t2v', name: 'SKYREELS-V2-T2V', type: 'T2V' },
        ],
      },
    });
  });

  describe('Initial Render', () => {
    it('renders correctly', async () => {
      const { container } = render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      expect(container).toMatchSnapshot();
    });

    it('displays model selection dropdown', async () => {
      render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });

    it('displays prompt textarea', async () => {
      render(<VideoGenerator />);

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/describe/i);
        expect(textarea).toBeInTheDocument();
      });
    });

    it('displays generate button', async () => {
      render(<VideoGenerator />);

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /generate video/i });
        expect(button).toBeInTheDocument();
      });
    });

    it('fetches models on mount', async () => {
      render(<VideoGenerator />);

      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          expect.stringContaining('/models')
        );
      });
    });
  });

  describe('Form Validation', () => {
    it('disables generate button when prompt is empty', async () => {
      render(<VideoGenerator />);

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /generate video/i });
        expect(button).toBeDisabled();
      });
    });

    it('enables generate button when prompt is filled', async () => {
      const user = userEvent.setup();
      render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/describe/i);
      await user.type(textarea, 'A beautiful sunset over the ocean');

      const button = screen.getByRole('button', { name: /generate video/i });
      expect(button).toBeEnabled();
    });
  });

  describe('Model Selection', () => {
    it('populates models from API', async () => {
      render(<VideoGenerator />);

      await waitFor(() => {
        const select = screen.getByRole('combobox');
        expect(select).toBeInTheDocument();
      });

      // Check that models are loaded
      expect(screen.getByText(/WAN-2.2-T2V/i)).toBeInTheDocument();
    });

    it('shows image upload for I2V models', async () => {
      const user = userEvent.setup();
      render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'wan-2.2-i2v');

      await waitFor(() => {
        expect(screen.getByText(/input image/i)).toBeInTheDocument();
      });
    });
  });

  describe('Advanced Settings', () => {
    it('shows advanced settings when expanded', async () => {
      const user = userEvent.setup();
      render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      // Click on summary to expand
      const summary = screen.getByText(/advanced settings/i);
      await user.click(summary);

      // Check that settings are visible
      expect(screen.getByText(/frames/i)).toBeInTheDocument();
      expect(screen.getByText(/fps/i)).toBeInTheDocument();
    });
  });

  describe('Video Generation', () => {
    it('submits generation request', async () => {
      const user = userEvent.setup();

      mockedAxios.post.mockResolvedValue({
        data: {
          task_id: 'test-task-123',
          status: 'submitted',
          message: 'Task submitted',
        },
      });

      render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      // Fill prompt
      const textarea = screen.getByPlaceholderText(/describe/i);
      await user.type(textarea, 'Test prompt');

      // Click generate
      const button = screen.getByRole('button', { name: /generate video/i });
      await user.click(button);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          expect.stringContaining('/api/generate'),
          expect.objectContaining({
            prompt: 'Test prompt',
          })
        );
      });
    });

    it('shows generating state', async () => {
      const user = userEvent.setup();

      // Make the request hang
      mockedAxios.post.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 10000))
      );

      render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/describe/i);
      await user.type(textarea, 'Test prompt');

      const button = screen.getByRole('button', { name: /generate video/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/generating/i)).toBeInTheDocument();
      });
    });

    it('handles API errors', async () => {
      const user = userEvent.setup();

      mockedAxios.post.mockRejectedValue({
        response: {
          data: {
            detail: 'Generation failed',
          },
        },
      });

      render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/describe/i);
      await user.type(textarea, 'Test prompt');

      const button = screen.getByRole('button', { name: /generate video/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/error|failed/i)).toBeInTheDocument();
      });
    });
  });

  describe('Snapshots', () => {
    it('matches snapshot in initial state', async () => {
      const { container } = render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      expect(container).toMatchSnapshot();
    });

    it('matches snapshot with expanded settings', async () => {
      const user = userEvent.setup();
      const { container } = render(<VideoGenerator />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const summary = screen.getByText(/advanced settings/i);
      await user.click(summary);

      expect(container).toMatchSnapshot();
    });
  });
});
