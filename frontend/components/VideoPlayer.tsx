'use client'

import { Download } from 'lucide-react'

interface VideoPlayerProps {
  videoUrl: string
  presignedUrl?: string
  onDownload?: () => void
}

export default function VideoPlayer({ videoUrl, presignedUrl, onDownload }: VideoPlayerProps) {
  const downloadUrl = presignedUrl || videoUrl

  const handleDownload = () => {
    if (onDownload) {
      onDownload()
    } else {
      window.open(downloadUrl, '_blank')
    }
  }

  return (
    <div className="w-full bg-gray-800/50 rounded-lg p-4 border border-gray-700">
      <div className="aspect-video bg-black rounded-lg overflow-hidden mb-4">
        <video
          src={videoUrl}
          controls
          className="w-full h-full object-contain"
          autoPlay
          loop
        >
          Your browser does not support the video tag.
        </video>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-400">
          Video generated successfully
        </div>
        <button
          onClick={handleDownload}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          Download Video
        </button>
      </div>
    </div>
  )
}
