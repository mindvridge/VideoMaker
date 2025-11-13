# AI Video Generation Web Application

A full-stack web application for generating AI videos using multiple state-of-the-art models including Wan 2.2, SkyReels V2, and HunyuanVideo-I2V.

## Features

- **Multiple Model Support**: Choose from various AI models optimized for different use cases
  - Wan 2.2 (T2V, I2V)
  - SkyReels V2 (T2V, I2V, Diffusion Forcing)
  - HunyuanVideo-I2V (Stability/Dynamic modes)

- **Asynchronous Processing**: Background task processing with Celery
- **Real-time Progress Tracking**: WebSocket and SSE support for live updates
- **Cloud Storage**: Automatic upload to AWS S3 with CloudFront CDN
- **GPU Optimization**: Memory management, CPU offloading, and FP16/BF16 quantization
- **Modern UI**: Next.js 14 with TypeScript and Tailwind CSS

## Technology Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **Celery**: Distributed task queue for background processing
- **Redis**: Message broker and cache
- **PyTorch**: Deep learning framework
- **Diffusers**: Model inference pipeline
- **FFmpeg**: Video optimization
- **Boto3**: AWS S3 integration

### Frontend
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **NVIDIA CUDA**: GPU acceleration
- **AWS S3**: Object storage
- **CloudFront**: CDN

## Project Structure

```
video-gen-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── worker.py            # Celery worker configuration
│   │   ├── tasks.py             # Celery tasks
│   │   ├── models.py            # GPU model manager
│   │   ├── storage.py           # S3 storage manager
│   │   └── config.py            # Configuration settings
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Main page
│   │   ├── layout.tsx           # Root layout
│   │   └── globals.css          # Global styles
│   ├── components/
│   │   ├── VideoGenerator.tsx   # Video generation component
│   │   ├── ProgressBar.tsx      # Progress indicator
│   │   └── VideoPlayer.tsx      # Video player
│   ├── package.json
│   └── next.config.js
├── docker-compose.yml
├── .env.example
└── README.md
```

## Prerequisites

- **Docker** and **Docker Compose**
- **NVIDIA GPU** with CUDA support (recommended)
- **NVIDIA Container Toolkit** (for GPU support in Docker)
- **AWS Account** with S3 bucket (for video storage)
- At least **16GB RAM** (32GB+ recommended)
- **50GB+ free disk space** (for models and outputs)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd VideoMaker
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure the following:

```env
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
CLOUDFRONT_DOMAIN=your-domain.cloudfront.net

# GPU Settings
CUDA_VISIBLE_DEVICES=0
ENABLE_CPU_OFFLOAD=true
USE_BF16=true
```

### 3. Install NVIDIA Container Toolkit (if using GPU)

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 4. Build and Run with Docker Compose

```bash
docker-compose up --build
```

This will start:
- **FastAPI Backend** on http://localhost:8000
- **Next.js Frontend** on http://localhost:3000
- **Celery Worker** (GPU)
- **Redis** on port 6379
- **Flower** (Celery monitor) on http://localhost:5555

## Usage

### Web Interface

1. Open http://localhost:3000 in your browser
2. Select an AI model from the dropdown
3. Enter a text prompt describing your desired video
4. (Optional) Upload an image for Image-to-Video models
5. Adjust advanced settings if needed
6. Click "Generate Video"
7. Monitor real-time progress
8. Download the generated video when complete

### API Endpoints

#### Generate Video (Text-to-Video)

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "wan-2.2-t2v",
    "prompt": "A beautiful sunset over the ocean",
    "num_frames": 81,
    "height": 720,
    "width": 1280,
    "fps": 8
  }'
```

#### Generate Video (Image-to-Video)

```bash
curl -X POST http://localhost:8000/api/generate/i2v \
  -F "model_type=wan-2.2-i2v" \
  -F "prompt=Ocean waves" \
  -F "image=@input.jpg" \
  -F "num_frames=81"
```

#### Get Task Status

```bash
curl http://localhost:8000/api/status/{task_id}
```

#### Stream Progress (SSE)

```bash
curl http://localhost:8000/api/stream/{task_id}
```

#### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{task_id}')
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log('Progress:', data.percentage)
}
```

## Configuration

### Model Settings

Edit `backend/app/config.py` to customize:

- Model cache directory
- GPU memory settings
- Default video parameters
- Upload limits

### Video Parameters

Available parameters for video generation:

- `num_frames`: 1-300 (default: 81)
- `fps`: 1-30 (default: 8)
- `height`: 256-1080 (default: 720)
- `width`: 256-1920 (default: 1280)
- `num_inference_steps`: 10-100 (default: 50)
- `guidance_scale`: 1.0-20.0 (default: 7.5)

## Monitoring

### Celery Flower

Access Celery monitoring dashboard at http://localhost:5555

Features:
- Active tasks
- Task history
- Worker status
- Task statistics

### Logs

Backend logs are stored in `backend/logs/`:
- `api_*.log`: FastAPI application logs
- `worker_*.log`: Celery worker logs

## Performance Optimization

### GPU Memory Management

The application automatically manages GPU memory:
- Model CPU offloading when enabled
- Attention slicing for memory efficiency
- VAE slicing for large resolutions
- Automatic model unloading

### Video Optimization

FFmpeg automatically optimizes videos:
- H.264 codec with preset configuration
- Fast-start enabled for streaming
- Adjustable CRF for quality/size balance

### Caching

- Model weights cached in `/root/.cache/huggingface`
- Redis caching for task status
- CloudFront CDN for video delivery

## Troubleshooting

### GPU Not Detected

```bash
# Check GPU availability
nvidia-smi

# Verify Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### Out of Memory Errors

1. Enable CPU offloading: `ENABLE_CPU_OFFLOAD=true`
2. Reduce number of frames
3. Lower resolution
4. Use FP16: `USE_FP16=true`

### Slow Generation

- Check GPU utilization with `nvidia-smi`
- Reduce `num_inference_steps`
- Ensure models are cached locally
- Check network bandwidth for S3 uploads

### Connection Issues

```bash
# Check services status
docker-compose ps

# View logs
docker-compose logs web
docker-compose logs worker

# Restart services
docker-compose restart
```

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## API Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.

## Acknowledgments

- [Wan 2.2](https://github.com/alibaba/Wan) by Alibaba
- [SkyReels V2](https://github.com/SkyReels/SkyReels)
- [HunyuanVideo](https://github.com/Tencent/HunyuanVideo) by Tencent
- [Diffusers](https://github.com/huggingface/diffusers) by Hugging Face
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
