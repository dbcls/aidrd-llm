"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Upload, FileUp, CheckCircle2, AlertCircle } from "lucide-react"
import { Progress } from "@/components/ui/progress"

// APIのベースURL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

interface UploadFormProps {
  onTaskCreated: (taskId: string) => void
}

export default function UploadForm({ onTaskCreated }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!file) {
      setError("ファイルを選択してください")
      return
    }

    if (file.type !== "application/pdf") {
      setError("申請書PDFファイルのみアップロード可能です")
      return
    }

    setUploading(true)
    setProgress(0)
    setError(null)

    // FormDataの作成
    const formData = new FormData()
    formData.append("file", file)

    try {
      // アップロードの進捗をシミュレート
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 95) {
            clearInterval(progressInterval)
            return 95
          }
          return prev + 5
        })
      }, 200)

      // 実際のAPIエンドポイントにPDFをアップロード
      // ngrok-skip-browser-warningヘッダーを追加
      const response = await fetch(`${API_BASE_URL}/api/applications`, {
        method: "POST",
        headers: {
          "ngrok-skip-browser-warning": "true",
        },
        body: formData,
      })

      clearInterval(progressInterval)
      setProgress(100)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "アップロードに失敗しました")
      }

      const data = await response.json()
      // APIのレスポンス形式に合わせて調整
      const newTaskId = data.task_id || data.id || data.taskId

      if (!newTaskId) {
        throw new Error("タスクIDが取得できませんでした")
      }

      setTaskId(newTaskId)

      // 親コンポーネントにタスクIDを通知
      onTaskCreated(newTaskId)
    } catch (err) {
      setError(err instanceof Error ? err.message : "アップロードに失敗しました")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="pdf-upload">申請書PDFファイル</Label>
          <div className="flex items-center gap-2">
            <Input
              id="pdf-upload"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={uploading}
              className="flex-1"
            />
            <Button type="submit" disabled={uploading || !file}>
              {uploading ? <Upload className="mr-2 h-4 w-4 animate-pulse" /> : <FileUp className="mr-2 h-4 w-4" />}
              アップロード
            </Button>
          </div>
        </div>

        {uploading && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>アップロード中...</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}
      </form>

      {taskId && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            アップロードが完了しました。タスクID: <span className="font-mono font-bold">{taskId}</span>
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
