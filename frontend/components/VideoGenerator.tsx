'use client'

import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { Upload, Wand2, X, AlertCircle } from 'lucide-react'
import ProgressBar from './ProgressBar'
import VideoPlayer from './VideoPlayer'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Model {
  id: string
  name: string
  type: string
}

interface ProgressData {
  progress: number
  total: number
  percentage: number
  status: string
  metadata?: any
}

interface TaskResult {
  success: boolean
  video_path?: string
  s3_url?: string
  cdn_url?: string
  presigned_url?: string
  error?: string
}

export default function VideoGenerator() {
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [prompt, setPrompt] = useState<string>('')
  const [image, setImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)

  // Video parameters
  const [numFrames, setNumFrames] = useState<number>(81)
  const [height, setHeight] = useState<number>(720)
  const [width, setWidth] = useState<number>(1280)
  const [fps, setFps] = useState<number>(8)
  const [numInferenceSteps, setNumInferenceSteps] = useState<number>(50)
  const [guidanceScale, setGuidanceScale] = useState<number>(7.5)

  // Generation state
  const [isGenerating, setIsGenerating] = useState<boolean>(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [progress, setProgress] = useState<ProgressData | null>(null)
  const [result, setResult] = useState<TaskResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)

  // Fetch available models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await axios.get(`${API_URL}/models`)
        setModels(response.data.models)
        if (response.data.models.length > 0) {
          setSelectedModel(response.data.models[0].id)
        }
      } catch (err) {
        console.error('Failed to fetch models:', err)
        setError('Failed to load models')
      }
    }

    fetchModels()
  }, [])

  // Handle image upload
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImage(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  // Remove image
  const removeImage = () => {
    setImage(null)
    setImagePreview(null)
  }

  // Connect to WebSocket for progress updates
  const connectWebSocket = (taskId: string) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('Progress update:', data)

      if (data.status === 'connected') {
        return
      }

      setProgress(data)

      // Check if generation is complete
      if (data.percentage >= 100 && data.metadata) {
        setResult(data.metadata.result || data.metadata)
        setIsGenerating(false)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    wsRef.current = ws
  }

  // Handle video generation
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt')
      return
    }

    setIsGenerating(true)
    setError(null)
    setResult(null)
    setProgress(null)

    try {
      const isI2V = selectedModel.includes('i2v')

      let response

      if (isI2V && image) {
        // Image-to-video generation
        const formData = new FormData()
        formData.append('model_type', selectedModel)
        formData.append('prompt', prompt)
        formData.append('image', image)
        formData.append('num_frames', numFrames.toString())
        formData.append('height', height.toString())
        formData.append('width', width.toString())
        formData.append('fps', fps.toString())
        formData.append('num_inference_steps', numInferenceSteps.toString())
        formData.append('guidance_scale', guidanceScale.toString())
        formData.append('upload_to_s3', 'true')

        response = await axios.post(`${API_URL}/api/generate/i2v`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      } else {
        // Text-to-video generation
        response = await axios.post(`${API_URL}/api/generate`, {
          model_type: selectedModel,
          prompt,
          num_frames: numFrames,
          height,
          width,
          fps,
          num_inference_steps: numInferenceSteps,
          guidance_scale: guidanceScale,
          upload_to_s3: true,
        })
      }

      const { task_id } = response.data
      setTaskId(task_id)

      // Connect to WebSocket for progress updates
      connectWebSocket(task_id)

    } catch (err: any) {
      console.error('Generation failed:', err)
      setError(err.response?.data?.detail || 'Failed to start video generation')
      setIsGenerating(false)
    }
  }

  // Handle cancel
  const handleCancel = async () => {
    if (taskId) {
      try {
        await axios.delete(`${API_URL}/api/task/${taskId}`)
        if (wsRef.current) {
          wsRef.current.close()
        }
        setIsGenerating(false)
        setProgress(null)
      } catch (err) {
        console.error('Failed to cancel task:', err)
      }
    }
  }

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const isI2VModel = selectedModel.includes('i2v')

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-8 border border-gray-700">
        {/* Model Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Select Model
          </label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={isGenerating}
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
          >
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name} ({model.type})
              </option>
            ))}
          </select>
        </div>

        {/* Prompt Input */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Prompt
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isGenerating}
            placeholder="Describe the video you want to generate..."
            rows={4}
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 resize-none"
          />
        </div>

        {/* Image Upload (for I2V models) */}
        {isI2VModel && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Input Image (Required for I2V)
            </label>
            {!imagePreview ? (
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-600 border-dashed rounded-lg cursor-pointer bg-gray-700 hover:bg-gray-600 transition-colors">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <Upload className="w-8 h-8 text-gray-400 mb-2" />
                  <p className="text-sm text-gray-400">Click to upload image</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept="image/*"
                  onChange={handleImageChange}
                  disabled={isGenerating}
                />
              </label>
            ) : (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Preview"
                  className="w-full h-48 object-cover rounded-lg"
                />
                <button
                  onClick={removeImage}
                  disabled={isGenerating}
                  className="absolute top-2 right-2 p-2 bg-red-500 hover:bg-red-600 rounded-full text-white transition-colors disabled:opacity-50"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}

        {/* Advanced Settings */}
        <details className="mb-6">
          <summary className="cursor-pointer text-sm font-medium text-gray-300 mb-2">
            Advanced Settings
          </summary>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Frames</label>
              <input
                type="number"
                value={numFrames}
                onChange={(e) => setNumFrames(parseInt(e.target.value))}
                disabled={isGenerating}
                className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">FPS</label>
              <input
                type="number"
                value={fps}
                onChange={(e) => setFps(parseInt(e.target.value))}
                disabled={isGenerating}
                className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Width</label>
              <input
                type="number"
                value={width}
                onChange={(e) => setWidth(parseInt(e.target.value))}
                disabled={isGenerating}
                className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Height</label>
              <input
                type="number"
                value={height}
                onChange={(e) => setHeight(parseInt(e.target.value))}
                disabled={isGenerating}
                className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Inference Steps</label>
              <input
                type="number"
                value={numInferenceSteps}
                onChange={(e) => setNumInferenceSteps(parseInt(e.target.value))}
                disabled={isGenerating}
                className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Guidance Scale</label>
              <input
                type="number"
                step="0.1"
                value={guidanceScale}
                onChange={(e) => setGuidanceScale(parseFloat(e.target.value))}
                disabled={isGenerating}
                className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              />
            </div>
          </div>
        </details>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-400">{error}</div>
          </div>
        )}

        {/* Progress Bar */}
        {isGenerating && progress && (
          <div className="mb-6">
            <ProgressBar
              progress={progress.percentage}
              status={progress.status}
            />
          </div>
        )}

        {/* Generate Button */}
        <div className="flex gap-4">
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !prompt.trim() || (isI2VModel && !image)}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Wand2 className="w-5 h-5" />
            {isGenerating ? 'Generating...' : 'Generate Video'}
          </button>

          {isGenerating && (
            <button
              onClick={handleCancel}
              className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Result Video Player */}
      {result && result.success && result.presigned_url && (
        <div className="mt-8">
          <VideoPlayer
            videoUrl={result.cdn_url || result.presigned_url}
            presignedUrl={result.presigned_url}
          />
        </div>
      )}
    </div>
  )
}
