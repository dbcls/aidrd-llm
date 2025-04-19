"use client"

import { useState } from "react"
import UploadForm from "@/components/upload-form"
import TaskStatus from "@/components/task-status"

export default function Home() {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)

  // アップロード完了時にタスクIDを受け取る関数
  const handleTaskCreated = (taskId: string) => {
    setCurrentTaskId(taskId)
  }

  return (
    <div className="container mx-auto py-10 px-4">
      <h1 className="text-3xl font-bold text-center mb-8">人データベース申請支援システム</h1>

      <div className="grid gap-8 md:grid-cols-2">
        <div className="space-y-6">
          <div className="rounded-lg border p-6 shadow-sm">
            <h2 className="text-xl font-semibold mb-4">申請書PDFアップロード</h2>
            <UploadForm onTaskCreated={handleTaskCreated} />
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-lg border p-6 shadow-sm">
            <h2 className="text-xl font-semibold mb-4">処理状況確認</h2>
            <TaskStatus currentTaskId={currentTaskId} />
          </div>
        </div>
      </div>
    </div>
  )
}
